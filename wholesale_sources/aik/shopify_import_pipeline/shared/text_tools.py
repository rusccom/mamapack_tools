import re
import unicodedata


POLISH_ASCII = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def ascii_text(value):
    plain = value.translate(POLISH_ASCII)
    normalized = unicodedata.normalize("NFKD", plain)
    return normalized.encode("ascii", "ignore").decode("ascii")


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text(value).lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def short_vendor(value):
    letters = re.sub(r"[^A-Z0-9]", "", ascii_text(value).upper())
    return (letters or "SKU")[:8]


def format_token(word):
    if re.search(r"\d", word):
        return word.upper()
    if word.upper() in {"BIBS", "AICO", "SKU", "EAN"}:
        return word.upper()
    return word.lower().capitalize()


def format_piece(piece):
    return "/".join(format_token(item) for item in piece.split("/"))


def smart_title(value):
    return " ".join(format_piece(word) for word in value.split())


def list_text(items):
    values = [item for item in items if item]
    return ", ".join(values)


def trim_sku(value):
    return re.sub(r"-{2,}", "-", value.strip("-"))[:40]
