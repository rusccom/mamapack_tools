import html
import re
import unicodedata

from .models import ProductRecommendation, ProductRecord


MAX_HANDLE_WORDS = 8
MAX_TITLE_LENGTH = 65
MAX_DESCRIPTION_LENGTH = 155
BRAND_UPPER = {"akuku", "bibs", "b.o.", "canpol", "chicco", "lovi", "medela"}
GENERIC_VENDORS = {"mamapack", "fast bundle"}
POLISH_ASCII = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
SKIP_DESCRIPTION_MARKERS = {
    "aby komplet",
    "wiadomości do sprzedającego",
    "zanim zamówisz",
    "marka:",
    "produkt:",
    "rodzaj:",
}
FORCE_HANDLE_CHANGE = {
    "podstawowy-md",
    "podstawowy-md-1",
    "podstawowy-md-2",
    "torba-do-szpitala-1",
    "torba-do-szpitala-2",
    "torba-do-szpitala-3",
}
STOP_HANDLE_WORDS = {
    "a",
    "copy",
    "dla",
    "i",
    "na",
    "nr",
    "op",
    "oraz",
    "po",
    "rozm",
    "rozmiar",
    "szt",
    "wariant",
    "z",
}
JUNK_PATTERNS = [
    r"\bcopy\b",
    r"\b\d{4,}\b",
    r"\b[0-9]{1,3}/[0-9]{1,3}\b",
    r"\b[a-z]{1,4}\d{2,}[a-z0-9-]*\b",
    r"\b\d+[a-z]{0,2}\+\b",
]


def build_recommendations(products: list[ProductRecord]) -> list[ProductRecommendation]:
    used_handles = set()
    results: list[ProductRecommendation] = []
    for product in products:
        base_title = build_base_title(product)
        handle, handle_reason = choose_handle(products, product, base_title, used_handles)
        seo_title = build_seo_title(base_title)
        seo_description = build_seo_description(base_title, product.description)
        results.append(
            ProductRecommendation(
                product_id=product.id,
                legacy_id=product.legacy_id,
                status=product.status,
                title=product.title,
                handle=product.handle,
                vendor=product.vendor,
                product_type=product.product_type,
                description=product.description,
                current_seo_title=product.seo_title,
                current_seo_description=product.seo_description,
                online_store_url=product.online_store_url,
                recommended_handle=handle,
                recommended_seo_title=seo_title,
                recommended_seo_description=seo_description,
                change_handle=bool(handle_reason),
                handle_change_reason=handle_reason,
                change_seo_title=seo_title != product.seo_title,
                change_seo_description=seo_description != product.seo_description,
            )
        )
    return results


def build_base_title(product: ProductRecord) -> str:
    cleaned = normalize_space(product.title)
    cleaned = re.sub(r"\bDLA\s+DLA\b", "dla", cleaned, flags=re.I)
    cleaned = re.sub(r"\bNOWORODKA\s*-\s*gotowa wyprawka\b", "noworodka - gotowa wyprawka", cleaned, flags=re.I)
    cleaned = cleaned.replace("JENORAZOWY", "JEDNORAZOWY").replace("Jenorazowy", "Jednorazowy")
    cleaned = smart_case_mixed(cleaned)
    cleaned = cleaned.replace("60X90cm", "60x90 cm")
    cleaned = cleaned.replace("40X60cm", "40x60 cm")
    cleaned = re.sub(r"\((\d+)\s*szt\.?\)", r"\1 szt.", cleaned, flags=re.I)
    cleaned = re.sub(r"(\d+)\s*ML\b", r"\1 ml", cleaned)
    cleaned = re.sub(r"(\d+)\s*CM\b", r"\1 cm", cleaned)
    cleaned = re.sub(r"\s*\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s[-–]\s(?=$)", "", cleaned)
    cleaned = re.sub(r"[-–]{2,}", "-", cleaned)
    return normalize_space(cleaned).strip(" -.")


def choose_handle(
    products: list[ProductRecord],
    product: ProductRecord,
    base_title: str,
    used_handles: set[str],
) -> tuple[str, str]:
    reason = handle_problem_reason(product.handle)
    if not reason:
        used_handles.add(product.handle)
        return product.handle, ""
    return unique_handle(products, product, base_title, used_handles), reason


def unique_handle(products: list[ProductRecord], product: ProductRecord, base_title: str, used_handles: set[str]) -> str:
    existing = {item.handle for item in products if item.id != product.id}
    candidate = build_handle(base_title, product.description)
    if not candidate:
        candidate = slugify(product.title)
    if candidate == product.handle:
        used_handles.add(candidate)
        return candidate
    suffix = 2
    while candidate in used_handles or candidate in existing:
        candidate = f"{build_handle(base_title, product.description)}-{suffix}"
        suffix += 1
    used_handles.add(candidate)
    return candidate


