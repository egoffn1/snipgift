from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from db.models import AlertsHistory, ListingSeen, User, UserSettings
from utils.logger import get_logger

logger = get_logger("db.repo")


async def upsert_user(session, telegram_id: int, username: str | None = None) -> User:
    existing = await session.get(User, telegram_id)
    if existing:
        if username and existing.username != username:
            existing.username = username
        if not existing.is_active:
            existing.is_active = True
        await session.commit()
        return existing
    user = User(id=telegram_id, username=username, is_active=True)
    session.add(user)
    await session.commit()
    return user


async def get_user(session, telegram_id: int) -> User | None:
    return await session.get(User, telegram_id)


async def list_active_users(session) -> list[User]:
    result = await session.execute(select(User).where(User.is_active.is_(True)))
    return list(result.scalars().all())


async def save_settings(session, settings_obj: UserSettings) -> UserSettings:
    session.add(settings_obj)
    await session.commit()
    await session.refresh(settings_obj)
    return settings_obj


async def create_default_settings(
    session, user_id: int, gift_name: str = "", buy_markets: list[str] | None = None
) -> UserSettings:
    settings_obj = UserSettings(
        user_id=user_id,
        gift_name=gift_name or "",
        min_price=0.0,
        max_price=None,
        min_profit_pct=5.0,
        beautiful_id_only=False,
        buy_markets=buy_markets or ["tonnel", "mrkt"],
        sell_markets=["tonnel", "mrkt"],
        floor_markets=[],
        auctions_enabled=False,
        max_auction_bid=None,
        scan_interval=7,
    )
    return await save_settings(session, settings_obj)


async def get_settings_for_user(session, user_id: int) -> UserSettings | None:
    result = await session.execute(
        select(UserSettings)
        .where(UserSettings.user_id == user_id)
        .order_by(UserSettings.id.desc())
    )
    return result.scalars().first()


async def upsert_track_settings(
    session,
    user_id: int,
    gift_name: str,
    *,
    model: str | None = None,
    backdrop: str | None = None,
    pattern: str | None = None,
) -> UserSettings:
    result = await session.execute(
        select(UserSettings).where(
            UserSettings.user_id == user_id,
            UserSettings.gift_name == gift_name,
        )
    )
    existing = result.scalars().first()
    if existing:
        existing.model = model if model is not None else existing.model
        existing.backdrop = (
            backdrop if backdrop is not None else existing.backdrop
        )
        existing.pattern = pattern if pattern is not None else existing.pattern
        existing.paused = False
        await session.commit()
        await session.refresh(existing)
        return existing

    settings_obj = UserSettings(
        user_id=user_id,
        gift_name=gift_name,
        model=model,
        backdrop=backdrop,
        pattern=pattern,
        min_price=0.0,
        max_price=None,
        min_profit_pct=5.0,
        beautiful_id_only=False,
        buy_markets=["tonnel", "mrkt"],
        sell_markets=["tonnel", "mrkt"],
        floor_markets=[],
        auctions_enabled=False,
        max_auction_bid=None,
        scan_interval=7,
    )
    return await save_settings(session, settings_obj)


async def get_all_settings(session) -> list[UserSettings]:
    result = await session.execute(
        select(UserSettings, User)
        .join(User, User.id == UserSettings.user_id)
        .where(User.is_active.is_(True), UserSettings.paused.is_(False))
        .order_by(UserSettings.id.desc())
    )
    rows = result.all()
    return [(row[0], row[1]) for row in rows]


async def is_listing_seen(
    session, listing_id: str, ttl_seconds: int = 3600
) -> bool:
    if ttl_seconds <= 0:
        result = await session.execute(
            select(ListingSeen.id).where(ListingSeen.listing_id == listing_id)
        )
        return result.scalars().first() is not None
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    result = await session.execute(
        select(ListingSeen.id).where(
            ListingSeen.listing_id == listing_id,
            ListingSeen.seen_at >= cutoff,
        )
    )
    return result.scalars().first() is not None


async def mark_listing_seen(
    session,
    listing_id: str,
    market: str,
    gift_name: str,
    price: float,
) -> None:
    session.add(
        ListingSeen(
            listing_id=listing_id,
            market=market,
            gift_name=gift_name,
            price=price,
        )
    )
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.warning("mark_listing_seen failed (%s): %s", listing_id, exc)


async def prune_listings_seen(session, older_than_seconds: int = 86400) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    result = await session.execute(
        delete(ListingSeen).where(ListingSeen.seen_at < cutoff)
    )
    await session.commit()
    return result.rowcount or 0


async def add_alert(
    session, user_id: int, listing_id: str, profit_pct: float
) -> None:
    session.add(
        AlertsHistory(
            user_id=user_id,
            listing_id=listing_id,
            profit_pct=profit_pct,
        )
    )
    await session.commit()


async def get_recent_alerts(session, user_id: int, limit: int = 20):
    result = await session.execute(
        select(AlertsHistory)
        .where(AlertsHistory.user_id == user_id)
        .order_by(AlertsHistory.sent_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
