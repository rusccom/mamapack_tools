import html
import re
from urllib.parse import urljoin

import requests
import urllib3

from app_settings import BASE_URL, DETAIL_AUTH, EXCLUDE_TOKENS, FORM_LOGIN, FORM_PASSWORD, IMAGE_AUTH_BASE, SEARCH_PATH

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def hidden_fields(text):
    pattern = r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"'
    return {match.group(1): match.group(2) for match in re.finditer(pattern, text, re.I)}


def form_action(text, fallback):
    match = re.search(r'<form[^>]+action="([^"]+)"[^>]*id="aspnetForm"', text, re.I)
    return urljoin(fallback, match.group(1) if match else fallback)


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
        "ctl00$MainContent$btZaloguj$Button": "Zaloguj się",
    }


def confirm_payload(hidden):
    return {
        "__VIEWSTATE_KEY": hidden.get("__VIEWSTATE_KEY", ""),
        "__VIEWSTATE": hidden.get("__VIEWSTATE", ""),
        "ctl00$MainContent$btnZalogujPomimo$Button": "Tak",
    }


def login_b2b(session):
    url = urljoin(BASE_URL, SEARCH_PATH)
    page = session.get(url, verify=False, timeout=30)
    page = post_form(session, page, login_payload(hidden_fields(page.text)))
    if "ctl00$MainContent$btnZalogujPomimo$Button" not in page.text:
        return page
    payload = confirm_payload(hidden_fields(page.text))
    return post_form(session, page, payload)


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


def text_from_html(fragment):
    plain = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(plain).split())


def is_target_title(title):
    upper = title.upper()
    if not ("SMOCZEK" in upper or "SMOCZKÓW" in upper or "SMOCZKI " in upper):
        return False
    return not any(token in upper for token in EXCLUDE_TOKENS)


def parse_listing_items(page):
    pattern = r'<tr[^>]+id="record_\d+".*?<td class="tbxData tbxLeft tbxName[^"]*"><a href="([^"]+)">(.*?)</a></td>'
    items = []
    for href, raw_title in re.findall(pattern, page.text, re.S):
        title = text_from_html(raw_title)
        if is_target_title(title):
            items.append({"title": title, "url": urljoin(page.url, href)})
    return items


def collect_listing_items(session, page):
    items = []
    current = expand_page_size(session, page)
    while True:
        items.extend(parse_listing_items(current))
        if "!nastepna_strona" not in current.text:
            return items
        payload = page_payload(hidden_fields(current.text), "!nastepna_strona")
        current = post_form(session, current, payload)


def source_code(title):
    match = re.match(r"BIBS\s+(\S+)", title)
    return match.group(1) if match else ""


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
    image_rel = detail_value(r'href="(Obrazki/[^"]+)"', page.text)
    return {
        "code": source_code(item["title"]),
        "title": item["title"],
        "sku": detail_value(r"Indeks katalogowy:</b>\s*([^<]+)</p>", page.text),
        "barcode": detail_value(r"<th>Kod kreskowy:</th><td>([^<]+)</td>", page.text),
        "price": extract_price(page.text),
        "detail_url": item["url"],
        "image_url": urljoin(IMAGE_AUTH_BASE, image_rel) if image_rel else "",
    }


def collect_variants(search_text):
    session = start_session()
    page = login_b2b(session)
    page = search_catalog(session, page, search_text)
    items = collect_listing_items(session, page)
    return [detail_info(session, item) for item in items]
