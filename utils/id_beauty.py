import re


def is_palindrome(text: str) -> bool:
    return text == text[::-1]


def is_beautiful_id(raw_id: str | int) -> bool:
    text = str(raw_id).strip()
    if not text:
        return False
    if text.startswith("-"):
        text = text[1:]
    if not text.isdigit():
        return False
    num = int(text)
    if num < 1000:
        return True
    if is_palindrome(text):
        return True
    for length in (2, 3, 4):
        pattern = re.compile(r"^(\d)\1{%d}$" % (length - 1))
        if pattern.match(text):
            return True
    if (num % 1111) == 0:
        return True
    significant = text.lstrip("0")
    if significant and all(c == significant[0] for c in significant):
        return True
    return False
