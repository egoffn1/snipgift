from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.keyboards import _build_sell_kb, MARKET_LABELS
from db.session import session_factory
from db import repo
from utils.logger import get_logger

logger = get_logger("bot.settings")

router = Router(name="settings")


@router.callback_query(F.data == "cfg:open")
async def cf_open(callback: CallbackQuery) -> None:
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    await callback.answer()
    await _show_adjust(callback, uid)


@router.callback_query(F.data.startswith("cfg:sell:"))
async def cf_sell(callback: CallbackQuery) -> None:
    value = callback.data.split(":", 2)[2]
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, uid)
        if not existing:
            await callback.answer("Нет настроек")
            return
        sel = [s for s in (existing.sell_markets or []) if s in MARKET_LABELS]
        if value in MARKET_LABELS:
            if value in sel:
                sel.remove(value)
            else:
                sel.append(value)
        existing.sell_markets = sel
        await session.commit()
    await callback.answer()
    await _show_adjust(callback, uid)


@router.callback_query(F.data.startswith("cfg:profit:"))
async def cf_profit(callback: CallbackQuery) -> None:
    value = float(callback.data.split(":", 2)[2])
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, uid)
        if not existing:
            await callback.answer("Нет настроек")
            return
        existing.min_profit_pct = max(0.0, value)
        await session.commit()
    await callback.answer()
    await _show_adjust(callback, uid)


@router.callback_query(F.data == "cfg:pause")
async def cf_pause(callback: CallbackQuery) -> None:
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    async with session_factory() as session:
        existing = await repo.get_settings_for_user(session, uid)
        if existing:
            existing.paused = not existing.paused
            await session.commit()
    await callback.answer()
    await _show_adjust(callback, uid)


@router.callback_query(F.data == "cfg:done")
async def cf_done(callback: CallbackQuery) -> None:
    await callback.answer("Готово ✅")


async def _show_adjust(source, user_id: int) -> None:
    async with session_factory() as session:
        s = await repo.get_settings_for_user(session, user_id)
    if not s:
        return

    sell = [m for m in (s.sell_markets or []) if m in MARKET_LABELS]
    kb = _build_sell_kb(sell, s.min_profit_pct, s.paused)

    status = "⏸️ Пауза" if s.paused else "✅ Активен"
    text = (
        f"🎁 **{s.gift_name}** — {status}\n"
        f"Цена: {s.min_price:.0f}–{s.max_price or '∞'} TON\n"
        f"Мин. прибыль: **{s.min_profit_pct:.0f}%**\n"
        f"Рынки продажи: {', '.join(sell) or 'все'}\n\n"
        "Настрой — кнопки обновят алерт сразу."
    )

    if isinstance(source, CallbackQuery):
        try:
            await source.message.edit_text(
                text, parse_mode="Markdown", reply_markup=kb
            )
        except Exception:
            try:
                await source.message.answer(
                    text, parse_mode="Markdown", reply_markup=kb
                )
            except Exception:
                pass
    elif isinstance(source, Message):
        try:
            await source.answer(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            pass