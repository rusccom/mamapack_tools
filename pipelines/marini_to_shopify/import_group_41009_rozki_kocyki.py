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

SOURCE_URL = "https://b2b.marini.pl/items/41009?parent=22"
LIVE_PATH = ROOT / "wholesale_sources" / "marini" / "group_41009_live_extract.json"
XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "group_41009_rozki_kocyki"
REPORT_PATH = Path(__file__).with_name("group_41009_rozki_kocyki_shopify_sync_report.json")
COLLECTION_TITLE = "Rożki i kocyki dla niemowląt"
COLLECTION_HANDLE = "rozki-i-kocyki-dla-niemowlat"
PRODUCT_TITLE = "AKUKU Kocyk / otulacz / ręcznik muślinowy 110x105 cm"
POLISH_TRANS = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"})


def main() -> None:
    selected, skipped = select_items(load_live_items(), load_xml_metadata())
    products = [build_product(selected)] if selected else []
    client = build_shopify_client(ROOT)
    collection = ensure_collection(client, COLLECTION_TITLE, COLLECTION_HANDLE)
    validate_no_conflicts(client, products)
    created = create_products(client, collection, products)
    save_report(collection, selected, skipped, products, created)
    print(f"Created {len(created)} Shopify draft products / {len(selected)} SKU.")


def load_live_items() -> list[dict]:
    data = json.loads(LIVE_PATH.read_text(encoding="utf-8-sig"))
    items = []
    for group in data["extract"].get("groups", []):
        details = {item["id"]: item for item in group.get("details", [])}
        for row in group.get("articleList", []):
            items.append(live_item(row, details))
    return items


def live_item(row: dict, details: dict[int, dict]) -> dict:
    article = row["article"]
    detail = details.get(article["id"], {}).get("json") or {}
    price = detail.get("price") or {}
    stock = detail.get("stockLevel") or {}
    return {"id": article["id"], "sku": article["code"]["value"], "title": article["name"], "imageId": (article.get("image") or {}).get("imageId"), "stock": int(stock.get("value") or 0), "purchaseNet": float(price.get("netPrice") or 0), "barcode": detail.get("ean") or "", "priceList": bool(detail.get("itemExistsInCurrentPriceList"))}


def load_xml_metadata() -> dict[str, dict]:
    root = ET.parse(XML_PATH).getroot()
    result = {}
    for node in root.findall("b2b"):
        data = {child.tag: (child.text or "").strip() for child in node}
        if data.get("kod"):
            result[data["kod"]] = data
    return result