def handle_problem_reason(handle: str) -> str:
    if handle in FORCE_HANDLE_CHANGE:
        return "placeholder_handle"
    if re.fullmatch(r"bundle-product-\d+", handle):
        return "placeholder_handle"
    if "copy" in handle:
        return "copy_handle"
    if re.search(r"-[123]$", handle):
        return "variant_suffix_handle"
    return ""


def build_handle(base_title: str, description: str) -> str:
    parts = tokenize_handle(base_title)
    if len(parts) < 3:
        parts.extend(tokenize_handle(description))
    unique = []
    for part in parts:
        if part in unique or part in STOP_HANDLE_WORDS:
            continue
        unique.append(part)
        if len(unique) >= MAX_HANDLE_WORDS:
            break
    return "-".join(unique)


def tokenize_handle(text: str) -> list[str]:
    source = slugify(text)
    tokens = [token for token in source.split("-") if token]
    return [token for token in tokens if not is_junk_token(token)]


def build_seo_title(base_title: str) -> str:
    pieces = [normalize_space(base_title), "mamapack"]
    full = " – ".join(piece for piece in pieces if piece)
    if len(full) <= MAX_TITLE_LENGTH:
        return full
    variants = [
        shorten_title(base_title),
        trim_parentheses(base_title),
        trim_tail(base_title),
        trim_to_length(base_title, MAX_TITLE_LENGTH - 11),
    ]
    for variant in variants:
        variant = normalize_space(variant).strip(" -.")
        full = f"{variant} – mamapack"
        if len(full) <= MAX_TITLE_LENGTH:
            return full
    return trim_to_length(base_title, MAX_TITLE_LENGTH - 11) + " – mamapack"


def build_seo_description(base_title: str, description: str) -> str:
    lead = first_good_sentence(description)
    if not lead:
        return trim_to_length(
            f"{base_title}. Sprawdź szczegóły produktu i zamów online w mamapack.",
            MAX_DESCRIPTION_LENGTH,
        )
    lead = normalize_space(lead)
    if normalized_identity(base_title) == normalized_identity(lead):
        return trim_to_length(
            append_sentence(lead, "Sprawdź szczegóły produktu i zamów online w mamapack."),
            MAX_DESCRIPTION_LENGTH,
        )
    if normalized_identity(base_title) not in normalized_identity(lead):
        lead = append_sentence(base_title, lead)
    return trim_to_length(lead, MAX_DESCRIPTION_LENGTH)


def first_good_sentence(description: str) -> str:
    for block in description_blocks(description):
        if any(marker in block.lower() for marker in SKIP_DESCRIPTION_MARKERS):
            continue
        if len(block) >= 45:
            return block
    return ""


def clean_description(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[•✅]+", " ", text)
    return normalize_space(text)


def description_blocks(text: str) -> list[str]:
    cleaned = clean_description(text)
    raw_blocks = re.split(r"(?:\n+|(?<=[.!?])\s+)", cleaned)
    blocks = []
    for block in raw_blocks:
        candidate = normalize_space(block).strip(" -")
        if not candidate:
            continue
        if candidate.count(":") >= 2:
            continue
        if "  " in candidate:
            continue
        blocks.append(candidate)
    return blocks


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
        head = re.sub(r"[A-Za-z]+", lambda m: m.group(0).lower(), token)
        return head
    if token.isupper() or is_mostly_upper(token):
        return token.lower().capitalize()
    return token


def trim_parentheses(value: str) -> str:
    trimmed = re.sub(r"\s*\([^)]*\)", "", value)
    trimmed = re.sub(r"\s[-–]\s(?=$)", "", trimmed)
    return normalize_space(trimmed).strip(" -.") or normalize_space(value)


def shorten_title(value: str) -> str:
    title = trim_parentheses(value)
    title = re.sub(r"\bgotowa wyprawka\b", "wyprawka", title, flags=re.I)
    title = re.sub(r"\bjednorazowe\b", "", title, flags=re.I)
    title = re.sub(r"\bpielęgnacyjne\b", "", title, flags=re.I)
    title = re.sub(r"\s[-–]\s(?=$)", "", title)
    return normalize_space(title).strip(" -.")


def trim_tail(value: str) -> str:
    parts = re.split(r"\s[-–]\s", value)
    if len(parts) <= 1:
        return normalize_space(value)
    return normalize_space(" - ".join(parts[:2])).strip(" -.")


def trim_to_length(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    truncated = value[:length].rsplit(" ", 1)[0]
    return truncated.rstrip(" -–,.;:")


def is_junk_token(token: str) -> bool:
    if token in STOP_HANDLE_WORDS:
        return True
    return any(re.search(pattern, token, flags=re.I) for pattern in JUNK_PATTERNS)


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
