from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GiftListing:
    id: str
    market: str
    gift_name: str
    model: str = ""
    backdrop: str = ""
    pattern: str = ""
    price: float = 0.0
    currency: str = "TON"
    url: str = ""
    image_url: str = ""
    is_auction: bool = False
    auction_end: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def listing_id(self) -> str:
        return f"{self.market}:{self.id}"


def to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        value = value.strip().replace(" ", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return 0.0
    if isinstance(value, dict):
        amount = value.get("amount") or value.get("ton") or value.get("value")
        if amount is not None:
            return to_float(amount)
        symbol = str(value.get("symbol", "")).upper()
        if symbol in ("TON", "USD", "USDT"):
            return to_float(value.get("amount", 0))
    return 0.0


def first_present(item: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None


class MarketClient(ABC):
    name: str = "base"
    base_url: str = ""

    def __init__(self, session: Any, auth_data: str = "") -> None:
        self.session = session
        self.auth_data = auth_data

    @abstractmethod
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
        raise NotImplementedError

    async def get_auctions(
        self,
        gift_name: str = "",
        min_price: float = 0.0,
        max_price: float | None = None,
    ) -> list[GiftListing]:
        return []

    async def healthcheck(self) -> bool:
        return False
