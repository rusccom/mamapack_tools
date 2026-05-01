import re

from .models import ProductRecord
from .recommend_constants import MAX_TITLE_LENGTH
from .text_tools import normalize_space, smart_case_mixed, trim_to_length


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


def build_seo_title(base_title: str) -> str:
    full = " - ".join(piece for piece in [normalize_space(base_title), "mamapack"] if piece)
    if len(full) <= MAX_TITLE_LENGTH:
        return full
    for variant in title_variants(base_title):
        variant = normalize_space(variant).strip(" -.")
        full = f"{variant} - mamapack"
        if len(full) <= MAX_TITLE_LENGTH:
            return full
    return trim_to_length(base_title, MAX_TITLE_LENGTH - 11) + " - mamapack"


def title_variants(base_title: str) -> list[str]:
    return [
        shorten_title(base_title),
        trim_parentheses(base_title),
        trim_tail(base_title),
        trim_to_length(base_title, MAX_TITLE_LENGTH - 11),
    ]


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
