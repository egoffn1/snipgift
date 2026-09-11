from dataclasses import dataclass

from markets.base import GiftListing
from utils.logger import get_logger

logger = get_logger("core.floor")


@dataclass
class FloorResult:
    global_floor: float
    per_market: dict[str, float]
    floor_market: str
    sample_sizes: dict[str, int]


def compute_floor(
    listings: list[GiftListing],
    target_markets: list[str] | None = None,
) -> FloorResult:
    per_market_prices: dict[str, list[float]] = {}

    for listing in listings:
        if listing.price <= 0:
            continue
        market = listing.market
        if market not in per_market_prices:
            per_market_prices[market] = []
        per_market_prices[market].append(listing.price)

    if target_markets:
        per_market_prices = {
            m: prices
            for m, prices in per_market_prices.items()
            if m in target_markets
        }

    per_market_floor: dict[str, float] = {}
    sample_sizes: dict[str, int] = {}
    for market, prices in per_market_prices.items():
        sorted_prices = sorted(prices)
        trimmed = sorted_prices[:max(1, len(sorted_prices) // 4)] or sorted_prices
        floor = trimmed[0]
        per_market_floor[market] = floor
        sample_sizes[market] = len(prices)
        logger.debug(
            "Floor %s: %.2f (from %d listings)", market, floor, len(prices)
        )

    global_floor = 0.0
    floor_market = ""
    if per_market_floor:
        global_floor = min(per_market_floor.values())
        for m, f in per_market_floor.items():
            if f == global_floor:
                floor_market = m
                break

    return FloorResult(
        global_floor=global_floor,
        per_market=per_market_floor,
        floor_market=floor_market,
        sample_sizes=sample_sizes,
    )


def median_price(listings: list[GiftListing]) -> float | None:
    prices = sorted(item.price for item in listings if item.price > 0)
    if not prices:
        return None
    mid = len(prices) // 2
    if len(prices) % 2 == 0 and mid > 0:
        return (prices[mid - 1] + prices[mid]) / 2
    return prices[mid]
