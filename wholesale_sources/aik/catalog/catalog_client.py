import re
from collections import OrderedDict
from urllib.parse import urljoin

import requests
import urllib3

from .html_tools import match_one, strip_tags, unique_urls
from .models import CatalogVariant
from .settings import BASE_URL, DETAIL_AUTH, FORM_LOGIN, FORM_PASSWORD, IMAGE_AUTH_BASE, SEARCH_PATH

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def hidden_fields(text):
    pattern = r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"'
    return {match.group(1): match.group(2) for match in re.finditer(pattern, text, re.I)}


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


def login_payload(hidden):
    return {
        "__VIEWSTATE_KEY": hidden.get("__VIEWSTATE_KEY", ""),
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "ctl00$MainContent$tbLogin": FORM_LOGIN,
        "ctl00$MainContent$tbHaslo": FORM_PASSWORD,
        "ctl00$MainContent$btZaloguj$Button": "Zaloguj",
    }


def confirm_payload(hidden):
    return {
        "__VIEWSTATE_KEY": hidden.get("__VIEWSTATE_KEY", ""),
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "ctl00$MainContent$btnZalogujPomimo$Button": "Tak",
    }


def login_b2b(session):
    page = session.get(urljoin(BASE_URL, SEARCH_PATH), verify=False, timeout=30)
    page = post_form(session, page, login_payload(hidden_fields(page.text)))
    button = "ctl00$MainContent$btnZalogujPomimo$Button"
    if button not in page.text:
        return page
    return post_form(session, page, confirm_payload(hidden_fields(page.text)))


def search_payload(hidden, search_text):
    payload = dict(hidden)
    payload["__EVENTTARGET"] = "ctl00$miWyszukiwanieProduktow2"
    payload["__EVENTARGUMENT"] = "search"
    payload["ctl00_miWyszukiwanieProduktow"] = search_text
    payload["ctl00_miWyszukiwanieProduktow_encoded"] = search_text
    return payload


def page_payload(hidden, event_name):
    payload = dict(hidden)
    payload["__EVENTTARGET"] = "ctl00$MainContent$mtProduktyWyszukane"
    payload["__EVENTARGUMENT"] = event_name
    payload["ctl00_MainContent_mtProduktyWyszukane$pageSize"] = "100"
    payload["ctl00_MainContent_mtProduktyWyszukane$pageSize1"] = "100"
    return payload


def search_catalog(session, page, search_text):
    payload = search_payload(hidden_fields(page.text), search_text)
    return post_form(session, page, payload)


def expand_page_size(session, page):
    payload = page_payload(hidden_fields(page.text), "!wielkosc_strony")
    return post_form(session, page, payload)


def parse_listing_items(page):
    pattern = r'<tr[^>]+id="record_\d+".*?<td class="tbxData tbxLeft tbxName[^"]*"><a href="([^"]+)">(.*?)</a></td>'
    items = []
    for href, raw_title in re.findall(pattern, page.text, re.S):
        title = strip_tags(raw_title)
        items.append({"title": title, "url": urljoin(page.url, href)})
    return items


def collect_listing_items(session, page):
    items = OrderedDict()
    current = expand_page_size(session, page)
    while True:
        for item in parse_listing_items(current):
            items[item["url"]] = item
        if "!nastepna_strona" not in current.text:
            return list(items.values())
        payload = page_payload(hidden_fields(current.text), "!nastepna_strona")
        current = post_form(session, current, payload)


def detail_rows_map(text):
    rows = {}
    pairs = re.findall(r"<th>([^<]+)</th><td>(.*?)</td>", text, re.I | re.S)
    for key, value in pairs:
        rows[strip_tags(key).rstrip(":")] = strip_tags(value)
    return rows


def detail_title(text, fallback):
    pattern = r'<div id="szczegolyProduktu">.*?<h1 class="caption">.*?<span style="float: inherit; margin-top: 6px;">(.*?)</span>'
    title = strip_tags(match_one(pattern, text, re.I | re.S))
    return title or fallback


def detail_image_urls(text, page_url):
    images = re.findall(r'data-pelnezdjecie="([^"]+)"', text, re.I)
    if not images:
        images = re.findall(r'href="(Obrazki/[^"]+)"', text, re.I)
    absolute = unique_urls(page_url, images)
    return [url.replace(BASE_URL, IMAGE_AUTH_BASE) for url in absolute]


def detail_price(text, rows):
    pattern = r"class='cena_brutto'>([0-9]+,[0-9]+)"
    value = match_one(pattern, text, re.I)
    if value:
        return value.replace(",", ".")
    value = rows.get("Cena brutto bez rabatu", "").split()[0]
    return value.replace(",", ".")


def detail_vendor(rows, title):
    if rows.get("Kategoria główna"):
        return rows["Kategoria główna"]
    return title.split()[0] if title else "AICO"


def source_code(title):
    match = re.match(r"^\S+\s+(\S+)", title)
    return match.group(1) if match else ""


def build_variant(page_url, fallback_title, text):
    rows = detail_rows_map(text)
    title = detail_title(text, fallback_title)
    return CatalogVariant(
        title=title,
        vendor=detail_vendor(rows, title),
        source_code=source_code(title),
        supplier_sku=match_one(r"Indeks katalogowy:</b>\s*([^<]+)</p>", text, re.I),
        barcode=rows.get("Kod kreskowy", ""),
        price=detail_price(text, rows),
        detail_url=page_url,
        image_urls=tuple(detail_image_urls(text, page_url)),
        main_category=rows.get("Kategoria główna", ""),
        source_category=rows.get("Kategorie wielopoziomowa", ""),
    )


def fetch_detail(session, item):
    page = session.get(item["url"], verify=False, timeout=30)
    return build_variant(item["url"], item["title"], page.text)


def collect_catalog_variants(search_text, limit=0):
    session = start_session()
    page = login_b2b(session)
    page = search_catalog(session, page, search_text)
    items = collect_listing_items(session, page)
    if limit:
        items = items[:limit]
    return [fetch_detail(session, item) for item in items]
