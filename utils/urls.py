import re

TELEGRAM_MARKET = "telegram"

GIFT_URL_PATTERNS = [
    (
        TELEGRAM_MARKET,
        re.compile(
            r"(?:t\.me|telegram\.me)/nft/([^/\s?&]+)",
            re.IGNORECASE,
        ),
    ),
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
    "winterwreath",
}

_CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])")


def friendly_name(slug: str) -> str:
    """Turn a Telegram gift slug (WinterWreath / Year2024) into a display name."""
    if not slug:
        return ""
    spaced = _CAMEL_RE.sub(" ", slug)
    words = [w for w in re.split(r"[\s\-_]+", spaced) if w]
    if not words:
        return ""
    return " ".join(w.title() if not w.isupper() else w for w in words)


def parse_gift_url(text: str) -> tuple[str, str, str] | None:
    text = text.strip()
    start = text.find("http")
    if start < 0:
        return None
    url = text[start:]
    for market, pattern in GIFT_URL_PATTERNS:
        match = pattern.search(url)
        if not match:
            continue
        raw = match.group(1)
        raw = raw.rstrip("?)&").split("?")[0]
        if market == TELEGRAM_MARKET:
            m = re.match(r"^(.*)-(\d+)$", raw)
            if m:
                return market, m.group(2), m.group(1)
            return market, "0", raw
        gift_id = raw.split("/")[0]
        gift_id = gift_id.rstrip("?)&").split("?")[0]
        hint = _name_hint(raw)
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