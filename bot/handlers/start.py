from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards import main_menu
from db.session import session_factory
from db import repo
from utils.logger import get_logger

logger = get_logger("bot.start")

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    async with session_factory() as session:
        await repo.upsert_user(session, user.id, user.username)

    await message.answer(
        "👋 Привет! Я — **SnipGift**, сканер арбитража "
        "Telegram-подарков (NFT Gifts на TON).\n\n"
        "Я мониторю рынки Tonnel, MRKT, Portals и Fragment, "
        "нахожу листинги ниже флора и присылаю алерты.\n\n"
        "Нажми **🔍 Настроить поиск**, чтобы настроить "
        "поиск под себя.",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 **Как пользоваться:**\n"
        "1. Настроить поиск: выбери подарок, цену, маркеты и % прибыли\n"
        "2. Бот будет сканировать рынки каждые несколько секунд\n"
        "3. При нахождении выгодного листинга пришлёт алерт\n\n"
        "**/start** — главное меню\n"
        "**🔍 Настроить поиск** — настройка фильтров\n"
        "**📊 Мои алерты** — история и пауза\n\n"
        "⚠️ Задержка сканирования зависит от количества активных "
        "настроек. Настрой минимальный % прибыли, чтобы не спамило.",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "🏠 **Главное меню**",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:help")
async def cb_menu_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.edit_text(
        "📖 **Как пользоваться:**\n"
        "1. Настроить поиск: выбери подарок, цену, маркеты и % прибыли\n"
        "2. Бот будет сканировать рынки каждые несколько секунд\n"
        "3. При нахождении выгодного листинга пришлёт алерт",
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )
