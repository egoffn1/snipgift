import time
from typing import Any

import aiohttp
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    _build_attrs_kb,
    _build_sell_kb,
    MARKET_LABELS,
)
from db.session import session_factory
from db import repo
from markets.aggregator import create_clients, search_all
from utils.logger import get_logger

logger = get_logger("bot.settings")

router = Router(name="settings")

_ATTR_CACHE_TTL = 600
_attr_cache: dict[str, tuple[float, list[str], list[str], list[str]]] = {}


def _cycle(
    values: list[str], current: str | None, direction: str
) -> str | None:
    if not values:
        return None
    ring = list(values) + [None]
    if current not in ring:
        current = None
    idx = ring.index(current)
    if direction == "r":
        return ring[(idx + 1) % len(ring)]
    return ring[(idx - 1) % len(ring)]


def _pick_field(obj: Any, name: str) -> Any:
    return getattr(obj, name, None)


def _set_field(obj: Any, name: str, value: Any) -> None:
    setattr(obj, name, value)


# ─── fetch distinct attribute values ──────────────────────────────


async def _distinct_attrs(
    gift_name: str,
) -> tuple[list[str], list[str], list[str]]:
    cached = _attr_cache.get(gift_name)
    now = time.time()
    if cached and (now - cached[0]) < _ATTR_CACHE_TTL:
        return cached[1], cached[2], cached[3]

    models: list[str] = []
    backdrops: list[str] = []
    patterns: list[str] = []

    try:
        async with aiohttp.ClientSession() as http:
            clients = create_clients(http)
            listings = await search_all(
                clients,
                list(clients.keys()),
                gift_name=gift_name,
                limit=500,
            )
        seen_m: set[str] = set()
        seen_b: set[str] = set()
        seen_p: set[str] = set()
        for x in listings:
            m = (x.model or "").strip()
            if m and m not in seen_m:
                seen_m.add(m)
                models.append(m)
            b = (x.backdrop or "").strip()
            if b and b not in seen_b:
                seen_b.add(b)
                backdrops.append(b)
            p = (x.pattern or "").strip()
            if p and p not in seen_p:
                seen_p.add(p)
                patterns.append(p)
        models.sort()
        backdrops.sort()
        patterns.sort()
    except Exception as exc:
        logger.warning("Attribute fetch failed for %s: %s", gift_name, exc)

    _attr_cache[gift_name] = (now, models, backdrops, patterns)
    return models, backdrops, patterns


# ─── noop / unknown cfg callback ──────────────────────────────────


@router.callback_query(F.data == "cfg:noop")
async def cf_noop(callback: CallbackQuery) -> None:
    await callback.answer()


# ─── open main adjust panel ───────────────────────────────────────


@router.callback_query(F.data == "cfg:open")
async def cf_open(callback: CallbackQuery) -> None:
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    await callback.answer()
    await _show_adjust(callback, uid)


# ─── sell market toggle ───────────────────────────────────────────


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


# ─── profit buttons ───────────────────────────────────────────────


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


# ─── pause toggle ─────────────────────────────────────────────────


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


# ─── done button ──────────────────────────────────────────────────


@router.callback_query(F.data == "cfg:done")
async def cf_done(callback: CallbackQuery) -> None:
    await callback.answer("Готово ✅")


# ─── open attributes sub-panel ────────────────────────────────────


@router.callback_query(F.data == "cfg:attrs")
async def cf_attrs_open(callback: CallbackQuery) -> None:
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    await callback.answer()
    await _show_attrs(callback, uid)


# ─── cycle model / backdrop / pattern ─────────────────────────────


