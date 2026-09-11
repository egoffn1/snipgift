import asyncio
from typing import Any

from config import settings
from markets.base import GiftListing, MarketClient
from markets.tonnel import TonnelClient
from markets.mrkt import MrktClient
from markets.portals import PortalsClient
from markets.fragment import FragmentClient
from utils.logger import get_logger

logger = get_logger("markets.aggregator")

AVAILABLE_MARKETS: dict[str, type[MarketClient]] = {
    "tonnel": TonnelClient,
    "mrkt": MrktClient,
    "portals": PortalsClient,
    "fragment": FragmentClient,
}


def create_clients(
    session: Any,
    auth_map: dict[str, str] | None = None,
) -> dict[str, MarketClient]:
    if auth_map is None:
        auth_map = {
            "tonnel": settings.TONNEL_AUTH_DATA,
            "mrkt": settings.MRKT_AUTH_DATA,
            "portals": settings.PORTALS_AUTH_DATA,
            "fragment": settings.FRAGMENT_AUTH_DATA,
        }
    clients: dict[str, MarketClient] = {}
    for name, cls in AVAILABLE_MARKETS.items():
        auth = auth_map.get(name, "")
        clients[name] = cls(session=session, auth_data=auth)
    return clients


async def search_all(
    clients: dict[str, MarketClient],
    enabled_markets: list[str],
    *,
    gift_name: str = "",
    model: str | None = None,
    backdrop: str | None = None,
    pattern: str | None = None,
    min_price: float = 0.0,
    max_price: float | None = None,
    page: int = 1,
    limit: int = 100,
) -> list[GiftListing]:
    active = [m for m in enabled_markets if m in clients]
    if not active:
        active = list(clients.keys())

    async def _safe(market_name: str) -> list[GiftListing]:
        client = clients.get(market_name)
        if client is None:
            return []
        try:
            return await client.search_gifts(
                gift_name=gift_name,
                model=model,
                backdrop=backdrop,
                pattern=pattern,
                min_price=min_price,
                max_price=max_price,
                page=page,
                limit=limit,
            )
        except Exception as exc:
            logger.warning("Market %s search failed: %s", market_name, exc)
            return []

    results = await asyncio.gather(
        *[_safe(m) for m in active],
        return_exceptions=False,
    )
    all_listings: list[GiftListing] = []
    for listings in results:
        all_listings.extend(listings)
    return all_listings


async def fetch_auctions_all(
    clients: dict[str, MarketClient],
    enabled_markets: list[str],
    *,
    gift_name: str = "",
    min_price: float = 0.0,
    max_price: float | None = None,
) -> list[GiftListing]:
    active = [m for m in enabled_markets if m in clients]
    if not active:
        active = list(clients.keys())

    async def _safe(market_name: str) -> list[GiftListing]:
        client = clients.get(market_name)
        if client is None:
            return []
        try:
            return await client.get_auctions(
                gift_name=gift_name,
                min_price=min_price,
                max_price=max_price,
            )
        except Exception as exc:
            logger.warning("Market %s auction fetch failed: %s", market_name, exc)
            return []

    results = await asyncio.gather(
        *[_safe(m) for m in active],
        return_exceptions=False,
    )
    all_listings: list[GiftListing] = []
    for listings in results:
        all_listings.extend(listings)
    return all_listings
