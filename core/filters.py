from markets.base import GiftListing
from utils.id_beauty import is_beautiful_id
from utils.logger import get_logger

logger = get_logger("core.filters")


def passes_price_filter(
    listing: GiftListing,
    min_price: float,
    max_price: float | None,
) -> bool:
    price = listing.price
    if price <= 0:
        return False
    if price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def _attr_matches(listing_value: str, expected: str | None) -> bool:
    if not expected or expected.lower() in ("any", "любой"):
        return True
    return (listing_value or "").strip().lower() == expected.lower()


def passes_attribute_filter(
    listing: GiftListing,
    model: str | None = None,
    backdrop: str | None = None,
    pattern: str | None = None,
) -> bool:
    return (
        _attr_matches(listing.model, model)
        and _attr_matches(listing.backdrop, backdrop)
        and _attr_matches(listing.pattern, pattern)
    )


def passes_beautiful_id_filter(
    listing: GiftListing,
    beautiful_id_only: bool,
) -> bool:
    if not beautiful_id_only:
        return True
    return is_beautiful_id(listing.id)


def is_outlier(
    listing: GiftListing,
    median_price: float | None,
    deviation_threshold: float = 0.5,
) -> bool:
    if median_price is None or median_price <= 0:
        return False
    if listing.price <= 0:
        return False
    ratio = (median_price - listing.price) / median_price
    if ratio > deviation_threshold:
        logger.debug(
            "Outlier listing %s: price %.2f vs median %.2f (%.1f%% below)",
            listing.listing_id,
            listing.price,
            median_price,
            ratio * 100,
        )
        return True
    return False


def apply_all_filters(
    listing: GiftListing,
    *,
    min_price: float = 0.0,
    max_price: float | None = None,
    model: str | None = None,
    backdrop: str | None = None,
    pattern: str | None = None,
    beautiful_id_only: bool = False,
    median_price: float | None = None,
) -> bool:
    if not passes_price_filter(listing, min_price, max_price):
        return False
    if not passes_attribute_filter(listing, model, backdrop, pattern):
        return False
    if not passes_beautiful_id_filter(listing, beautiful_id_only):
        return False
    if is_outlier(listing, median_price):
        return False
    return True
