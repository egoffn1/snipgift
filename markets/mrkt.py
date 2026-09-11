from typing import Any

from markets.base import GiftListing, MarketClient, first_present, to_float
from markets.http import request_with_retry
from utils.logger import get_logger

logger = get_logger("markets.mrkt")

MRKT_API = "https://api.tgmrkt.io"


class MrktClient(MarketClient):
    name = "mrkt"
    base_url = "https://tgmrkt.io"

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        }
        if self.auth_data:
            headers["authorization"] = f"Bearer {self.auth_data}"
        return headers

    async def search_gifts(
        self,
        gift_name: str = "",
        model: str | None = None,
        backdrop: str | None = None,
        pattern: str | None = None,
        min_price: float = 0.0,
        max_price: float | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> list[GiftListing]:
        body: dict[str, Any] = {
            "collectionNames": [gift_name] if gift_name else [],
            "modelNames": [model] if model else [],
            "backdropNames": [backdrop] if backdrop else [],
            "patternNames": [pattern] if pattern else [],
            "minPrice": min_price or 0.01,
            "maxPrice": max_price if max_price is not None else 999999,
            "ordering": "price",
            "number": limit,
            "page": page,
        }
        try:
            response = await request_with_retry(
                self.session, "post", f"{MRKT_API}/api/v1/gifts/saling", json=body,
                headers=self._headers(),
            )
            if response is None or response.status != 200:
                buf = await response.text() if response is not None else ""
                logger.warning(
                    "MRKT saling status=%s body=%s",
                    response.status if response else "N/A",
                    buf[:300],
                )
                return []
            payload = await response.json()
        except Exception as exc:
            logger.warning("MRKT saling request failed: %s", exc)
            return []

        return self._parse_payload(payload)

    async def get_auctions(
        self,
        gift_name: str = "",
        min_price: float = 0.0,
        max_price: float | None = None,
    ) -> list[GiftListing]:
        body = {
            "collectionNames": [gift_name] if gift_name else [],
            "minPrice": min_price or 0.01,
            "maxPrice": max_price if max_price is not None else 999999,
            "auctionsOnly": True,
            "number": 50,
        }
        try:
            response = await request_with_retry(
                self.session, "post", f"{MRKT_API}/api/v1/gifts/auctions", json=body,
                headers=self._headers(),
            )
            if response is None or response.status != 200:
                logger.warning(
                    "MRKT auctions status=%s",
                    response.status if response else "N/A",
                )
                return []
            payload = await response.json()
        except Exception as exc:
            logger.warning("MRKT auctions request failed: %s", exc)
            return []

        listings = self._parse_payload(payload)
        for listing in listings:
            listing.is_auction = True
        return listings

    async def get_gift_by_id(self, gift_id: str) -> GiftListing | None:
        try:
            listings = await self.search_gifts(limit=300)
        except Exception as exc:
            logger.debug("MRKT get_gift_by_id search failed: %s", exc)
            return None
        for listing in listings:
            if listing.id == gift_id:
                return listing
        return None

    @staticmethod
    def _parse_payload(payload: Any) -> list[GiftListing]:
        if not isinstance(payload, dict):
            return []
        items = None
        for key in ("gifts", "items", "listings", "data", "results"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        if items is None and isinstance(payload.get("data"), dict):
            inner = payload["data"]
            for key in ("gifts", "items", "listings", "list"):
                if isinstance(inner.get(key), list):
                    items = inner[key]
                    break
        if not isinstance(items, list):
            return []

        listings: list[GiftListing] = []
        for raw in items:
            parsed = MrktClient._parse_item(raw)
            if parsed is not None:
                listings.append(parsed)
        return listings

    @staticmethod
    def _parse_item(raw: Any) -> GiftListing | None:
        if not isinstance(raw, dict):
            return None
        gift = raw.get("gift")
        node = gift if isinstance(gift, dict) else raw

        gift_id = first_present(
            node, ["id", "gift_id", "token_id", "nft_id", "slug"]
        )
        if gift_id is None:
            gift_id = first_present(raw, ["id", "listing_id", "sale_id"])
        if gift_id is None:
            return None

        name = first_present(node, ["collection", "collection_name", "gift_name", "name"])
        raw_price = first_present(raw, ["price", "priceTon", "buy_price", "cost"])
        if raw_price is None:
            price_obj = raw.get("price")
            if isinstance(price_obj, dict):
                raw_price = first_present(price_obj, ["amount", "ton", "value"])
        price = to_float(raw_price)

        image_url = first_present(
            node,
            ["image_url", "image", "img", "preview", "photo"],
        )
        url = f"https://tgmrkt.io/gifts/{gift_id}"
        return GiftListing(
            id=str(gift_id),
            market="mrkt",
            gift_name=str(name or ""),
            model=str(first_present(node, ["model", "model_name"]) or ""),
            backdrop=str(first_present(node, ["backdrop", "backdrop_name"]) or ""),
            pattern=str(first_present(node, ["pattern", "pattern_name"]) or ""),
            price=price,
            url=url,
            image_url=str(image_url or ""),
            is_auction=bool(
                raw.get("auction") or raw.get("is_auction") or raw.get("isAuction")
            ),
            raw=raw,
        )
