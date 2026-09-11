from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from db.session import session_factory
from db import repo
from utils.logger import get_logger

logger = get_logger("bot.alerts")

router = Router(name="alerts")


def _alerts_kb(existing, paused: bool) -> InlineKeyboardMarkup:
    buttons = []
    if existing:
        btn_txt = "▶️ Продолжить сканирование" if paused else "⏸️ Пауза"
        btn_cb = "alert:resume" if paused else "alert:pause"
        buttons.append([InlineKeyboardButton(text=btn_txt, callback_data=btn_cb)])
        buttons.append([
            InlineKeyboardButton(text="⚙️ Настроить алерт", callback_data="cfg:open"),
        ])
    buttons.append([InlineKeyboardButton(text="🔍 Прислать ссылку", callback_data="menu:alerts")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _alerts_text(existing, recent, paused: bool) -> str:
    status = "⏸️ **СКАН ПРИОСТАНОВЛЕН**" if paused else "⏱️ **Сканер активен**"
    lines = [status, ""]
    if not existing:
        lines.append(
            "Пока ничего не отслеживаю. Пришли ссылку на подарок — "
            "начну мониторить похожие."
        )
        return "\n".join(lines)
    lines.append(f"🎁 Трекинг: **{existing.gift_name}**")
    lines.append(
        f"Цена: {existing.min_price:.1f}–{existing.max_price or '∞'} TON"
        f" · прибыль ≥ {existing.min_profit_pct:.1f}%"
    )
    lines.append("", "**Последние алерты:**")
    if not recent:
        lines.append("Пока пусто — как только найдётся выгодный листинг, он появится здесь.")
    else:
        for alert in recent[:10]:
            lines.append(
                f"• `{alert.listing_id}` — прибыль {alert.profit_pct:+.1f}% "
                f"({alert.sent_at.strftime('%d.%m %H:%M')})"
            )
    return "\n".join(lines)


async def _load_state(user_id: int):
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user_id)
        recent = await repo.get_recent_alerts(session, user_id, limit=20)
        paused = existing.paused if existing else False
    return existing, recent, paused


async def render_alerts(callback: CallbackQuery, user_id: int) -> None:
    existing, recent, paused = await _load_state(user_id)
    text = _alerts_text(existing, recent, paused)
    await callback.message.edit_text(
        text, parse_mode="Markdown", reply_markup=_alerts_kb(existing, paused)
    )


async def render_alerts_message(
    message: Message, existing, recent
) -> None:
    paused = existing.paused if existing else False
    text = _alerts_text(existing, recent, paused)
    await message.answer(
        text, parse_mode="Markdown", reply_markup=_alerts_kb(existing, paused)
    )


@router.callback_query(F.data == "menu:alerts")
async def cb_alerts(callback: CallbackQuery) -> None:
    await callback.answer()
    user = callback.from_user
    user_id = user.id if user else None
    if user_id is None:
        return
    await render_alerts(callback, user_id)


async def _set_pause(callback: CallbackQuery, paused: bool) -> None:
    user = callback.from_user
    user_id = user.id if user else None
    if user_id is None:
        await callback.answer("Ошибка: нет user")
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user_id)
        if existing is not None:
            existing.paused = paused
            await session.commit()
    await callback.answer("Готово")


@router.callback_query(F.data == "alert:pause")
async def cb_pause(callback: CallbackQuery) -> None:
    await _set_pause(callback, True)
    await callback.answer()
    user = callback.from_user
    if user:
        await render_alerts(callback, user.id)


@router.callback_query(F.data == "alert:resume")
async def cb_resume(callback: CallbackQuery) -> None:
    await _set_pause(callback, False)
    user = callback.from_user
    if user:
        await render_alerts(callback, user.id)


@router.callback_query(F.data == "menu:resume")
async def cb_resume_menu(callback: CallbackQuery) -> None:
    await _set_pause(callback, False)
    user = callback.from_user
    if user:
        await render_alerts(callback, user.id)


@router.callback_query(F.data == "menu:pause")
async def cb_pause_menu(callback: CallbackQuery) -> None:
    await _set_pause(callback, True)
    user = callback.from_user
    if user:
        await render_alerts(callback, user.id)


@router.callback_query(F.data.startswith("mute:"))
async def cb_mute(callback: CallbackQuery) -> None:
    gift_name = callback.data.split(":", 1)[1]
    user = callback.from_user
    user_id = user.id if user else None
    if user_id is None:
        await callback.answer("Ошибка: нет user")
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user_id)
        if existing is not None:
            existing.paused = True
            await session.commit()
    await callback.answer(
        f"Подарок `{gift_name}` замьючен: скан приостановлен. "
        "Чтобы вернуть, нажми «▶️ Продолжить».",
        show_alert=True,
    )