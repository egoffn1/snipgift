import asyncio
from typing import Any

from config import settings
from db.session import session_factory
from db import repo
from markets.aggregator import create_clients, search_all, fetch_auctions_all
from core.filters import apply_all_filters
from core.floor import median_price
from core.analyzer import analyze_profit, ProfitResult
from utils.logger import get_logger

logger = get_logger("core.scanner")


def _mark_all_seen_factory():
    seen: set[str] = set()

    def check_and_mark(listing_id: str) -> bool:
        if listing_id in seen:
            return False
        seen.add(listing_id)
        return True

    return check_and_mark


async def _send_alert(
    bot: Any,
    user_id: int,
    result: ProfitResult,
    user_settings: Any,
) -> None:
    listing = result.listing
    market_url = listing.url or "https://tonnel.network"

    lines = [
        f"**{listing.gift_name}**",
    ]
    if listing.model:
        lines.append(f"Model: `{listing.model}`")
    if listing.backdrop:
        lines.append(f"Backdrop: `{listing.backdrop}`")
    if listing.pattern:
        lines.append(f"Pattern: `{listing.pattern}`")
    lines.append(f"ID: `{listing.id}`")
    lines.append("")
    lines.append(
        f"**Buy:** {result.buy_price:.2f} TON ({listing.market})"
        f"  fee {result.buy_market_fee*100:.1f}%"
    )
    lines.append(
        f"**Floor sell:** {result.floor_sell:.2f} TON ({result.floor_market})"
        f"  fee {result.sell_fee*100:.1f}%"
    )
    lines.append("")
    profit_emoji = "+" if result.profit_ton >= 0 else ""
    lines.append(
        f"**Net sell:** {result.net_sell:.2f} TON | "
        f"**Profit:** {profit_emoji}{result.profit_ton:.2f} TON "
        f"({profit_emoji}{result.profit_pct:.1f}%)"
    )
    if listing.is_auction:
        lines.append("Auction listing")
    text = "\n".join(lines)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open on market",
                    url=market_url,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Mute this gift",
                    callback_data=f"mute:{listing.gift_name}",
                )
            ],
        ]
    )

    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    except Exception as exc:
        logger.warning("Failed to send alert to %d: %s", user_id, exc)


async def self_ping_loop(http_session: Any, base_url: str) -> None:
    if not base_url:
        logger.warning("SELF_PING: no WEBHOOK_URL set, skipping self-ping loop")
        return
    ping_url = f"{base_url.rstrip('/')}/ping"
    logger.info("Self-ping loop will hit %s every %ds", ping_url, settings.SELF_PING_INTERVAL)
    while True:
        try:
            async with http_session.get(ping_url, timeout=10) as resp:
                logger.debug("Self-ping -> %s", resp.status)
        except Exception as exc:
            logger.warning("Self-ping failed: %s", exc)
        await asyncio.sleep(settings.SELF_PING_INTERVAL)


async def scanner_loop(bot: Any, http_session: Any) -> None:
    clients = create_clients(http_session)
    logger.info("Scanner started with markets: %s", list(clients.keys()))
    seen_check = _mark_all_seen_factory()

    while True:
        try:
            await _run_scan_cycle(bot, clients, seen_check)
        except Exception as exc:
            logger.error("Scanner cycle failed: %s", exc, exc_info=True)

        await asyncio.sleep(settings.SCAN_INTERVAL)


async def _run_scan_cycle(
    bot: Any,
    clients: Any,
    seen_check: Any,
) -> None:
    async with session_factory() as db_session:
        all_settings = await repo.get_all_settings(db_session)

    if not all_settings:
        return

    query_map: dict[str, list] = {}
    for user_settings, user in all_settings:
        key = (
            user_settings.gift_name.lower().strip(),
            tuple(sorted(user_settings.buy_markets or [])),
        )
        if key not in query_map:
            query_map[key] = []
        query_map[key].append((user_settings, user))

    for (gift_name, buy_markets_str), user_list in query_map.items():
        buy_markets = list(buy_markets_str) if buy_markets_str else list(clients.keys())
        first_settings = user_list[0][0]
        try:
            listings = await search_all(
                clients,
                buy_markets,
                gift_name=gift_name,
                model=first_settings.model,
                backdrop=first_settings.backdrop,
                pattern=first_settings.pattern,
                min_price=first_settings.min_price,
                max_price=first_settings.max_price,
                limit=200,
            )
        except Exception as exc:
            logger.warning("Search failed for %s: %s", gift_name, exc)
            continue

        if first_settings.auctions_enabled:
            try:
                auctions = await fetch_auctions_all(
                    clients,
                    buy_markets,
                    gift_name=gift_name,
                    min_price=first_settings.min_price,
                    max_price=first_settings.max_price,
                )
                listings.extend(auctions)
            except Exception as exc:
                logger.warning("Auction fetch failed for %s: %s", gift_name, exc)

        floor_markets_list = list(first_settings.floor_markets or [])
        sell_markets_list = list(first_settings.sell_markets or [])
        median = median_price(listings)

        seen_in_cycle: set[str] = set()
        for listing in listings:
            lid = listing.listing_id
            if lid in seen_in_cycle:
                continue
            seen_in_cycle.add(lid)
            if not seen_check(lid):
                continue

            for user_settings, user in user_list:
                if not apply_all_filters(
                    listing,
                    min_price=user_settings.min_price,
                    max_price=user_settings.max_price,
                    model=user_settings.model,
                    backdrop=user_settings.backdrop,
                    pattern=user_settings.pattern,
                    beautiful_id_only=user_settings.beautiful_id_only,
                    median_price=median,
                ):
                    continue

                result = analyze_profit(
                    listing,
                    all_floor_listings=listings,
                    sell_markets=sell_markets_list,
                    floor_markets=floor_markets_list,
                )
                if result is None:
                    continue

                if not result.is_auction and result.profit_pct < user_settings.min_profit_pct:
                    continue
                if result.is_auction and user_settings.max_auction_bid is not None:
                    if listing.price > user_settings.max_auction_bid:
                        continue

                async with session_factory() as db_session:
                    is_dup = await repo.is_listing_seen(
                        db_session, lid, ttl_seconds=settings.LISTINGS_TTL
                    )
                if is_dup:
                    continue

                await _send_alert(bot, user.id, result, user_settings)

                async with session_factory() as db_session:
                    await repo.mark_listing_seen(
                        db_session,
                        lid,
                        listing.market,
                        listing.gift_name,
                        listing.price,
                    )
                    await repo.add_alert(
                        db_session,
                        user.id,
                        lid,
                        result.profit_pct,
                    )