@router.callback_query(F.data.startswith("cfg:attr:"))
async def cf_attr_cycle(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    _, _, field, direction = parts
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    async with session_factory() as session:
        s = await repo.get_settings_for_user(session, uid)
        if not s:
            await callback.answer("Нет настроек")
            return
        models, backdrops, patterns = await _distinct_attrs(s.gift_name)
        values = {"model": models, "backdrop": backdrops, "pattern": patterns}.get(
            field, []
        )
        cur = getattr(s, field, None)
        setattr(s, field, _cycle(values, cur, direction))
        await session.commit()
    await callback.answer()
    await _show_attrs(callback, uid)


# ─── beautiful ID toggle ──────────────────────────────────────────


@router.callback_query(F.data.startswith("cfg:attr:id:"))
async def cf_attr_id(callback: CallbackQuery) -> None:
    flag = callback.data.endswith("yes")
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    async with session_factory() as session:
        s = await repo.get_settings_for_user(session, uid)
        if not s:
            await callback.answer("Нет настроек")
            return
        s.beautiful_id_only = flag
        await session.commit()
    await callback.answer()
    await _show_attrs(callback, uid)


# ─── back from attributes to main adjust ──────────────────────────


@router.callback_query(F.data == "cfg:attrs:back")
async def cf_attrs_back(callback: CallbackQuery) -> None:
    user = callback.from_user
    uid = user.id if user else None
    if not uid:
        await callback.answer()
        return
    await callback.answer()
    await _show_adjust(callback, uid)


# ─── render helpers ───────────────────────────────────────────────


async def _show_adjust(source: CallbackQuery | Message, user_id: int) -> None:
    async with session_factory() as session:
        s = await repo.get_settings_for_user(session, user_id)
    if not s:
        return

    sell = [m for m in (s.sell_markets or []) if m in MARKET_LABELS]
    kb = _build_sell_kb(sell, s.min_profit_pct, s.paused)

    status = "⏸️ Пауза" if s.paused else "✅ Активен"
    model = s.model or "—"
    backdrop = s.backdrop or "—"
    pattern = s.pattern or "—"
    id_text = "красивый ✨" if s.beautiful_id_only else "любой"
    text = (
        f"🎁 **{s.gift_name}** — {status}\n"
        f"Вариант: 🖌 `{model}` · 🎨 `{backdrop}` · 🧩 `{pattern}`\n"
        f"🔢 ID: {id_text}\n"
        f"Цена: {s.min_price:.0f}–{s.max_price or '∞'} TON\n"
        f"Мин. прибыль: **{s.min_profit_pct:.0f}%**\n"
        f"Рынки продажи: {', '.join(sell) or 'все'}\n\n"
        "Настрой — кнопки обновят алерт сразу."
    )
    await _send_reply(source, text, kb)


async def _show_attrs(source: CallbackQuery | Message, user_id: int) -> None:
    async with session_factory() as session:
        s = await repo.get_settings_for_user(session, user_id)
    if not s:
        return

    models, backdrops, patterns = await _distinct_attrs(s.gift_name)
    kb = _build_attrs_kb(
        models,
        backdrops,
        patterns,
        s.model,
        s.backdrop,
        s.pattern,
        s.beautiful_id_only,
    )

    model = s.model or "Любая"
    backdrop = s.backdrop or "Любая"
    pattern = s.pattern or "Любая"
    id_text = "✅ Вкл" if s.beautiful_id_only else "Выкл"
    text = (
        f"🎁 **{s.gift_name}** — варианты коллекции\n\n"
        f"🖌 Модель: `{model}`\n"
        f"🎨 Фон: `{backdrop}`\n"
        f"🧩 Узор: `{pattern}`\n"
        f"🔢 Красивый ID: **{id_text}**\n\n"
        "Стрелки ‹ › перебирают варианты. "
        "ID — палиндромы, повторы и номера < 1000."
    )
    await _send_reply(source, text, kb)


async def _send_reply(
    source: CallbackQuery | Message, text: str, kb: Any
) -> None:
    message = getattr(source, "message", None)
    if message is not None and hasattr(message, "edit_text"):
        try:
            await message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            try:
                await message.answer(text, parse_mode="Markdown", reply_markup=kb)
            except Exception:
                pass
        return
    if isinstance(source, Message):
        try:
            await source.answer(text, parse_mode="Markdown", reply_markup=kb)
        except Exception:
            pass
