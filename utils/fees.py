import os

DEFAULT_FEES: dict[str, float] = {
    "tonnel": 0.10,
    "mrkt": 0.05,
    "portals": 0.10,
    "fragment": 0.00,
}


def get_fees() -> dict[str, float]:
    fees = dict(DEFAULT_FEES)
    for market, default in DEFAULT_FEES.items():
        env_value = os.getenv(f"FEE_{market.upper()}")
        if env_value is not None:
            try:
                fees[market] = float(env_value)
            except ValueError:
                pass
    return fees


def get_fee(market: str) -> float:
    return get_fees().get(market, 0.0)


def net_after_sell(price: float, market: str) -> float:
    return price * (1.0 - get_fee(market))
