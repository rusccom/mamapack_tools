import re
from collections import defaultdict

from shared.text_tools import short_vendor, slugify, smart_title, trim_sku
from .models import ShopifyVariantDraft


GROUP_OVERRIDES = {
    "212110101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CAPEL BLUSH MIX",
    "222110101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CAPEL BLUSH MIX",
    "212112101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CHAMOMILE LAWN/VIOLET SKY MIX",
    "222112101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CHAMOMILE LAWN/VIOLET SKY MIX",
    "2111417": "SMOCZEK 2 PAK LATEX ANATOMICZNY KOŚĆ SŁONIOWA/RÓŻ",
    "2211417": "SMOCZEK 2 PAK LATEX ANATOMICZNY KOŚĆ SŁONIOWA/RÓŻ",
    "11017101": "SMOCZEK STUDIO KOLOR 2 PAK LATEX KOŚĆ SŁONIOWA/JAŚMIN",
    "12017101": "SMOCZEK STUDIO KOLOR 2 PAK LATEX KOŚĆ SŁONIOWA/JAŚMIN",
    "11017103": "SMOCZEK STUDIO KOLOR 2 PAK LATEX JAŚMIN/RÓŻ",
    "12017103": "SMOCZEK STUDIO KOLOR 2 PAK LATEX JAŚMIN/RÓŻ",
    "11033101": "SMOCZEK MUMINKI MARZĄCY 2 PAK LATEX BABY PINK",
    "12033101": "SMOCZEK MUMINKI MARZĄCY 2 PAK LATEX BABY PINK",
}


def clean_title(title, code):
    if code in GROUP_OVERRIDES:
        return GROUP_OVERRIDES[code]
    cleaned = re.sub(r"^\S+\s+\S+\s+", "", title.upper()).strip()
    cleaned = re.sub(r"\bROZMIAR\s+[0-9A-Z]+\b", "", cleaned)
    cleaned = re.sub(r"\bSIZE\s+[0-9A-Z]+\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" -/")


def extract_size(title):
    pattern = r"\b(?:ROZMIAR|SIZE)\s+([0-9A-Z]+)\b"
    match = re.search(pattern, title.upper())
    return match.group(1) if match else ""


def product_type(variant):
    if "SMOCZEK" in variant.title.upper():
        return "Pacifier"
    return variant.source_category or "Catalog Product"


def display_title(vendor, group_key):
    return smart_title(f"{vendor} {group_key}".strip())


def fallback_sku(vendor, handle, option_value):
    tail = "-".join(handle.split("-")[-2:]) or "item"
    raw = f"{short_vendor(vendor)}-{option_value or 'STD'}-{tail}".upper()
    raw = raw.replace(" ", "-").replace("/", "-")
    return trim_sku(raw)


def build_variant(product_handle, variant, option_value):
    sku = variant.supplier_sku or fallback_sku(variant.vendor, product_handle, option_value)
    file_key = slugify(variant.image_urls[0]) if variant.image_urls else slugify(variant.detail_url)
    return ShopifyVariantDraft(
        option_value=option_value or "Default Title",
        sku=sku,
        barcode=variant.barcode,
        price=variant.price,
        detail_url=variant.detail_url,
        source_code=variant.source_code,
        source_title=variant.title,
        file_key=file_key,
        source_sku=variant.supplier_sku,
    )


def grouped_variants(variants):
    buckets = defaultdict(list)
    for variant in variants:
        key = clean_title(variant.title, variant.source_code)
        buckets[key].append((extract_size(variant.title), variant))
    return buckets


def ordered_variants(group):
    group.sort(key=lambda item: (item[0] == "", item[0], item[1].supplier_sku))
    return group


def build_product_stub(group_key, group):
    sample = group[0][1]
    title = display_title(sample.vendor, group_key)
    handle = slugify(title)
    option_values = tuple(item[0] for item in group if item[0]) or ("Default Title",)
    option_name = "Size" if any(item[0] for item in group) else "Title"
    file_map = {}
    variants = []
    for size_value, variant in group:
        draft = build_variant(handle, variant, size_value)
        if draft.file_key and variant.image_urls:
            file_map[draft.file_key] = variant.image_urls[0]
        variants.append(draft)
    tags = tuple(dict.fromkeys([sample.vendor, product_type(sample), sample.main_category, sample.source_category]))
    links = tuple(dict.fromkeys(item[1].detail_url for item in group))
    return handle, title, tags, option_name, option_values, tuple(variants), links, file_map