def select_items(items: list[dict], xml: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    selected, skipped = [], []
    for item in items:
        reason = skip_reason(item)
        if not reason:
            item.update(enrich_item(xml.get(item["sku"], {}), item))
            reason = "" if item["imagePaths"] else "missing image"
        (skipped if reason else selected).append({**item, "reason": reason} if reason else item)
    return sorted(selected, key=lambda row: row["variantValue"]), skipped


def skip_reason(item: dict) -> str:
    if item["stock"] <= 0:
        return "stock is zero"
    if not item["priceList"] or item["purchaseNet"] <= 0:
        return "missing price"
    return ""


def enrich_item(xml_item: dict, item: dict) -> dict:
    title = xml_item.get("nazwa") or item["title"]
    return {"sourceTitle": title, "brand": "AKUKU", "variantValue": variant_value(title), "imagePaths": image_paths_for(xml_item, item), "salePrice": f"{item['purchaseNet'] * 1.6:.2f}"}


def variant_value(title: str) -> str:
    value = re.sub(r"^AKUKU\s+A\d+\s+Kocyk\s*/\s*otulacz\s*/\s*ręcznik\s+muślinowy\s+110x105\s+cm\s+", "", title, flags=re.I)
    return value.strip() or "Wzór"


def image_paths_for(xml_item: dict, item: dict) -> list[str]:
    urls = (xml_item.get("zdjecia") or "").split()[:3]
    if item.get("imageId"):
        urls.append(f"https://b2b.marini.pl/imagehandler.ashx?id={item['imageId']}&width=1000&height=1000")
    return [path for path in download_all(urls, item["sku"]) if path]


def download_all(urls: list[str], sku: str) -> list[str]:
    paths = []
    for index, url in enumerate(urls, start=1):
        try:
            paths.append(str(download_image(url, sku, index)))
        except Exception as exc:
            print(f"[image skip] {sku} {url}: {exc}")
    return paths


def download_image(url: str, sku: str, index: int) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGE_DIR / f"{sku}-{index}{Path(url.split('?', 1)[0]).suffix or '.jpg'}"
    if path.exists() and path.stat().st_size > 0:
        return path
    args = ["curl.exe", "-sS", "-L", "--http1.1", "--ssl-no-revoke", "--connect-timeout", "15", "--max-time", "60", "--retry", "2", "--retry-all-errors", "-k", "-A", "Mozilla/5.0", "-o", str(path), url]
    subprocess.run(args, check=True)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError("downloaded file is empty")
    return path


def build_product(items: list[dict]) -> SimpleNamespace:
    file_map, variants = media_and_variants(items)
    return SimpleNamespace(title=PRODUCT_TITLE, handle=slugify(PRODUCT_TITLE), description_html=build_product_description(description_spec(items)), vendor="AKUKU", product_type=COLLECTION_TITLE, tags=("AKUKU", "Marini", COLLECTION_TITLE), option_name="Wzór", option_values=[item["variantValue"] for item in items], variants=tuple(variants), file_map=file_map, seo=seo_fields(items), source_items=items)


def media_and_variants(items: list[dict]) -> tuple[dict[str, str], list[SimpleNamespace]]:
    file_map, variants = {}, []
    for item in items:
        keys = media_keys(file_map, item)
        variants.append(SimpleNamespace(sku=item["sku"], barcode=item["barcode"], price=item["salePrice"], option_value=item["variantValue"], file_key=keys[0]))
    return file_map, variants


def media_keys(file_map: dict[str, str], item: dict) -> list[str]:
    keys = []
    for index, path in enumerate(item["imagePaths"], start=1):
        key = f"{item['sku']}-{index}"
        file_map[key] = path
        keys.append(key)
    return keys


def description_spec(items: list[dict]) -> dict:
    patterns = ", ".join(item["variantValue"] for item in items)
    return {"eyebrow": COLLECTION_TITLE, "title": PRODUCT_TITLE, "subtitle": "Miękki muślinowy kocyk, otulacz i ręcznik w jednym, przydatny w domu, na spacerze i po kąpieli.", "badges": ["muślin", "110x105 cm", f"Wzory: {patterns}"], "introTitle": "Delikatny dodatek do wyprawki", "introText": "Lekki muślin dobrze sprawdza się przy codziennej pielęgnacji maluszka: jako kocyk, otulacz, ręcznik albo osłonka w czasie spaceru.", "producerTitle": "Najważniejsze cechy", "producerItems": ["uniwersalny format 110x105 cm", "miękki materiał odpowiedni dla niemowląt", "praktyczny w domu, podróży i po kąpieli"], "cards": [{"title": "Wiele zastosowań", "text": "Może służyć jako kocyk, otulacz, ręcznik lub lekka osłonka."}, {"title": "Do wyprawki", "text": "Łatwy do spakowania produkt na pierwsze miesiące z dzieckiem."}], "detailsTitle": "Dane produktu", "details": detail_rows(items, patterns), "careTitle": "Pielęgnacja", "careSteps": ["Pierz i susz zgodnie z zaleceniami producenta.", "Przed pierwszym użyciem sprawdź metkę i stan produktu."], "safetyTitle": "Ważne", "safetyText": "Produkt należy używać pod opieką osoby dorosłej i zgodnie z przeznaczeniem.", "sourceNote": "Produkt dodany na podstawie danych Marini B2B."}


def detail_rows(items: list[dict], patterns: str) -> list[dict]:
    return [{"label": "Marka", "value": "AKUKU"}, {"label": "Rozmiar", "value": "110x105 cm"}, {"label": "Wzory", "value": patterns}, {"label": "SKU", "value": ", ".join(item["sku"] for item in items)}, {"label": "EAN", "value": ", ".join(item["barcode"] for item in items if item["barcode"])}]


def seo_fields(items: list[dict]) -> dict:
    patterns = ", ".join(item["variantValue"] for item in items)
    desc = f"{PRODUCT_TITLE} marki AKUKU. Muślinowy kocyk, otulacz i ręcznik dla niemowląt. Wzory: {patterns}."
    return {"title": f"{PRODUCT_TITLE} | MamaPack", "description": desc[:320]}


def validate_no_conflicts(client, products: list[SimpleNamespace]) -> None:
    sku_conflicts = [v.sku for p in products for v in p.variants if variant_sku_exists(client, v.sku)]
    handle_conflicts = [p.handle for p in products if product_handle_exists(client, p.handle)]
    if sku_conflicts or handle_conflicts:
        raise RuntimeError(json.dumps({"skuConflicts": sku_conflicts, "handleConflicts": handle_conflicts}, ensure_ascii=False, indent=2))


def create_products(client, collection: dict, products: list[SimpleNamespace]) -> list[dict]:
    created = []
    for product in products:
        product_id = sync_product(client, product)
        update_product_seo(client, product_id, product.handle, product.seo["title"], product.seo["description"])
        add_products_to_collection(client, collection["id"], [product_id])
        created.append(verify_product(client, product_id, product))
    return created


VERIFY_QUERY = "query VerifyProduct($id: ID!) { product(id: $id) { id title handle status variants(first: 20) { nodes { sku barcode price selectedOptions { name value } } } media(first: 30) { nodes { status alt mediaContentType } } collections(first: 20) { nodes { title handle } } seo { title description } } }"


def verify_product(client, product_id: str, product: SimpleNamespace) -> dict:
    data = {}
    for _ in range(18):
        data = client.execute(VERIFY_QUERY, {"id": product_id})["product"]
        statuses = [node["status"] for node in data["media"]["nodes"]]
        if statuses and all(status == "READY" for status in statuses):
            break
        time.sleep(5)
    return {"product": data, "sourceItems": product.source_items}


def save_report(collection: dict, selected: list[dict], skipped: list[dict], products: list[SimpleNamespace], created: list[dict]) -> None:
    report = {"createdAt": datetime.now().astimezone().isoformat(), "sourceUrl": SOURCE_URL, "collection": collection, "availableSkuCount": len(selected), "skippedCount": len(skipped), "skipped": skipped, "productCountAfterGrouping": len(products), "products": product_report(products), "created": created}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def product_report(products: list[SimpleNamespace]) -> list[dict]:
    return [{"title": p.title, "optionName": p.option_name, "variantCount": len(p.variants), "skus": [v.sku for v in p.variants], "variantValues": [v.option_value for v in p.variants]} for p in products]


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower().translate(POLISH_TRANS)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


if __name__ == "__main__":
    main()
