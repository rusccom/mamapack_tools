import html
import re

from .recommend_constants import MAX_DESCRIPTION_LENGTH, SKIP_DESCRIPTION_MARKERS
from .text_tools import append_sentence, normalize_space, normalized_identity, trim_to_length


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
