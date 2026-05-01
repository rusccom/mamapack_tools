# -*- coding: utf-8 -*-
import csv
import html
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://e.aico.com.pl/"
SEARCH_URL = urljoin(BASE, "ProduktyWyszukiwanie.aspx")
OUTPUT = Path(__file__).resolve().parent / "bibs-shopify-import.csv"
IMAGE_AUTH_BASE = "https://b2b:aico2012@e.aico.com.pl/"
DETAIL_AUTH = ("b2b", "aico2012")
FORM_LOGIN = "smarttradeorg"
FORM_PASSWORD = "Vectra321"

EXCLUDE_TOKENS = (
    "POJEMNIK",
    "PUDE",
    "KLIPS",
    "DO BUTELEK",
    "UCHWYT",
    "BUTELKA",
    "CHUSTA",
    "KUBK",
    "OBIADOWY",
)

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

SIZE_OVERRIDES = {"222110101": "2"}

HEADERS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Option3 Name",
    "Option3 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare-at Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Variant Barcode",
    "Image Src",
    "Image Alt Text",
]


def hidden_fields(text):
    pattern = r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"'
    return {m.group(1): m.group(2) for m in re.finditer(pattern, text, re.I)}


def form_action(text, fallback):
    match = re.search(r'<form[^>]+action="([^"]+)"[^>]*id="aspnetForm"', text, re.I)
    target = match.group(1) if match else fallback
    return urljoin(fallback, target)


def start_session():
    session = requests.Session()
    session.auth = DETAIL_AUTH
    return session


def post_form(session, page, payload):
    target = form_action(page.text, page.url)
    return session.post(target, data=payload, verify=False, timeout=30)


def login_b2b(session):
    page = session.get(SEARCH_URL, verify=False, timeout=30)
    hidden = hidden_fields(page.text)
    payload = {
        "__VIEWSTATE_KEY": hidden.get("__VIEWSTATE_KEY", ""),
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "ctl00$MainContent$tbLogin": FORM_LOGIN,
        "ctl00$MainContent$tbHaslo": FORM_PASSWORD,
        "ctl00$MainContent$btZaloguj$Button": "Zaloguj się",
    }
    page = post_form(session, page, payload)
    if "ctl00$MainContent$btnZalogujPomimo$Button" not in page.text:
        return page
    hidden = hidden_fields(page.text)
    payload = {
        "__VIEWSTATE_KEY": hidden.get("__VIEWSTATE_KEY", ""),
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "ctl00$MainContent$btnZalogujPomimo$Button": "Tak",
    }
    return post_form(session, page, payload)


def search_bibs(session, page):
    hidden = hidden_fields(page.text)
    payload = {**hidden, "__EVENTTARGET": "ctl00$miWyszukiwanieProduktow2", "__EVENTARGUMENT": "search"}
    payload["ctl00_miWyszukiwanieProduktow"] = "BIBS"
    payload["ctl00_miWyszukiwanieProduktow_encoded"] = "BIBS"
    page = post_form(session, page, payload)
    hidden = hidden_fields(page.text)
    payload = {
        **hidden,
        "__EVENTTARGET": "ctl00$MainContent$mtProduktyWyszukane",
        "__EVENTARGUMENT": "!wielkosc_strony",
        "ctl00_MainContent_mtProduktyWyszukane$pageSize": "100",
        "ctl00_MainContent_mtProduktyWyszukane$pageSize1": "100",
    }
    return post_form(session, page, payload)


def text_from_html(fragment):
    plain = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(plain).split())


def pacifier_title(title):
    upper = title.upper()
    has_pacifier = "SMOCZEK" in upper or "SMOCZKÓW" in upper or "SMOCZKI " in upper
    return has_pacifier and not any(token in upper for token in EXCLUDE_TOKENS)


def listing_items(page):
    pattern = r'<tr[^>]+id="record_\d+".*?<td class="tbxData tbxLeft tbxName[^"]*"><a href="([^"]+)">(.*?)</a></td>'
    items = []
    for href, raw_title in re.findall(pattern, page.text, re.S):
        title = text_from_html(raw_title)
        if pacifier_title(title):
            items.append({"title": title, "url": urljoin(page.url, href)})
    return items


def collect_items(session, page):
    items = []
    while True:
        items.extend(listing_items(page))
        if "!nastepna_strona" not in page.text:
            return items
        hidden = hidden_fields(page.text)
        payload = {
            **hidden,
            "__EVENTTARGET": "ctl00$MainContent$mtProduktyWyszukane",
            "__EVENTARGUMENT": "!nastepna_strona",
            "ctl00_MainContent_mtProduktyWyszukane$pageSize": "100",
            "ctl00_MainContent_mtProduktyWyszukane$pageSize1": "100",
        }
        page = post_form(session, page, payload)


def source_code(title):
    match = re.match(r"BIBS\s+(\S+)", title)
    return match.group(1) if match else ""


