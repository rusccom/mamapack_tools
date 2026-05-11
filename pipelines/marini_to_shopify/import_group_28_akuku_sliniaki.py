from __future__ import annotations
import json
import re
import subprocess
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from shopify_store.collections import add_products_to_collection, ensure_collection
from shopify_store.core.graphql import build_shopify_client
from shopify_store.products import build_product_description, sync_product, update_product_seo
from shopify_store.products.identity import product_handle_exists, variant_sku_exists

SOURCE_URL = "https://b2b.marini.pl/items/28?parent=22"
LIVE_PATH = ROOT / "wholesale_sources" / "marini" / "group_28_live_extract.json"
XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "group_28_akuku_sliniaki"
REPORT_PATH = Path(__file__).with_name("group_28_akuku_sliniaki_shopify_sync_report.json")
COLLECTION_TITLE = "Śliniaki"
COLLECTION_HANDLE = "sliniaki"
POLISH_TRANS = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"})
GROUPS = [
    ("AKUKU Śliniak z rękawkiem", "Wzór", {"A0517": "Borsuk", "A0518": "Misio"}),
    ("AKUKU Śliniak na rzep", "Rozmiar", {"A1300": "mały", "A1320": "średni"}),
    ("AKUKU Śliniak apaszka na rzep", "Wzór", {"A1512": "Serduszka", "A1513": "Jeżyki"}),
    ("AKUKU Śliniak wiązany", "Rozmiar", {"A1600": "mini", "A1640": "mały"}),
    ("AKUKU Śliniak wiązany z nadrukiem", "Wzór", {"A1662": "Sowy", "A1663": "Autka", "A1664": "Jeżyki", "A1665": "Gwiazdki", "A1666": "Koty"}),
    ("AKUKU Śliniak rękawek okulary", "Title", {"A1744": "Default Title"}),
]


def main() -> None:
    xml = load_xml_by_code()
    live = load_live_by_source_sku()
    client = build_shopify_client(ROOT)
    collection = ensure_collection(client, COLLECTION_TITLE, COLLECTION_HANDLE)
    to_create, skipped = split_conflicts(client, xml, live)
    created = create_products(client, collection, to_create)
    save_report(collection, to_create, skipped, created)
    print(f"Created {len(created)} Shopify draft products / {sum(len(p.variants) for p in to_create)} SKU.")


def load_xml_by_code() -> dict[str, dict]:
    result = {}
    root = ET.parse(XML_PATH).getroot()
    for node in root.findall("b2b"):
        data = {child.tag: (child.text or "").strip() for child in node}
        code = akuku_code(data.get("nazwa", ""))
        if code:
            result[code] = data
    return result


def load_live_by_source_sku() -> dict[str, dict]:
    data = json.loads(LIVE_PATH.read_text(encoding="utf-8-sig"))
    result = {}
    for group in data["extract"].get("groups", []):
        details = {item["id"]: item for item in group.get("details", [])}
        for row in group.get("articleList", []):
            item = live_item(row, details)
            result[item["sourceSku"]] = item
    return result


def live_item(row: dict, details: dict[int, dict]) -> dict:
    article = row["article"]
    detail = details.get(article["id"], {}).get("json") or {}
    stock = detail.get("stockLevel") or {}
    price = detail.get("price") or {}
    return {"sourceSku": article["code"]["value"], "imageId": (article.get("image") or {}).get("imageId"), "stock": int(stock.get("value") or 0), "purchaseNet": float(price.get("netPrice") or 0), "barcode": detail.get("ean") or ""}


def akuku_code(title: str) -> str:
    match = re.search(r"\b(A\d{4})\b", title)
    return match.group(1) if match else ""


def split_conflicts(client, xml: dict, live: dict) -> tuple[list[SimpleNamespace], list[dict]]:
    products, skipped = [], []
    for title, option, variants in GROUPS:
        missing = [code for code in variants if code not in xml]
        conflicts = conflict_reasons(client, title, variants)
        if missing or conflicts["skus"] or conflicts["handles"]:
            skipped.append({"title": title, "missing": missing, "conflicts": conflicts})
            continue
        products.append(build_product(title, option, variants, xml, live))
    return products, skipped


