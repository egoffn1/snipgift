from typing import Any

from markets.base import GiftListing, MarketClient, first_present, to_float
from markets.http import request_with_retry
from utils.logger import get_logger

logger = get_logger("markets.portals")

PORTALS_BASE = "https://portals.to"
PORTALS_FIREBASE = "https://identitytoolkit.googleapis.com"


class PortalsClient(MarketClient):
    name = "portals"
    base_url = PORTALS_BASE

    async def search_gifts(
        self,
        gift_name: str = "",
        model: str | None = None,
        backdrop: str | None = None,
        pattern: str | None = None,
        min_price: float = 0.0,
        max_price: float | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> list[GiftListing]:
        return await self._try_fetch("listings", gift_name)

    async def get_auctions(
        self,
        gift_name: str = "",
        min_price: float = 0.0,
        max_price: float | None = None,
    ) -> list[GiftListing]:
        return await self._try_fetch("auctions", gift_name)

    async def _try_fetch(self, endpoint: str, gift_name: str) -> list[GiftListing]:
        try:
            endpoints = [
                f"{PORTALS_BASE}/api/{endpoint}?collection={gift_name}",
                f"{PORTALS_BASE}/api/gifts/{endpoint}",
                f"{PORTALS_BASE}/api/shop?collection={gift_name}",
            ]
            for url in endpoints:
                response = await request_with_retry(
                    self.session, "get", url,
                    timeout=8,
                )
                if response is not None and response.status == 200:
                    try:
                        payload = await response.json()
                        return self._parse_response(payload)
                    except Exception:
                        pass

            logger.info(
                "Portals client: no public REST API found. "
                "Portals is a Firebase-based Telegram Mini App; "
                "gift data is loaded via client SDK, not HTTP API. "
                "TODO: implement via Telegram WebView session or MTProto."
            )
            return []
        except Exception as exc:
            logger.warning("Portals request failed: %s", exc)
            return []

    @staticmethod
    def _parse_response(payload: Any) -> list[GiftListing]:
        if not isinstance(payload, dict):
            return []
        items = None
        for key in ("gifts", "items", "listings", "data", "results", "nodes"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        if not isinstance(items, list):
            return []

        listings: list[GiftListing] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            gift = raw.get("gift") or raw.get("node") or raw
            if not isinstance(gift, dict):
                continue
            gid = (
                gift.get("id")
                or gift.get("gift_id")
                or gift.get("uid")
                or raw.get("id")
            )
            if gid is None:
                continue
            listings.append(GiftListing(
                id=str(gid),
                market="portals",
                gift_name=str(first_present(gift, ["collection", "gift_name", "name"]) or ""),
                model=str(first_present(gift, ["model", "model_name"]) or ""),
                backdrop=str(first_present(gift, ["backdrop", "backdrop_name"]) or ""),
                pattern=str(first_present(gift, ["pattern", "pattern_name"]) or ""),
                price=to_float(
                    first_present(raw, ["price", "cost", "priceTon", "price_ton"])
                ),
                url=f"https://portals.to/shop/{gid}",
                image_url=str(first_present(gift, ["image", "image_url", "img"]) or ""),
                is_auction=bool(raw.get("auction") or raw.get("is_auction")),
                raw=raw,
            ))
        return listings
