from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards import (
    MARKET_LABELS,
    market_checkboxes,
    floor_market_choice,
    attr_options,
    yes_no,
    auctions_menu,
    settings_saved,
    main_menu,
)
from config import settings as app_settings
from db.session import session_factory
from db import repo
from utils.logger import get_logger

logger = get_logger("bot.settings")

router = Router(name="settings")


class SearchSettings(StatesGroup):
    gift_name = State()
    model = State()
    model_manual = State()
    backdrop = State()
    backdrop_manual = State()
    pattern = State()
    pattern_manual = State()
    min_price = State()
    max_price = State()
    min_profit = State()
    beautiful_id = State()
    buy_markets = State()
    sell_markets = State()
    floor_markets = State()
    auctions = State()
    max_auction_bid = State()


def _float_or_none(text: str) -> float | None:
    text = text.strip().replace(",", ".").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


@router.callback_query(F.data == "menu:settings")
async def start_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(SearchSettings.gift_name)
    await callback.message.edit_text(
        "🔍 **Шаг 1/13. Название подарка**\n\n"
        "Введи название коллекции подарка, например:\n"
        "`Heart`, `Diamond`, `Ring`, `Star`...",
        parse_mode="Markdown",
    )


@router.message(SearchSettings.gift_name, F.text)
async def on_gift_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    await state.update_data(gift_name=name)
    await state.set_state(SearchSettings.model)
    kb = attr_options("model")
    kb.inline_keyboard.insert(0, [{"text": "🌹 Heart", "callback_data": "model:Heart"}])
    kb.inline_keyboard.insert(1, [{"text": "💎 Diamond", "callback_data": "model:Diamond"}])
    kb.inline_keyboard.insert(2, [{"text": "💍 Ring", "callback_data": "model:Ring"}])
    kb.inline_keyboard.insert(3, [{"text": "⭐ Star", "callback_data": "model:Star"}])
    await message.answer(
        "🔍 **Шаг 2/13. Модель** (можно пропустить как «любая»)",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.callback_query(SearchSettings.model, F.data.startswith("model:"))
async def on_model_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    if choice == "any":
        await state.update_data(model=None)
        await _ask_backdrop(callback.message, state)
    elif choice == "manual":
        await state.set_state(SearchSettings.model_manual)
        await callback.message.answer("✍️ Введи название модели текстом:")
    else:
        await state.update_data(model=choice if choice != "любая" else None)
        await _ask_backdrop(callback.message, state)


@router.message(SearchSettings.model_manual, F.text)
async def on_model_manual(message: Message, state: FSMContext) -> None:
    await state.update_data(model=message.text.strip())
    await _ask_backdrop(message, state)


async def _ask_backdrop(message: Message, state: FSMContext) -> None:
    kb = attr_options("backdrop")
    kb.inline_keyboard.insert(0, [{"text": "🌌 Небо", "callback_data": "backdrop:Небо"}])
    kb.inline_keyboard.insert(1, [{"text": "🌊 Море", "callback_data": "backdrop:Море"}])
    await state.set_state(SearchSettings.backdrop)
    await message.answer(
        "🔍 **Шаг 3/13. Фон** (можно пропустить как «любой»)",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.callback_query(SearchSettings.backdrop, F.data.startswith("backdrop:"))
async def on_backdrop_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    if choice == "any":
        await state.update_data(backdrop=None)
        await _ask_pattern(callback.message, state)
    elif choice == "manual":
        await state.set_state(SearchSettings.backdrop_manual)
        await callback.message.answer("✍️ Введи название фона текстом:")
    else:
        await state.update_data(backdrop=choice if choice != "любой" else None)
        await _ask_pattern(callback.message, state)


@router.message(SearchSettings.backdrop_manual, F.text)
async def on_backdrop_manual(message: Message, state: FSMContext) -> None:
    await state.update_data(backdrop=message.text.strip())
    await _ask_pattern(message, state)


async def _ask_pattern(message: Message, state: FSMContext) -> None:
    kb = attr_options("pattern")
    kb.inline_keyboard.insert(0, [{"text": "🎁 Подарок", "callback_data": "pattern:Подарок"}])
    kb.inline_keyboard.insert(1, [{"text": "💠 Узор", "callback_data": "pattern:Узор"}])
    await state.set_state(SearchSettings.pattern)
    await message.answer(
        "🔍 **Шаг 4/13. Узор** (можно пропустить как «любой»)",
        parse_mode="Markdown",
        reply_markup=kb,
    )


@router.callback_query(SearchSettings.pattern, F.data.startswith("pattern:"))
async def on_pattern_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    if choice == "any":
        await state.update_data(pattern=None)
        await _ask_min_price(callback.message, state)
    elif choice == "manual":
        await state.set_state(SearchSettings.pattern_manual)
        await callback.message.answer("✍️ Введи название узора текстом:")
    else:
        await state.update_data(pattern=choice if choice != "любый" else None)
        await _ask_min_price(callback.message, state)


@router.message(SearchSettings.pattern_manual, F.text)
async def on_pattern_manual(message: Message, state: FSMContext) -> None:
    await state.update_data(pattern=message.text.strip())
    await _ask_min_price(message, state)


async def _ask_min_price(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSettings.min_price)
    await message.answer(
        "🔍 **Шаг 5/13. Мин. цена покупки, TON**\n\n"
        "Введи число, например `5` или `12.5`",
        parse_mode="Markdown",
    )


@router.message(SearchSettings.min_price, F.text)
async def on_min_price(message: Message, state: FSMContext) -> None:
    value = _float_or_none(message.text)
    if value is None or value < 0:
        await message.answer("⚠️ Введи корректное число (≥ 0), например `5`")
        return
    await state.update_data(min_price=value)
    await state.set_state(SearchSettings.max_price)
    await message.answer(
        "🔍 **Шаг 6/13. Макс. цена покупки, TON**\n\n"
        "Введи число или `0` / `нет`, чтобы не ограничивать.",
        parse_mode="Markdown",
    )


@router.message(SearchSettings.max_price, F.text)
async def on_max_price(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text in ("0", "нет", "no", "--", "skip"):
        max_price = None
    else:
        value = _float_or_none(text)
        if value is None or value < 0:
            await message.answer("⚠️ Введи число, или `0` чтобы пропустить")
            return
        max_price = value
    await state.update_data(max_price=max_price)
    await state.set_state(SearchSettings.min_profit)
    await message.answer(
        "🔍 **Шаг 7/13. Мин. % прибыли для алерта**\n\n"
        "Например `10` — алерт придёт, если прибыль ≥ 10%.",
        parse_mode="Markdown",
    )


@router.message(SearchSettings.min_profit, F.text)
async def on_min_profit(message: Message, state: FSMContext) -> None:
    value = _float_or_none(message.text)
    if value is None or value < 0:
        await message.answer("⚠️ Введи число ≥ 0, например `10`")
        return
    await state.update_data(min_profit=value)
    await state.set_state(SearchSettings.beautiful_id)
    await message.answer(
        "🔍 **Шаг 8/13. Только «красивый» ID?**\n\n"
        "(палиндром, повторяющиеся цифры, числа < 1000)",
        parse_mode="Markdown",
        reply_markup=yes_no("bid"),
    )


@router.callback_query(SearchSettings.beautiful_id, F.data.startswith("bid:"))
async def on_bid_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    await state.update_data(beautiful_id=(choice == "yes"))
    await _ask_buy_markets(callback.message, state)


async def _ask_buy_markets(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSettings.buy_markets)
    data = await state.get_data()
    selected = data.get("buy_markets") or ["tonnel", "mrkt"]
    await message.answer(
        "🔍 **Шаг 9/13. Маркеты ПОКУПКИ**\n"
        "Где искать (можно отметить несколько)",
        parse_mode="Markdown",
        reply_markup=market_checkboxes(selected, "buy"),
    )


@router.callback_query(SearchSettings.buy_markets, F.data.startswith("buy:"))
async def on_buy_markets(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = list(data.get("buy_markets") or [])
    if choice == "done":
        if not selected:
            await callback.answer("Выбери хотя бы один маркет")
            return
        await _ask_sell_markets(callback.message, state)
        return
    if choice in MARKET_LABELS:
        selected = [s for s in selected if s in MARKET_LABELS]
        if choice in selected:
            selected.remove(choice)
        else:
            selected.append(choice)
        await state.update_data(buy_markets=selected)
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=market_checkboxes(selected, "buy")
        )
    else:
        await callback.answer()


async def _ask_sell_markets(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSettings.sell_markets)
    data = await state.get_data()
    selected = data.get("sell_markets") or ["tonnel", "mrkt"]
    await message.answer(
        "🔍 **Шаг 10/13. Маркеты ПРОДАЖИ**\n"
        "Куда планируешь перепродать",
        parse_mode="Markdown",
        reply_markup=market_checkboxes(selected, "sell"),
    )


@router.callback_query(SearchSettings.sell_markets, F.data.startswith("sell:"))
async def on_sell_markets(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = list(data.get("sell_markets") or [])
    if choice == "done":
        if not selected:
            await callback.answer("Выбери хотя бы один маркет")
            return
        await _ask_floor(callback.message, state)
        return
    if choice in MARKET_LABELS:
        selected = [s for s in selected if s in MARKET_LABELS]
        if choice in selected:
            selected.remove(choice)
        else:
            selected.append(choice)
        await state.update_data(sell_markets=selected)
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=market_checkboxes(selected, "sell")
        )
    else:
        await callback.answer()


async def _ask_floor(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSettings.floor_markets)
    await message.answer(
        "🔍 **Шаг 11/13. Маркеты для расчёта ФЛОРА**\n"
        "«Все» = глобальный флор по всем рынкам",
        parse_mode="Markdown",
        reply_markup=floor_market_choice(),
    )


@router.callback_query(SearchSettings.floor_markets, F.data.startswith("floor:"))
async def on_floor(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = list(data.get("floor_markets") or [])

    if choice == "all":
        await state.update_data(floor_markets=[])
        await _ask_auctions(callback.message, state)
        return
    if choice == "manual":
        await callback.answer()
        await callback.message.edit_text(
            "Выбери маркеты для расчёта флора",
            reply_markup=market_checkboxes(selected, "floor"),
        )
        return
    if choice == "done":
        if not selected:
            await callback.answer("Выбери хотя бы один или «Все»")
            return
        await _ask_auctions(callback.message, state)
        return
    if choice in MARKET_LABELS:
        selected = [s for s in selected if s in MARKET_LABELS]
        if choice in selected:
            selected.remove(choice)
        else:
            selected.append(choice)
        await state.update_data(floor_markets=selected)
        await callback.answer()
        await callback.message.edit_reply_markup(
            reply_markup=market_checkboxes(selected, "floor")
        )
        return
    await callback.answer()


async def _ask_auctions(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchSettings.auctions)
    await message.answer(
        "🔍 **Шаг 12/13. Участвовать в аукционах?**",
        parse_mode="Markdown",
        reply_markup=auctions_menu(),
    )


@router.callback_query(SearchSettings.auctions, F.data.startswith("auction:"))
async def on_auctions(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    choice = callback.data.split(":", 1)[1]
    enabled = choice == "on"
    await state.update_data(auctions=enabled)
    if enabled:
        await state.set_state(SearchSettings.max_auction_bid)
        await callback.message.answer(
            "🔍 **Шаг 13/13. Макс. ставка на аукционе, TON**\n"
            "Введи число или `0`, чтобы не ограничивать.",
            parse_mode="Markdown",
        )
    else:
        await state.update_data(max_auction_bid=None)
        await _finish(callback.from_user.id, callback.message, state)


@router.message(SearchSettings.max_auction_bid, F.text)
async def on_max_bid(message: Message, state: FSMContext) -> None:
    text = message.text.strip().lower()
    if text in ("0", "нет", "no", "skip"):
        max_bid = None
    else:
        value = _float_or_none(text)
        if value is None or value < 0:
            await message.answer("⚠️ Введи число ≥ 0 или `0` для пропуска")
            return
        max_bid = value
    await state.update_data(max_auction_bid=max_bid)
    from_user = message.from_user
    user_id = from_user.id if from_user else None
    await _finish(user_id, message, state)


async def _finish(user_id: int | None, message: Message, state: FSMContext) -> None:
    if user_id is None:
        await state.clear()
        return
    data = await state.get_data()

    from db.models import UserSettings

    settings_obj = UserSettings(
        user_id=user_id,
        gift_name=str(data.get("gift_name", "")),
        model=data.get("model"),
        backdrop=data.get("backdrop"),
        pattern=data.get("pattern"),
        min_price=float(data.get("min_price", 0)),
        max_price=data.get("max_price"),
        min_profit_pct=float(data.get("min_profit", 5)),
        beautiful_id_only=bool(data.get("beautiful_id", False)),
        buy_markets=data.get("buy_markets") or ["tonnel", "mrkt"],
        sell_markets=data.get("sell_markets") or ["tonnel", "mrkt"],
        floor_markets=data.get("floor_markets") or [],
        auctions_enabled=bool(data.get("auctions", False)),
        max_auction_bid=data.get("max_auction_bid"),
        scan_interval=app_settings.SCAN_INTERVAL,
    )

    async with session_factory() as session:
        await repo.upsert_user(session, user_id, None)
        old = await repo.get_settings_for_user(session, user_id)
        if old is not None:
            await session.delete(old)
            await session.commit()
        await repo.save_settings(session, settings_obj)

    await state.clear()
    summary = (
        f"✅ **Настройки сохранены!**\n\n"
        f"🎁 Подарок: `{settings_obj.gift_name}`\n"
        f"Модель: `{settings_obj.model or 'любая'}`\n"
        f"Фон: `{settings_obj.backdrop or 'любой'}`\n"
        f"Узор: `{settings_obj.pattern or 'любой'}`\n"
        f"Цена: {settings_obj.min_price:.1f} — "
        f"{settings_obj.max_price or '∞'} TON\n"
        f"Мин. прибыль: **{settings_obj.min_profit_pct:.1f}%**\n"
        f"Красивый ID: "
        f"{'да' if settings_obj.beautiful_id_only else 'нет'}\n"
        f"Маркеты покупки: {', '.join(settings_obj.buy_markets or [])}\n"
        f"Маркеты продажи: {', '.join(settings_obj.sell_markets or [])}\n"
        f"Флор: {', '.join(settings_obj.floor_markets) or 'Все'}\n"
        f"Аукционы: {'вкл' if settings_obj.auctions_enabled else 'выкл'}"
    )
    await message.answer(summary, parse_mode="Markdown", reply_markup=settings_saved())


@router.callback_query(F.data == "menu:show_settings")
async def cb_show_settings(callback: CallbackQuery) -> None:
    await callback.answer()
    user = callback.from_user
    user_id = user.id if user else None
    if user_id is None:
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user_id)

    if existing is None:
        await callback.message.edit_text(
            "Настроек ещё нет. Нажми **🔍 Настроить поиск**",
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )
        return
    summary = (
        "📋 **Текущие настройки:**\n"
        f"🎁 Подарок: `{existing.gift_name}`\n"
        f"Модель: `{existing.model or 'любая'}`\n"
        f"Фон: `{existing.backdrop or 'любой'}`\n"
        f"Узор: `{existing.pattern or 'любой'}`\n"
        f"Цена: {existing.min_price:.1f} — "
        f"{existing.max_price or '∞'} TON\n"
        f"Мин. прибыль: {existing.min_profit_pct:.1f}%\n"
        f"Красивый ID: {'да' if existing.beautiful_id_only else 'нет'}\n"
        f"Покупка: {', '.join(existing.buy_markets or [])}\n"
        f"Продажа: {', '.join(existing.sell_markets or [])}\n"
        f"Флор: {', '.join(existing.floor_markets) or 'Все'}\n"
        f"Аукционы: {'вкл' if existing.auctions_enabled else 'выкл'}\n"
        f"Пауза: {'да' if existing.paused else 'нет'}"
    )
    await callback.message.edit_text(
        summary, parse_mode="Markdown", reply_markup=main_menu()
    )