def normalize_key(title, code):
    if code in GROUP_OVERRIDES:
        return GROUP_OVERRIDES[code]
    key = re.sub(r"^BIBS\s+\S+\s+", "", title.upper()).strip()
    key = re.sub(r"\bROZMIAR\s+[123]\b", "", key)
    swaps = [
        (r"\bRÓŻOWY\b", "RÓŻ"),
        (r"\bRÓŻOWA\b", "RÓŻ"),
        (r"\bWANILA\b", "WANILIA"),
        (r"\bSZAŁWIOWY\b", "SZAŁWIA"),
        (r"\bMARZĄCE\b", "MARZĄCY"),
        (r"\b2\s+PACK\b", "2 PAK"),
    ]
    for pattern, replacement in swaps:
        key = re.sub(pattern, replacement, key)
    key = re.sub(r"\s+", " ", key)
    return re.sub(r"\s*/\s*", "/", key).strip()


def variant_size(code, title):
    match = re.search(r"ROZMIAR\s+([123])", title)
    if match:
        return match.group(1)
    return SIZE_OVERRIDES.get(code, "")


def detail_value(pattern, text):
    match = re.search(pattern, text, re.I | re.S)
    return match.group(1).strip() if match else ""


def extract_price(text):
    patterns = [
        r"class='cena_brutto'>([0-9]+,[0-9]+)",
        r"<th>Cena brutto bez rabatu:</th><td>([0-9]+,[0-9]+)",
        r"([0-9]+,[0-9]+)&nbsp;PLN&nbsp;brutto",
    ]
    for pattern in patterns:
        value = detail_value(pattern, text)
        if value:
            return value.replace(",", ".")
    return ""


def detail_info(session, item):
    page = session.get(item["url"], verify=False, timeout=30)
    code = source_code(item["title"])
    image_rel = detail_value(r'href="(Obrazki/[^"]+)"', page.text)
    return {
        "code": code,
        "title": item["title"],
        "group_key": normalize_key(item["title"], code),
        "size": variant_size(code, item["title"]),
        "sku": detail_value(r"Indeks katalogowy:</b>\s*([^<]+)</p>", page.text),
        "barcode": detail_value(r"<th>Kod kreskowy:</th><td>([^<]+)</td>", page.text),
        "price": extract_price(page.text),
        "detail_url": item["url"],
        "image_url": urljoin(IMAGE_AUTH_BASE, image_rel) if image_rel else "",
    }


def polish_ascii(text):
    mapping = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")
    return text.translate(mapping)


def handle_slug(text):
    ascii_text = polish_ascii(text)
    ascii_text = unicodedata.normalize("NFKD", ascii_text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def display_title(key):
    return "BIBS " + key.lower().title()


def material_tag(key):
    if "LATEX" in key:
        return "Latex"
    if "SILIKON" in key:
        return "Silicone"
    return "Pacifier"


def source_links(variants):
    items = []
    for variant in variants:
        label = f"Size {variant['size']}" if variant["size"] else variant["sku"] or variant["code"]
        search_url = f"{SEARCH_URL}?search={quote_plus(variant['code'])}"
        detail_url = html.escape(variant["detail_url"])
        search_url = html.escape(search_url)
        items.append(f'<li>{html.escape(label)}: <a href="{detail_url}">detail</a> | <a href="{search_url}">search by code</a></li>')
    return "".join(items)


def body_html(title, key, variants):
    sizes = ", ".join(v["size"] for v in variants if v["size"]) or "Default"
    intro = f"<p>{html.escape(title)} prepared from the AICO B2B catalog for Shopify import.</p>"
    meta = f"<ul><li>Brand: BIBS</li><li>Category: Pacifier</li><li>Material: {html.escape(material_tag(key))}</li><li>Available sizes: {html.escape(sizes)}</li></ul>"
    return intro + meta + "<p>Original AICO links:</p><ul>" + source_links(variants) + "</ul>"


def fallback_sku(variant):
    size = variant["size"] or "std"
    suffix = handle_slug(variant["group_key"]).split("-")[-2:]
    return f"BIBS-{size}-{'-'.join(suffix)}".upper().strip("-")


def rows_for_product(handle, title, key, variants):
    rows = []
    option_name = "Size" if any(v["size"] for v in variants) else "Title"
    tags = f"BIBS,Pacifier,AICO,{material_tag(key)}"
    body = body_html(title, key, variants)
    for index, variant in enumerate(variants):
        row = {header: "" for header in HEADERS}
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
        if index != 0:
            rows.append(row)
            continue
        row["Title"] = title
        row["Body (HTML)"] = body
        row["Vendor"] = "BIBS"
        row["Type"] = "Pacifier"
        row["Tags"] = tags
        row["Published"] = "FALSE"
        rows.append(row)
    return rows


def main():
    session = start_session()
    page = login_b2b(session)
    page = search_bibs(session, page)
    items = collect_items(session, page)
    variants = [detail_info(session, item) for item in items]
    products = defaultdict(list)
    for variant in variants:
        products[variant["group_key"]].append(variant)
    rows = []
    for key in sorted(products):
        group = products[key]
        group.sort(key=lambda item: (item["size"] == "", item["size"], item["sku"]))
        title = display_title(key)
        handle = handle_slug("bibs " + key)
        rows.extend(rows_for_product(handle, title, key, group))
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"products={len(products)} variants={len(variants)} rows={len(rows)} file={OUTPUT}")


if __name__ == "__main__":
    main()
