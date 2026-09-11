from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from db.session import session_factory
from db import repo
from utils.logger import get_logger

logger = get_logger("bot.alerts")

router = Router(name="alerts")


@router.callback_query(F.data == "menu:alerts")
async def cb_alerts(callback: CallbackQuery) -> None:
    await callback.answer()
    user = callback.from_user
    user_id = user.id if user else None
    if user_id is None:
        return

    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, user_id)
        recent = await repo.get_recent_alerts(session, user_id, limit=20)
        paused = existing.paused if existing else False

    status = "⏸️ **СКАН ПРИОСТАНОВЛЕН**" if paused else "⏱️ **Сканер активен**"
    lines = [status, ""]
    if not recent:
        lines.append("Алертов пока нет — как только найдётся выгодный листинг, он появится здесь.")
    else:
        lines.append("**Последние алерты:**")
        for alert in recent[:10]:
            lines.append(
                f"• `{alert.listing_id}` — прибыль {alert.profit_pct:+.1f}% "
                f"({alert.sent_at.strftime('%d.%m %H:%M')})"
            )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            (
                [
                    InlineKeyboardButton(
                        text="▶️ Продолжить сканирование",
                        callback_data="alert:resume",
                    )
                ]
                if paused
                else [
                    InlineKeyboardButton(
                        text="⏸️ Пауза",
                        callback_data="alert:pause",
                    )
                ]
            ),
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")],
        ]
    )
    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=keyboard)


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
    await cb_alerts(callback)


@router.callback_query(F.data == "alert:resume")
async def cb_resume(callback: CallbackQuery) -> None:
    await _set_pause(callback, False)
    await cb_alerts(callback)


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
        "Чтобы вернуть, нажми «Продолжить» в меню алертов.",
        show_alert=True,
    )
