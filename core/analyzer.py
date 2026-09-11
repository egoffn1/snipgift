from dataclasses import dataclass

from markets.base import GiftListing
from core.floor import compute_floor
from utils.fees import get_fee
from utils.logger import get_logger

logger = get_logger("core.analyzer")


@dataclass
class ProfitResult:
    listing: GiftListing
    buy_price: float
    buy_market_fee: float
    net_buy: float
    floor_global: float
    floor_market: str
    floor_sell: float
    sell_fee: float
    net_sell: float
    profit_ton: float
    profit_pct: float
    is_auction: bool


def analyze_profit(
    listing: GiftListing,
    all_floor_listings: list[GiftListing],
    *,
    sell_markets: list[str] | None = None,
    floor_markets: list[str] | None = None,
) -> ProfitResult | None:
    buy_price = listing.price
    if buy_price <= 0:
        return None

    buy_fee = get_fee(listing.market)
    net_buy = buy_price * (1. - buy_fee)

    floor = compute_floor(all_floor_listings, target_markets=floor_markets or None)
    floor_global = floor.global_floor
    floor_market = floor.floor_market

    sell_price_for_calc = floor_global
    sell_market_for_calc = floor_market

    if sell_markets:
        best_sell = 0.0
        best_sell_market = ""
        for sm in sell_markets:
            mp = floor.per_market.get(sm, 0.0)
            if mp > best_sell:
                best_sell = mp
                best_sell_market = sm
        if best_sell > 0:
            sell_price_for_calc = best_sell
            sell_market_for_calc = best_sell_market

    if sell_price_for_calc <= 0:
        return None

    sell_fee = get_fee(sell_market_for_calc) if sell_market_for_calc else 0.0
    net_sell = sell_price_for_calc * (1.0 - sell_fee)
    profit_ton = net_sell - buy_price
    profit_pct = (profit_ton / buy_price * 100) if buy_price > 0 else 0.0

    return ProfitResult(
        listing=listing,
        buy_price=buy_price,
        buy_market_fee=buy_fee,
        net_buy=net_buy,
        floor_global=floor_global,
        floor_market=floor_market,
        floor_sell=sell_price_for_calc,
        sell_fee=sell_fee,
        net_sell=net_sell,
        profit_ton=profit_ton,
        profit_pct=profit_pct,
        is_auction=listing.is_auction,
    )
