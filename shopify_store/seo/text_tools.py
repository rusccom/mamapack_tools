import re
import unicodedata

from .recommend_constants import BRAND_UPPER, POLISH_ASCII


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def is_mostly_upper(value: str) -> bool:
    letters = [ch for ch in value if ch.isalpha()]
    if not letters:
        return False
    return sum(ch.isupper() for ch in letters) / len(letters) > 0.65


def smart_case_mixed(value: str) -> str:
    words = re.split(r"(\s+)", value)
    return "".join(convert_word(word) if not word.isspace() else word for word in words)


def smart_case(value: str) -> str:
    words = re.split(r"(\s+)", value.lower())
    return "".join(smart_piece(word) if not word.isspace() else word for word in words)


def smart_piece(word: str) -> str:
    if re.search(r"\d", word):
        return word.upper()
    if word.lower() in BRAND_UPPER:
        return word.upper()
    return word.capitalize()


def convert_word(word: str) -> str:
    if not word:
        return word
    parts = re.split(r"([/-])", word)
    return "".join(convert_token(part) if part not in {"/", "-"} else part for part in parts)


def convert_token(token: str) -> str:
    letters = [ch for ch in token if ch.isalpha()]
    if not letters:
        return token
    if token.lower() in BRAND_UPPER:
        return token.upper()
    if any(ch.isdigit() for ch in token):
        return re.sub(r"[A-Za-z]+", lambda match: match.group(0).lower(), token)
    if token.isupper() or is_mostly_upper(token):
        return token.lower().capitalize()
    return token


def trim_to_length(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    truncated = value[:length].rsplit(" ", 1)[0]
    return truncated.rstrip(" -–,.;:")


def slugify(value: str) -> str:
    text = ascii_text(value).lower()
    text = re.sub(r"(\d)([a-z])", r"\1-\2", text)
    text = re.sub(r"([a-z])(\d)", r"\1-\2", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text)


def ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", (value or "").translate(POLISH_ASCII))
    return normalized.encode("ascii", "ignore").decode("ascii")


def normalized_identity(value: str) -> str:
    return slugify(value).replace("-", "")


def append_sentence(first: str, second: str) -> str:
    head = first.rstrip(" .")
    tail = second.lstrip(" .")
    return f"{head}. {tail}"
