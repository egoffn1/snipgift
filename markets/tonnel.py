from typing import Any

from markets.base import GiftListing, MarketClient, first_present, to_float
from markets.http import request_with_retry
from utils.logger import get_logger

logger = get_logger("markets.tonnel")

TONNEL_API = "https://gifts2.tonnel.network/api"


class TonnelClient(MarketClient):
    name = "tonnel"
    base_url = "https://tonnel.network"

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
        price_range: list = [min_price, 999999]
        if max_price is not None:
            price_range = [min_price, max_price]

        body = {
            "authData": self.auth_data,
            "filter": {
                "gift_name": gift_name or "",
                "model": model or "",
                "backdrop": backdrop or "",
                "pattern": pattern or "",
            },
            "page": page,
            "limit": limit,
            "sort": "price-asc",
            "price_range": price_range,
        }
        try:
            response = await request_with_retry(
                self.session, "post", f"{TONNEL_API}/pageGifts", json=body
            )
            if response is None or response.status != 200:
                buf = await response.text() if response is not None else ""
                logger.warning(
                    "Tonnel pageGifts status=%s body=%s",
                    response.status if response else "N/A",
                    buf[:300],
                )
                return []
            payload = await response.json()
        except Exception as exc:
            logger.warning("Tonnel pageGifts request failed: %s", exc)
            return []

        return self._parse_page(payload)

    async def get_auctions(
        self,
        gift_name: str = "",
        min_price: float = 0.0,
        max_price: float | None = None,
    ) -> list[GiftListing]:
        body = {
            "authData": self.auth_data,
            "filter": {"gift_name": gift_name or ""},
            "page": 1,
            "limit": 50,
        }
        try:
            response = await request_with_retry(
                self.session, "post", f"{TONNEL_API}/getAuctions", json=body
            )
            if response is None or response.status != 200:
                logger.warning(
                    "Tonnel getAuctions status=%s",
                    response.status if response else "N/A",
                )
                return []
            payload = await response.json()
        except Exception as exc:
            logger.warning("Tonnel getAuctions request failed: %s", exc)
            return []

        listings = self._parse_page(payload)
        for listing in listings:
            listing.is_auction = True
        return listings

    async def get_gift_by_id(self, gift_id: str) -> GiftListing | None:
        try:
            listings = await self.search_gifts(limit=500)
        except Exception as exc:
            logger.debug("Tonnel get_gift_by_id search failed: %s", exc)
            return None
        for listing in listings:
            if listing.id == gift_id:
                return listing
        return None

    @staticmethod
    def _parse_page(payload: Any) -> list[GiftListing]:
        if not isinstance(payload, dict):
            return []
        items = None
        for key in ("data", "gifts", "items", "list", "result", "records"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        if items is None:
            for key in ("data", "gifts", "items", "result"):
                wrapped = payload.get(key)
                if isinstance(wrapped, dict):
                    for inner in ("items", "list", "records", "rows"):
                        if isinstance(wrapped.get(inner), list):
                            items = wrapped[inner]
                            break
                if items is not None:
                    break
        if not isinstance(items, list):
            return []

        listings: list[GiftListing] = []
        for raw in items:
            parsed = TonnelClient._parse_item(raw)
            if parsed is not None:
                listings.append(parsed)
        return listings

    @staticmethod
    def _parse_item(raw: Any) -> GiftListing | None:
        if not isinstance(raw, dict):
            return None
        gift = raw.get("gift")
        if isinstance(gift, dict):
            node = gift
        else:
            node = raw

        gift_id = first_present(node, ["id", "gift_id", "token_id", "nft_id", "uid"])
        if gift_id is None:
            gift_id = first_present(raw, ["id", "gift_id", "token_id", "listing_id"])
        if gift_id is None:
            return None

        name = first_present(node, ["gift_name", "name", "title", "collection"])
        raw_price = first_present(
            raw, ["price", "cost", "amount", "buy_price", "stick_price", "sell_price"]
        )
        price = to_float(raw_price)

        image_url = first_present(
            node,
            ["image", "image_url", "imageLink", "img", "photo", "gift_url"],
        )

        seller = raw.get("seller") or raw.get("owner")
        url = f"https://tonnel.network/gift/{gift_id}"
        if isinstance(seller, dict):
            pass
        return GiftListing(
            id=str(gift_id),
            market="tonnel",
            gift_name=str(name or ""),
            model=str(first_present(node, ["model", "model_name"]) or ""),
            backdrop=str(first_present(node, ["backdrop", "backdrop_name"]) or ""),
            pattern=str(first_present(node, ["pattern", "pattern_name", "token_type"]) or ""),
            price=price,
            url=url,
            image_url=str(image_url or ""),
            raw=raw,
        )