def conflict_reasons(client, title: str, variants: dict) -> dict:
    sku_conflicts = [sku for sku in variants if variant_sku_exists(client, sku)]
    handle = slugify(title)
    handle_conflicts = [handle] if product_handle_exists(client, handle) else []
    return {"skus": sku_conflicts, "handles": handle_conflicts}


def build_product(title: str, option: str, variants: dict, xml: dict, live: dict) -> SimpleNamespace:
    items = [build_item(code, value, xml[code], live) for code, value in variants.items()]
    option_name = option if len(items) > 1 else "Title"
    file_map, product_variants = media_and_variants(items)
    return SimpleNamespace(title=title, handle=slugify(title), description_html=build_product_description(description_spec(title, option_name, items)), vendor="AKUKU", product_type=COLLECTION_TITLE, tags=("AKUKU", "Marini", COLLECTION_TITLE), option_name=option_name, option_values=[item["variantValue"] for item in items] if len(items) > 1 else ["Default Title"], variants=tuple(product_variants), file_map=file_map, seo=seo_fields(title, items), source_items=items)


def build_item(code: str, value: str, xml_item: dict, live: dict) -> dict:
    source_sku = xml_item["kod"]
    live_item = live.get(source_sku, {})
    price = float(live_item.get("purchaseNet") or xml_item.get("cena") or 0)
    return {"sku": code, "sourceSku": source_sku, "sourceTitle": xml_item["nazwa"], "variantValue": value, "barcode": live_item.get("barcode") or xml_item.get("EAN", ""), "purchaseNet": price, "salePrice": f"{price * 1.6:.2f}", "stock": live_item.get("stock", 0), "imagePaths": image_paths_for(xml_item, live_item, code)}


def image_paths_for(xml_item: dict, live_item: dict, sku: str) -> list[str]:
    urls = marini_image_urls((xml_item.get("zdjecia") or "").split()[:2])
    if live_item.get("imageId"):
        urls.append(f"https://b2b.marini.pl/imagehandler.ashx?id={live_item['imageId']}&width=1000&height=1000")
    paths = download_all(urls, sku)
    if not paths:
        raise RuntimeError(f"No image downloaded for {sku}")
    return paths


def marini_image_urls(urls: list[str]) -> list[str]:
    result = []
    for url in urls:
        result.append(url)
        if url.startswith("https://marini.pl/"):
            result.append(url.replace("https://", "http://", 1))
    return result


def download_all(urls: list[str], sku: str) -> list[str]:
    paths = []
    for index, url in enumerate(urls, start=1):
        try:
            paths.append(str(download_image(url, sku, index)))
            break
        except Exception as exc:
            print(f"[image skip] {sku} {url}: {exc}")
    return paths


def download_image(url: str, sku: str, index: int) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGE_DIR / f"{sku}-{index}{Path(url.split('?', 1)[0]).suffix or '.jpg'}"
    if path.exists() and path.stat().st_size > 0:
        return path
    args = ["curl.exe", "-sS", "-L", "--tlsv1.2", "--http1.1", "--ssl-no-revoke", "--connect-timeout", "15", "--max-time", "60", "--retry", "3", "--retry-all-errors", "-k", "-A", "Mozilla/5.0", "-o", str(path), url]
    subprocess.run(args, check=True)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError("downloaded file is empty")
    return path


def media_and_variants(items: list[dict]) -> tuple[dict[str, str], list[SimpleNamespace]]:
    file_map, variants = {}, []
    for item in items:
        file_map[item["sku"]] = item["imagePaths"][0]
        variants.append(SimpleNamespace(sku=item["sku"], barcode=item["barcode"], price=item["salePrice"], option_value=item["variantValue"], file_key=item["sku"]))
    return file_map, variants


