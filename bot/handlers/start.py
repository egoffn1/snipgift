import aiohttp
from aiogram import Router, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu_kb, track_confirm_kb
from bot.handlers.alerts import render_alerts_message
from config import settings as app_settings
from db.session import session_factory
from db import repo
from markets.aggregator import create_clients
from markets.base import GiftListing
from utils.logger import get_logger
from utils.urls import parse_gift_url, friendly_name, TELEGRAM_MARKET

logger = get_logger("bot.start")

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user:
        async with session_factory() as session:
            await repo.upsert_user(session, user.id, user.username)
    await _send_welcome(message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _send_welcome(message)


async def _send_welcome(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я — **SnipGift**, сканер арбитража "
        "Telegram-подарков (NFT Gifts на TON).\n\n"
        "Просто **скинь мне ссылку на подарок** — и я начну "
        "отслеживать похожие.\n\n"
        "Работают:\n"
        "• ссылки с маркетов — `tonnel.network/gift/12345`\n"
        "• ссылки из Telegram — `t.me/nft/WinterWreath-2868`",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("track"))
async def cmd_track(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    url = text.replace("/track", "", 1).strip()
    if url:
        await _handle_gift_url(message, url)
    else:
        await message.answer(
            "Отправь ссылку на подарок, например:\n"
            "`/track https://tonnel.network/gift/12345`",
            parse_mode="Markdown",
        )


@router.message(StateFilter(None), F.text.regexp(r"(?i)http(s)?://"))
async def on_msg_with_url(message: Message) -> None:
    await _handle_gift_url(message, message.text or "")


def _client_for(market: str, http: aiohttp.ClientSession):
    auth = {
        "tonnel": app_settings.TONNEL_AUTH_DATA,
        "mrkt": app_settings.MRKT_AUTH_DATA,
        "portals": app_settings.PORTALS_AUTH_DATA,
        "fragment": app_settings.FRAGMENT_AUTH_DATA,
    }.get(market, "")
    clients = create_clients(http, {market: auth})
    return clients.get(market)


async def _resolve_name(market: str, gift_id: str, hint: str) -> str | None:
    if market == TELEGRAM_MARKET:
        return friendly_name(hint) or None
    if hint and hint.lower() in {"tonnel", "fragment", "mrkt", "portals"}:
        hint = ""
    try:
        async with aiohttp.ClientSession() as http:
            client = _client_for(market, http)
            if client is None:
                return hint or None
            gift: GiftListing | None = await client.get_gift_by_id(gift_id)
            return gift.gift_name or hint or None
    except Exception as exc:
        logger.debug("metadata resolve failed for %s %s: %s", market, gift_id, exc)
        return hint or None


async def _handle_gift_url(message: Message, url: str) -> None:
    parsed = parse_gift_url(url)
    if not parsed:
        await message.answer(
            "⚠️ Не узнал ссылку. Отправь ссылку на подарок:\n"
            "• ссылка с маркета (`tonnel.network`, `tgmrkt.io`, `portals.to`, `fragment.com`)\n"
            "• ссылка из Telegram (`t.me/nft/WinterWreath-2868`)",
            parse_mode="Markdown",
        )
        return

    market, gift_id, hint = parsed
    user = message.from_user
    if not user:
        return

    await message.answer("🔎 Определяю подарок...")

    name = await _resolve_name(market, gift_id, hint)
    if not name:
        await message.answer(
            "😔 Не удалось определить коллекцию по ссылке. "
            "Напиши название подарка текстом (например `Heart`), "
            "и я начну отслеживать.",
            parse_mode="Markdown",
        )
        return

    async with session_factory() as session:
        await repo.upsert_user(session, user.id, user.username)
        await repo.upsert_track_settings(session, user.id, name)

    await message.answer(
        f"🎉 Начинаю отслеживать **{name}**!\n"
        "Найду дешёвые листинги и пришлю алерт, если продавец "
        "выложил цену ниже рынка.\n\n"
        "Можно подкрутить алерт (прибыль, рынки продажи, пауза).",
        parse_mode="Markdown",
        reply_markup=track_confirm_kb(),
    )


@router.message(StateFilter(None), F.text == "🔍 Настроить поиск")
async def on_menu_settings(message: Message) -> None:
    await message.answer(
        "Просто отправь мне **ссылку на подарок**, который хочешь "
        "отслеживать — я всё сделаю сам.\n\n"
        "Хочешь подстроить алерт под себя? Нажми **📊 Мои алерты** "
        "и там будут кнопки настроек.",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.message(StateFilter(None), F.text == "📊 Мои алерты")
async def on_menu_alerts(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user.id)
        if existing:
            recent = await repo.get_recent_alerts(session, user.id, limit=20)
        else:
            recent = []
    await render_alerts_message(message, existing, recent)


@router.message(StateFilter(None), F.text == "⏸️ Пауза")
async def on_menu_pause(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user.id)
        if existing:
            existing.paused = True
            await session.commit()
    await message.answer(
        "⏸️ Скан приостановлен. Нажми «▶️ Продолжить» для возобновления.",
        reply_markup=main_menu_kb(),
    )


@router.message(StateFilter(None), F.text == "▶️ Продолжить")
async def on_menu_resume(message: Message) -> None:
    user = message.from_user
    if not user:
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user.id)
        if existing:
            existing.paused = False
            await session.commit()
    await message.answer("✅ Скан продолжается!", reply_markup=main_menu_kb())


@router.message(StateFilter(None), F.text == "ℹ️ Помощь")
async def on_menu_help(message: Message) -> None:
    await message.answer(
        "📖 **Как пользоваться:**\n"
        "1. Скинь ссылку на подарок — бот определит коллекцию и начнёт мониторить похожие\n"
        "2. Раз в несколько секунд сканирует Tonnel / MRKT / Portals / Fragment\n"
        "3. Найдёт листинг дешевле рынка — пришлёт алерт с ценой и прибылью\n\n"
        "Свой алерт можно подкрутить: **📊 Мои алерты**",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.message(StateFilter(None))
async def on_unknown_text(message: Message) -> None:
    if not message.text:
        return
    await message.answer(
        "Не понял 😅 Отправь ссылку на подарок — с маркета или из Telegram:\n"
        "`https://tonnel.network/gift/12345` или `https://t.me/nft/Heart-123`",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main(callback: CallbackQuery) -> None:
    await callback.answer("Главное меню внизу под полем ввода 👇")