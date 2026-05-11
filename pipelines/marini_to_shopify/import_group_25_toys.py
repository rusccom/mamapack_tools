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

SOURCE_URL = "https://b2b.marini.pl/items/25?parent=0"
LIVE_PATH = ROOT / "wholesale_sources" / "marini" / "group_25_live_extract.json"
XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "group_25_toys"
REPORT_PATH = Path(__file__).with_name("group_25_toys_shopify_sync_report.json")
COLLECTIONS = {"Gryzaki": "gryzaki", "Zabawki": "zabawki", "Zabawki do kąpieli": "zabawki-do-kapieli"}
COLOR_WORDS = {"niebieski", "niebieska", "różowy", "różowa", "zielony", "zielona", "jasne", "ciemne"}
POLISH_TRANS = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"})


def main() -> None:
    live = load_live_items()
    selected, skipped = select_items(live, load_xml_metadata())
    products = build_products(group_items(selected))
    client = build_shopify_client(ROOT)
    collections = ensure_collections(client, products)
    validate_no_conflicts(client, products)
    created = create_products(client, collections, products)
    save_report(collections, selected, skipped, products, created)
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
    return selected, skipped


def skip_reason(item: dict) -> str:
    if item["stock"] <= 0:
        return "stock is zero"
    if not item["priceList"] or item["purchaseNet"] <= 0:
        return "missing price"
    return ""


def enrich_item(xml_item: dict, item: dict) -> dict:
    title = xml_item.get("nazwa") or item["title"]
    base, variant = split_base_variant(title)
    return {"sourceTitle": title, "brand": brand(title), "collection": choose_collection(title), "baseTitle": base, "variantValue": variant, "imagePaths": image_paths_for(xml_item, item), "salePrice": f"{item['purchaseNet'] * 1.6:.2f}"}


def brand(title: str) -> str:
    return title.split(" ", 1)[0].title()


def choose_collection(title: str) -> str:
    text = plain(title)
    if "kapiel" in text:
        return "Zabawki do kąpieli"
    if "gryzak" in text:
        return "Gryzaki"
    return "Zabawki"


def split_base_variant(title: str) -> tuple[str, str]:
    without_code = re.sub(r"^(AKUKU)\s+A\d+\s+", r"\1 ", title, flags=re.I)
    parts = without_code.rsplit(" ", 1)
    if len(parts) == 2 and plain(parts[1]) in {plain(item) for item in COLOR_WORDS}:
        return parts[0], parts[1].lower()
    return title, ""


def image_paths_for(xml_item: dict, item: dict) -> list[str]:
    urls = (xml_item.get("zdjecia") or "").split()
    sources = urls[:1]
    if item.get("imageId"):
        sources.append(f"https://b2b.marini.pl/imagehandler.ashx?id={item['imageId']}&width=1000&height=1000")
    return [path for path in download_all(sources, item["sku"]) if path]


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
    args = ["curl.exe", "-sS", "-L", "--http1.1", "--ssl-no-revoke", "--connect-timeout", "15", "--max-time", "60", "--retry", "2", "--retry-all-errors", "-k", "-A", "Mozilla/5.0", "-o", str(path), url]
    subprocess.run(args, check=True)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError("downloaded file is empty")
    return path


