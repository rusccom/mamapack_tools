import re

from .models import ProductRecord
from .recommend_constants import FORCE_HANDLE_CHANGE, JUNK_PATTERNS, MAX_HANDLE_WORDS, STOP_HANDLE_WORDS
from .text_tools import slugify


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
    candidate = build_handle(base_title, product.description) or slugify(product.title)
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


def is_junk_token(token: str) -> bool:
    if token in STOP_HANDLE_WORDS:
        return True
    return any(re.search(pattern, token, flags=re.I) for pattern in JUNK_PATTERNS)
