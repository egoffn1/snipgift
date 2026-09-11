import re

GIFT_URL_PATTERNS = [
    (
        "tonnel",
        re.compile(
            r"tonnel\.network/(?:gift|nft|item)s?/([0-9a-zA-Z_%.-]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "mrkt",
        re.compile(
            r"tgmrkt\.io/(?:gifts?|nft|marketplace)s?/([0-9a-zA-Z_%.-]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "portals",
        re.compile(
            r"portals\.to/(?:shop|gift|nft)s?/([0-9a-zA-Z_%.-]+)",
            re.IGNORECASE,
        ),
    ),
    (
        "fragment",
        re.compile(
            r"fragment\.com/(?:gift|ton/gifts)s?/([0-9a-zA-Z_%.-]+)",
            re.IGNORECASE,
        ),
    ),
]

KNOWN_COLLECTIONS = {
    "heart",
    "diamond",
    "ring",
    "star",
    "crystal",
    "rose",
    "coin",
    "gift",
    "trifles",
    "birthday",
    "dead",
    "humming",
    "sparkle",
}


def parse_gift_url(text: str) -> tuple[str, str, str] | None:
    text = text.strip()
    start = text.find("http")
    if start < 0:
        return None
    url = text[start:]
    for market, pattern in GIFT_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            raw_id = match.group(1)
            gift_id = raw_id.split("/")[0]
            gift_id = gift_id.rstrip("?)&").split("?")[0]
            hint = _name_hint(raw_id)
            return market, gift_id, hint
    return None


def _name_hint(raw_id: str) -> str:
    base = raw_id.split("?")[0].split("&")[0].rstrip("/")
    parts = [p for p in re.split(r"[-_\.\s/]", base) if p]
    if not parts:
        return ""
    for part in parts:
        if part.lower() in KNOWN_COLLECTIONS:
            return part
    if parts[-1].isdigit():
        return parts[-2] if len(parts) > 1 else ""
    return parts[-1]