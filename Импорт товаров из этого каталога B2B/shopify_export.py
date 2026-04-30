import csv
import html
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus, urljoin

from app_settings import BASE_URL, GROUP_OVERRIDES, SEARCH_PATH, SHOPIFY_HEADERS, SIZE_OVERRIDES


def normalize_key(title, code):
    if code in GROUP_OVERRIDES:
        return GROUP_OVERRIDES[code]
    key = re.sub(r"^BIBS\s+\S+\s+", "", title.upper()).strip()
    key = re.sub(r"\bROZMIAR\s+[123]\b", "", key)
    swaps = [(r"\bRÓŻOWY\b", "RÓŻ"), (r"\bRÓŻOWA\b", "RÓŻ"), (r"\bWANILA\b", "WANILIA")]
    swaps += [(r"\bSZAŁWIOWY\b", "SZAŁWIA"), (r"\bMARZĄCE\b", "MARZĄCY"), (r"\b2\s+PACK\b", "2 PAK")]
    for pattern, replacement in swaps:
        key = re.sub(pattern, replacement, key)
    return re.sub(r"\s*/\s*", "/", re.sub(r"\s+", " ", key)).strip()


def variant_size(title, code):
    match = re.search(r"ROZMIAR\s+([123])", title)
    if match:
        return match.group(1)
    return SIZE_OVERRIDES.get(code, "")


def material_tag(group_key):
    if "LATEX" in group_key:
        return "Latex"
    if "SILIKON" in group_key:
        return "Silicone"
    return "Pacifier"


def display_title(group_key):
    return "BIBS " + group_key.lower().title()


def polish_ascii(text):
    source = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
    target = "acelnoszzACELNOSZZ"
    return text.translate(str.maketrans(source, target))


def handle_slug(text):
    ascii_text = polish_ascii(text)
    ascii_text = unicodedata.normalize("NFKD", ascii_text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def fallback_sku(variant):
    size = variant["size"] or "std"
    suffix = handle_slug(variant["group_key"]).split("-")[-2:]
    return f"BIBS-{size}-{'-'.join(suffix)}".upper().strip("-")


def source_links_html(variants):
    search_base = urljoin(BASE_URL, SEARCH_PATH)
    lines = []
    for variant in variants:
        label = f"Size {variant['size']}" if variant["size"] else variant["sku"] or variant["code"]
        search_url = f"{search_base}?search={quote_plus(variant['code'])}"
        detail_url = html.escape(variant["detail_url"])
        search_url = html.escape(search_url)
        lines.append(f'<li>{html.escape(label)}: <a href="{detail_url}">detail</a> | <a href="{search_url}">search by code</a></li>')
    return "".join(lines)


def body_html(title, group_key, variants):
    sizes = ", ".join(v["size"] for v in variants if v["size"]) or "Default"
    intro = f"<p>{html.escape(title)} prepared from the AICO B2B catalog for Shopify import.</p>"
    meta = f"<ul><li>Brand: BIBS</li><li>Category: Pacifier</li><li>Material: {html.escape(material_tag(group_key))}</li><li>Available sizes: {html.escape(sizes)}</li></ul>"
    links = "<p>Original AICO links:</p><ul>" + source_links_html(variants) + "</ul>"
    return intro + meta + links


def group_variants(variants):
    grouped = defaultdict(list)
    for variant in variants:
        variant["group_key"] = normalize_key(variant["title"], variant["code"])
        variant["size"] = variant_size(variant["title"], variant["code"])
        grouped[variant["group_key"]].append(variant)
    for group in grouped.values():
        group.sort(key=lambda item: (item["size"] == "", item["size"], item["sku"]))
    return grouped


def product_rows(handle, title, group_key, variants):
    rows = []
    option_name = "Size" if any(v["size"] for v in variants) else "Title"
    tags = f"BIBS,Pacifier,AICO,{material_tag(group_key)}"
    body = body_html(title, group_key, variants)
    for index, variant in enumerate(variants):
        row = {header: "" for header in SHOPIFY_HEADERS}
        row["Handle"] = handle
        row["Option1 Name"] = option_name
        row["Option1 Value"] = variant["size"] or "Default Title"
        row["Variant SKU"] = variant["sku"] or fallback_sku(variant)
        row["Variant Inventory Policy"] = "deny"
        row["Variant Fulfillment Service"] = "manual"
        row["Variant Price"] = variant["price"]
        row["Variant Requires Shipping"] = "TRUE"
        row["Variant Taxable"] = "TRUE"
        row["Variant Barcode"] = variant["barcode"]
        row["Image Src"] = variant["image_url"]
        row["Image Alt Text"] = title if not variant["size"] else f"{title} - Size {variant['size']}"
        if index == 0:
            row["Title"] = title
            row["Body (HTML)"] = body
            row["Vendor"] = "BIBS"
            row["Type"] = "Pacifier"
            row["Tags"] = tags
            row["Published"] = "FALSE"
        rows.append(row)
    return rows


def csv_rows(variants):
    rows = []
    grouped = group_variants(variants)
    for group_key in sorted(grouped):
        title = display_title(group_key)
        handle = handle_slug("bibs " + group_key)
        rows.extend(product_rows(handle, title, group_key, grouped[group_key]))
    return rows, len(grouped)


def output_path(base_dir, search_text):
    slug = handle_slug(search_text) or "catalog"
    return Path(base_dir) / f"shopify-import-{slug}.csv"


def write_csv(base_dir, search_text, variants):
    rows, products_count = csv_rows(variants)
    target = output_path(base_dir, search_text)
    with target.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=SHOPIFY_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return target, products_count, len(rows)