def description_spec(title: str, option: str, items: list[dict]) -> dict:
    values = ", ".join(item["variantValue"] for item in items)
    return {"eyebrow": "AKUKU", "title": title, "subtitle": "Praktyczny śliniak dla dziecka, który pomaga chronić ubranko podczas jedzenia i codziennych aktywności.", "badges": ["AKUKU", option, values], "introTitle": "Wygoda przy posiłkach", "introText": "Śliniak sprawdza się w domu i poza nim, kiedy chcesz szybko zabezpieczyć ubranko dziecka przed zabrudzeniem.", "producerTitle": "Najważniejsze cechy", "producerItems": ["lekki i praktyczny format", "łatwy do spakowania do torby", "dobry dodatek do wyprawki", "różne warianty do wyboru"], "cards": [{"title": "Na co dzień", "text": "Pomaga ograniczyć przebieranie po posiłku."}, {"title": "Do wyprawki", "text": "Mały produkt, który często przydaje się od pierwszych miesięcy."}], "detailsTitle": "Dane produktu", "details": detail_rows(option, items), "careTitle": "Pielęgnacja", "careSteps": ["Czyść i używaj zgodnie z zaleceniami producenta.", "Przed użyciem sprawdź stan produktu."], "safetyTitle": "Ważne", "safetyText": "Produkt należy stosować pod opieką osoby dorosłej i zgodnie z przeznaczeniem.", "sourceNote": "Produkt dodany na podstawie danych Marini B2B."}


def detail_rows(option: str, items: list[dict]) -> list[dict]:
    return [{"label": "Marka", "value": "AKUKU"}, {"label": option, "value": ", ".join(item["variantValue"] for item in items)}, {"label": "SKU wariantów", "value": ", ".join(item["sku"] for item in items)}, {"label": "EAN", "value": ", ".join(item["barcode"] for item in items if item["barcode"])}]


def seo_fields(title: str, items: list[dict]) -> dict:
    codes = ", ".join(item["sku"] for item in items)
    desc = f"{title} marki AKUKU. Praktyczny śliniak dla dziecka. Warianty SKU: {codes}."
    return {"title": f"{title} | MamaPack", "description": desc[:320]}


def create_products(client, collection: dict, products: list[SimpleNamespace]) -> list[dict]:
    created = []
    for product in products:
        product_id = sync_product(client, product)
        update_product_seo(client, product_id, product.handle, product.seo["title"], product.seo["description"])
        add_products_to_collection(client, collection["id"], [product_id])
        created.append(verify_product(client, product_id, product))
    return created


VERIFY_QUERY = "query VerifyProduct($id: ID!) { product(id: $id) { id title handle status variants(first: 50) { nodes { sku barcode price selectedOptions { name value } } } media(first: 50) { nodes { status alt mediaContentType } } collections(first: 20) { nodes { title handle } } seo { title description } } }"


def verify_product(client, product_id: str, product: SimpleNamespace) -> dict:
    data = {}
    for _ in range(18):
        data = client.execute(VERIFY_QUERY, {"id": product_id})["product"]
        statuses = [node["status"] for node in data["media"]["nodes"]]
        if statuses and all(status == "READY" for status in statuses):
            break
        time.sleep(5)
    return {"product": data, "sourceItems": product.source_items}


def save_report(collection: dict, products: list[SimpleNamespace], skipped: list[dict], created: list[dict]) -> None:
    report = {"createdAt": datetime.now().astimezone().isoformat(), "sourceUrl": SOURCE_URL, "collection": collection, "createdProductCount": len(created), "createdSkuCount": sum(len(p.variants) for p in products), "skippedExistingOrMissing": skipped, "products": product_report(products), "created": created}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def product_report(products: list[SimpleNamespace]) -> list[dict]:
    return [{"title": p.title, "optionName": p.option_name, "skus": [v.sku for v in p.variants], "variantValues": [v.option_value for v in p.variants]} for p in products]


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower().translate(POLISH_TRANS)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


if __name__ == "__main__":
    main()