def group_items(items: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups = {}
    for item in items:
        key = (item["collection"], item["baseTitle"] if item["variantValue"] else item["sourceTitle"])
        groups.setdefault(key, []).append(item)
    return groups


def build_products(groups: dict[tuple[str, str], list[dict]]) -> list[SimpleNamespace]:
    products = []
    for (collection, title), items in sorted(groups.items(), key=lambda row: row[0][1]):
        products.append(build_product(collection, title, sorted(items, key=lambda item: item["sku"])))
    return products


def build_product(collection: str, title: str, items: list[dict]) -> SimpleNamespace:
    file_map, variants = media_and_variants(items)
    multi = len(items) > 1 and all(item["variantValue"] for item in items)
    return SimpleNamespace(title=title, handle=slugify(title), description_html=build_product_description(description_spec(title, collection, items, multi)), vendor=items[0]["brand"], product_type=collection, tags=(items[0]["brand"], "Marini", collection), option_name="Kolor" if multi else "Title", option_values=[item["variantValue"] for item in items] if multi else ["Default Title"], variants=tuple(variants), file_map=file_map, seo=seo_fields(title, collection, items), collection_title=collection, source_items=items)


def media_and_variants(items: list[dict]) -> tuple[dict[str, str], list[SimpleNamespace]]:
    file_map, variants = {}, []
    for item in items:
        keys = []
        for index, path in enumerate(item["imagePaths"], start=1):
            key = f"{item['sku']}-{index}"
            file_map[key] = path
            keys.append(key)
        variants.append(SimpleNamespace(sku=item["sku"], barcode=item["barcode"], price=item["salePrice"], option_value=item["variantValue"] or "Default Title", file_key=keys[0]))
    return file_map, variants


def description_spec(title: str, collection: str, items: list[dict], multi: bool) -> dict:
    skus = ", ".join(item["sku"] for item in items)
    variants = ", ".join(item["variantValue"] for item in items if item["variantValue"])
    return {"eyebrow": collection, "title": title, "subtitle": subtitle(collection), "badges": badges(collection, multi, variants), "introTitle": "Dlaczego warto?", "introText": intro(collection), "producerTitle": "Najważniejsze cechy", "producerItems": features(collection), "cards": cards(collection), "detailsTitle": "Dane produktu", "details": detail_rows(items, variants, skus), "careTitle": "Przed podaniem dziecku", "careSteps": ["Sprawdź stan produktu przed każdym użyciem.", "Czyść i przechowuj zgodnie z zaleceniami producenta."], "safetyTitle": "Ważne", "safetyText": "Produkt należy używać pod opieką osoby dorosłej i zgodnie z instrukcją producenta.", "sourceNote": "Produkt dodany na podstawie danych Marini B2B."}


def subtitle(collection: str) -> str:
    if collection == "Gryzaki":
        return "Praktyczny gryzak dla maluszka, pomocny w czasie ząbkowania."
    if collection == "Zabawki do kąpieli":
        return "Zabawka do kąpieli, która urozmaica codzienną pielęgnację dziecka."
    return "Lekka zabawka dla niemowląt i małych dzieci do codziennej zabawy."


def intro(collection: str) -> str:
    if collection == "Zabawki do kąpieli":
        return "Kolorowa zabawka pomaga oswoić kąpiel i zamienić ją w spokojniejszy, przyjemniejszy rytuał."
    return "Produkt sprawdzi się jako mały dodatek do wyprawki, prezent albo element codziennej zabawy dziecka."


def features(collection: str) -> list[str]:
    if collection == "Gryzaki":
        return ["wygodny format do małych rączek", "pomocny przy ząbkowaniu", "lekki i praktyczny na spacer lub do domu"]
    return ["lekki, dziecięcy format", "dobry dodatek do wyprawki", "łatwy do zabrania w podróż lub na spacer"]


def cards(collection: str) -> list[dict]:
    return [{"title": "Dla maluszka", "text": "Forma produktu jest dopasowana do codziennych aktywności dziecka."}, {"title": "Do wyprawki", "text": "Mały, praktyczny produkt, który łatwo mieć pod ręką."}]


def badges(collection: str, multi: bool, variants: str) -> list[str]:
    values = [collection, "AKUKU"]
    if multi:
        values.append(f"Warianty: {variants}")
    return values


def detail_rows(items: list[dict], variants: str, skus: str) -> list[dict]:
    rows = [{"label": "Marka", "value": items[0]["brand"]}, {"label": "SKU", "value": skus}, {"label": "EAN", "value": ", ".join(item["barcode"] for item in items if item["barcode"])}, {"label": "Warianty", "value": variants}]
    return [row for row in rows if row["value"]]


def seo_fields(title: str, collection: str, items: list[dict]) -> dict:
    skus = ", ".join(item["sku"] for item in items)
    desc = f"{title} marki AKUKU. {collection.lower()} dla niemowląt i małych dzieci. SKU: {skus}."
    return {"title": f"{title} | MamaPack", "description": desc[:320]}


def ensure_collections(client, products: list[SimpleNamespace]) -> dict:
    needed = sorted({product.collection_title for product in products})
    return {title: ensure_collection(client, title, COLLECTIONS[title]) for title in needed}


def validate_no_conflicts(client, products: list[SimpleNamespace]) -> None:
    duplicates = duplicate_skus(products)
    sku_conflicts = [v.sku for p in products for v in p.variants if variant_sku_exists(client, v.sku)]
    handle_conflicts = [p.handle for p in products if product_handle_exists(client, p.handle)]
    if duplicates or sku_conflicts or handle_conflicts:
        raise RuntimeError(json.dumps({"duplicates": duplicates, "skuConflicts": sku_conflicts, "handleConflicts": handle_conflicts}, ensure_ascii=False, indent=2))


def duplicate_skus(products: list[SimpleNamespace]) -> list[str]:
    skus = [variant.sku for product in products for variant in product.variants]
    return sorted({sku for sku in skus if skus.count(sku) > 1})


def create_products(client, collections: dict, products: list[SimpleNamespace]) -> list[dict]:
    created = []
    for product in products:
        product_id = sync_product(client, product)
        update_product_seo(client, product_id, product.handle, product.seo["title"], product.seo["description"])
        add_products_to_collection(client, collections[product.collection_title]["id"], [product_id])
        created.append(verify_product(client, product_id, product))
    return created


VERIFY_QUERY = "query VerifyProduct($id: ID!) { product(id: $id) { id title handle status variants(first: 80) { nodes { sku barcode price selectedOptions { name value } } } media(first: 80) { nodes { status alt mediaContentType } } collections(first: 20) { nodes { title handle } } seo { title description } } }"


def verify_product(client, product_id: str, product: SimpleNamespace) -> dict:
    data = {}
    for _ in range(18):
        data = client.execute(VERIFY_QUERY, {"id": product_id})["product"]
        statuses = [node["status"] for node in data["media"]["nodes"]]
        if statuses and all(status == "READY" for status in statuses):
            break
        time.sleep(5)
    return {"collectionTitle": product.collection_title, "product": data, "sourceItems": product.source_items}


def save_report(collections: dict, selected: list[dict], skipped: list[dict], products: list[SimpleNamespace], created: list[dict]) -> None:
    report = {"createdAt": datetime.now().astimezone().isoformat(), "sourceUrl": SOURCE_URL, "collections": collections, "availableSkuCount": len(selected), "skippedCount": len(skipped), "skipped": skipped, "productCountAfterGrouping": len(products), "products": product_report(products), "created": created}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def product_report(products: list[SimpleNamespace]) -> list[dict]:
    return [{"title": p.title, "collection": p.collection_title, "optionName": p.option_name, "variantCount": len(p.variants), "skus": [v.sku for v in p.variants], "variantValues": [v.option_value for v in p.variants]} for p in products]


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower().translate(POLISH_TRANS)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


def plain(value: str) -> str:
    return slugify(value).replace("-", " ")


if __name__ == "__main__":
    main()
