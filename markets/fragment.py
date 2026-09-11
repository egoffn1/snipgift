import re
from typing import Any

from markets.base import GiftListing, MarketClient, first_present, to_float
from markets.http import request_with_retry
from utils.logger import get_logger

logger = get_logger("markets.fragment")

FRAGMENT_BASE = "https://fragment.com"


class FragmentClient(MarketClient):
    name = "fragment"
    base_url = FRAGMENT_BASE

    def _auth_headers(self) -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html",
        }
        if self.auth_data:
            headers["x-fragment-token"] = self.auth_data
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
        limit: int = 100,
    ) -> list[GiftListing]:
        result = await self._try_api(gift_name, limit, page)
        if result:
            return result
        return await self._try_html_scrape(gift_name)

    async def get_auctions(
        self,
        gift_name: str = "",
        min_price: float = 0.0,
        max_price: float | None = None,
    ) -> list[GiftListing]:
        result = await self._try_api(
            gift_name or "", 50, 1, endpoint="auctions"
        )
        for listing in result:
            listing.is_auction = True
        if result:
            return result
        return await self._try_html_scrape(gift_name, path="/ton/auctions")

    async def _try_api(
        self,
        collection: str,
        limit: int,
        page: int,
        endpoint: str = "gifts",
    ) -> list[GiftListing]:
        payload_body = {
            "method": "getGifts",
            "collection": collection,
            "limit": limit,
            "page": page,
        }
        if endpoint == "auctions":
            payload_body["method"] = "getAuctions"
            payload_body["auction"] = True

        try:
            response = await request_with_retry(
                self.session,
                "post",
                f"{FRAGMENT_BASE}/api/{endpoint}",
                json=payload_body,
                headers=self._auth_headers(),
            )
            if response is None or response.status != 200:
                return []
            body = await response.json()
            if isinstance(body, dict) and "error" in body:
                logger.info(
                    "Fragment API /api/%s returned: %s. "
                    "Fragment requires Telegram Mini App auth (web_app_data) "
                    "to access gift listings API. TODO: implement MTProto session "
                    "or store web_app initData from the Fragment Telegram bot.",
                    endpoint,
                    str(body.get("error"))[:100],
                )
                return []
            return self._parse_api_response(body)
        except Exception as exc:
            logger.debug("Fragment API %s failed: %s", endpoint, exc)
            return []

    @staticmethod
    def _parse_api_response(payload: Any) -> list[GiftListing]:
        if not isinstance(payload, (dict, list)):
            return []
        if isinstance(payload, list):
            items = payload
        else:
            items = None
            for key in ("gifts", "items", "data", "results"):
                candidate = payload.get(key)
                if isinstance(candidate, list):
                    items = candidate
                    break
            if items is None:
                return []
        listings: list[GiftListing] = []
        for raw in items:
            if not isinstance(raw, dict):
                continue
            node = raw.get("gift") or raw
            gid = node.get("id") or node.get("number") or raw.get("id")
            if gid is None:
                continue
            listings.append(GiftListing(
                id=str(gid),
                market="fragment",
                gift_name=str(first_present(node, ["name", "gift_name", "collection"]) or ""),
                model=str(first_present(node, ["model"]) or ""),
                backdrop=str(first_present(node, ["backdrop"]) or ""),
                pattern=str(first_present(node, ["pattern"]) or ""),
                price=to_float(first_present(raw, ["price", "ton_amount", "amount"])),
                url=f"https://fragment.com/gift/{gid}",
                image_url=str(first_present(node, ["image_url", "image"]) or ""),
                raw=raw,
            ))
        return listings

    async def _try_html_scrape(
        self, gift_name: str, path: str = "/ton/gifts"
    ) -> list[GiftListing]:
        try:
            url = f"{FRAGMENT_BASE}{path}"
            response = await request_with_retry(
                self.session, "get", url,
                headers=self._auth_headers(),
                timeout=12,
            )
            if response is None or response.status != 200:
                return []
            html = await response.text()
            return self._parse_gift_html(html, gift_name)
        except Exception as exc:
            logger.debug("Fragment HTML scrape failed: %s", exc)
            return []

    @staticmethod
    def _parse_gift_html(html: str, gift_name: str) -> list[GiftListing]:
        row_pattern = re.compile(
            r'<tr[^>]*class="tm-row-selectable".*?</tr>', re.S
        )
        href_pattern = re.compile(r'href="/gift/(\d+)"')
        ton_pattern = re.compile(
            r'icon-ton["\s>]*([0-9,\.]+)', re.S
        )

        rows = row_pattern.findall(html)
        listings: list[GiftListing] = []
        for row in rows:
            href = href_pattern.search(row)
            if not href:
                continue
            gid = href.group(1)
            price_match = ton_pattern.search(row)
            price = to_float(price_match.group(1)) if price_match else 0.0
            if gift_name and gift_name.lower() not in row.lower():
                continue
            listings.append(GiftListing(
                id=gid,
                market="fragment",
                gift_name=gift_name,
                price=price,
                url=f"https://fragment.com/gift/{gid}",
                raw={"source": "html_scrape"},
            ))
        if listings:
            logger.info(
                "Fragment HTML scrape got %d listings (gift=%s)", len(listings), gift_name
            )
        return listings
