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

SOURCE_URL = "https://b2b.marini.pl/items/15?parent=10"
LIVE_PATH = ROOT / "wholesale_sources" / "marini" / "forbaby_krzeselka_15_live_extract.json"
XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "forbaby_krzeselka_15"
REPORT_PATH = Path(__file__).with_name("forbaby_krzeselka_15_shopify_sync_report.json")
COLLECTION_TITLE = "Krzesełka do karmienia"
COLLECTION_HANDLE = "krzeselka-do-karmienia"
MODELS = ("DECCO", "ICON", "MASTER")
MODEL_TITLES = {
    "DECCO": "4 Baby Decco krzesełko do karmienia",
    "ICON": "4 Baby Icon krzesełko do karmienia",
    "MASTER": "4 Baby Master 6w1 krzesełko do karmienia",
}
COLOR_NAMES = {"BLACK": "czarny", "CAMEL": "camel", "GREEN": "zielony", "GREY": "szary", "BEIGE": "beżowy"}
POLISH_TRANS = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"})
INFO = {
    "DECCO": ("Regulowane krzesełko do karmienia z miękką tapicerką i wygodną tacką.", "6-36 miesięcy", "do 15 kg", "7 wysokości, 5 pozycji oparcia, 3 pozycje podnóżka", ["Miękka tapicerka z eko-skóry jest łatwa do utrzymania w czystości.", "Pięciopunktowe pasy i dodatkowy element chronią przed wyślizgnięciem.", "Podwójna, regulowana tacka ułatwia karmienie i sprzątanie.", "Tylne kółka pomagają wygodnie przestawić krzesełko."]),
    "ICON": ("Krzesełko i leżaczek w jednym, z szeroką regulacją od pierwszych dni.", "od pierwszych dni do ok. 3 lat", "do 15 kg", "6 wysokości, 4 pozycje oparcia, regulowany podnóżek", ["Może pełnić funkcję ergonomicznego leżaczka dla najmłodszego dziecka.", "Anatomiczne siedzisko wspiera wygodną pozycję podczas odpoczynku i posiłku.", "Podwójna tacka nadaje się do mycia w zmywarce.", "Duży kosz pod siedziskiem pomaga mieć akcesoria zawsze pod ręką."]),
    "MASTER": ("Wielofunkcyjne krzesełko 6w1, które zmienia się w krzesełko ze stolikiem.", "zgodnie z instrukcją producenta", "", "regulowana tacka i kilka konfiguracji użytkowania", ["Wysokie krzesełko można przekształcić w małe krzesełko ze stolikiem.", "Zdejmowana tapicerka z eko-skóry ułatwia codzienną pielęgnację.", "Pięciopunktowe szelki i trzpień pod tacką pomagają chronić dziecko.", "Nakładka na stolik jest kompatybilna z popularnymi klockami."]),
}


def main() -> None:
    live = load_live_items()
    selected, skipped = select_available_items(live, load_xml_metadata())
    products = build_products(group_items(selected))
    client = build_shopify_client(ROOT)
    collection = ensure_collection(client, COLLECTION_TITLE, COLLECTION_HANDLE)
    validate_no_conflicts(client, products)
    created = create_products(client, collection, products)
    save_report(collection, selected, skipped, products, created)
    print(f"Created {len(created)} Shopify draft products in {COLLECTION_TITLE}.")


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


def select_available_items(items: list[dict], xml: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    selected, skipped = [], []
    for item in items:
        reason = base_skip_reason(item)
        if not reason:
            item.update(xml_enrichment(xml.get(item["sku"], {}), item))
            reason = "" if item.get("imagePaths") else "missing image"
        (skipped if reason else selected).append({**item, "reason": reason} if reason else item)
    return selected, skipped


def base_skip_reason(item: dict) -> str:
    title = item["title"].upper()
    if not any(model in title for model in MODELS):
        return "not requested model"
    if item["stock"] <= 0:
        return "stock is zero"
    if not item["priceList"] or item["purchaseNet"] <= 0:
        return "missing price"
    return ""


def xml_enrichment(xml_item: dict, item: dict) -> dict:
    title = xml_item.get("nazwa") or item["title"]
    model, color = split_model_color(title)
    return {"sourceTitle": title, "model": model, "color": color, "colorName": color_name(color), "imagePaths": image_paths_for(xml_item, item), "salePrice": f"{item['purchaseNet'] * 1.6:.2f}"}


def split_model_color(title: str) -> tuple[str, str]:
    text = title.upper().replace("4 BABY KRZESEŁKO DZIECIĘCE ", "")
    for model in ("MASTER XXIII", "MASTER", "DECCO", "ICON"):
        if text.startswith(model):
            return ("MASTER" if model.startswith("MASTER") else model, text.replace(model, "", 1).strip())
    return text, ""


def color_name(color: str) -> str:
    return COLOR_NAMES.get(color, color.lower())


def image_paths_for(xml_item: dict, item: dict) -> list[str]:
    urls = (xml_item.get("zdjecia") or "").split()
    if not urls and item.get("imageId"):
        urls = [f"https://b2b.marini.pl/imagehandler.ashx?id={item['imageId']}&width=1000&height=1000"]
    return [str(download_image(url, item["sku"], index)) for index, url in enumerate(urls[:8], start=1)]


def download_image(url: str, sku: str, index: int) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = IMAGE_DIR / f"{sku}-{index}{Path(url.split('?', 1)[0]).suffix or '.jpg'}"
    if path.exists() and path.stat().st_size > 0:
        return path
    run_curl(url, path)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError(f"Image download failed for {sku}: {url}")
    return path


def run_curl(url: str, path: Path) -> None:
    args = ["curl.exe", "-sS", "-L", "--http1.1", "--ssl-no-revoke", "--retry", "5"]
    args += ["--retry-all-errors", "-k", "-A", "Mozilla/5.0", "-o", str(path), url]
    subprocess.run(args, check=True)


def group_items(items: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["model"], []).append(item)
    return groups


def build_products(groups: dict[str, list[dict]]) -> list[SimpleNamespace]:
    return [build_product(model, groups[model]) for model in MODELS if model in groups]


def build_product(model: str, items: list[dict]) -> SimpleNamespace:
    items = sorted(items, key=lambda item: item["colorName"])
    title = MODEL_TITLES[model]
    file_map, variants = media_and_variants(items)
    multiple = len(items) > 1
    return SimpleNamespace(title=title, handle=slugify(title), description_html=build_product_description(description_spec(title, model, items)), vendor="4 Baby", product_type=COLLECTION_TITLE, tags=("4 Baby", "Marini", COLLECTION_TITLE), option_name="Kolor" if multiple else "Title", option_values=[item["colorName"] for item in items] if multiple else ["Default Title"], variants=tuple(variants), file_map=file_map, seo=seo_fields(title, items), source_items=items)


def media_and_variants(items: list[dict]) -> tuple[dict[str, str], list[SimpleNamespace]]:
    file_map, variants = {}, []
    for item in items:
        keys = media_keys(file_map, item)
        variants.append(SimpleNamespace(sku=item["sku"], barcode=item["barcode"], price=item["salePrice"], option_value=item["colorName"], file_key=keys[0]))
    return file_map, variants


def media_keys(file_map: dict[str, str], item: dict) -> list[str]:
    keys = []
    for index, path in enumerate(item["imagePaths"], start=1):
        key = f"{item['sku']}-{index}"
        file_map[key] = path
        keys.append(key)
    return keys


def description_spec(title: str, model: str, items: list[dict]) -> dict:
    subtitle, age, load, regulation, features = INFO[model]
    colors = ", ".join(item["colorName"] for item in items)
    return {"eyebrow": "4 Baby", "title": title, "subtitle": subtitle, "badges": badges(age, load, items), "introTitle": "Wygodne karmienie każdego dnia", "introText": "Praktyczne krzesełko pomaga stworzyć dziecku stabilne i wygodne miejsce do posiłku, a rodzicom ułatwia sprzątanie po karmieniu.", "producerTitle": "Najważniejsze cechy", "producerItems": features, "cards": feature_cards(), "detailsTitle": "Szczegóły", "details": detail_rows(model, colors, age, load, regulation), "safetyTitle": "Bezpieczeństwo", "safetyText": "Używaj krzesełka zgodnie z instrukcją producenta i zawsze pod opieką osoby dorosłej.", "sourceNote": "Opis przygotowany na podstawie danych Marini B2B i materiałów producenta 4 Baby."}


def badges(age: str, load: str, items: list[dict]) -> list[str]:
    color_badge = f"{len(items)} kolory" if len(items) > 1 else items[0]["colorName"]
    return [COLLECTION_TITLE, age, load or "6w1", color_badge]


def feature_cards() -> list[dict]:
    return [{"title": "Komfort dziecka", "text": "Regulacje pomagają dopasować pozycję do wieku i etapu rozwoju."}, {"title": "Wygoda rodzica", "text": "Łatwe czyszczenie i praktyczna tacka sprawdzają się przy codziennych posiłkach."}]


def detail_rows(model: str, colors: str, age: str, load: str, regulation: str) -> list[dict]:
    rows = [{"label": "Producent", "value": "4 Baby"}, {"label": "Model", "value": model.title()}, {"label": "Przeznaczenie", "value": COLLECTION_TITLE.lower()}, {"label": "Wiek dziecka", "value": age}, {"label": "Maksymalne obciążenie", "value": load}, {"label": "Regulacja", "value": regulation}, {"label": "Kolory", "value": colors}]
    return [row for row in rows if row["value"]]


def seo_fields(title: str, items: list[dict]) -> dict:
    colors = ", ".join(item["colorName"] for item in items)
    desc = f"{title}: krzesełko do karmienia 4 Baby z praktycznymi regulacjami. Kolory: {colors}."
    return {"title": f"{title} | MamaPack", "description": desc[:320]}


def validate_no_conflicts(client, products: list[SimpleNamespace]) -> None:
    duplicates = duplicate_skus(products)
    conflicts = shopify_conflicts(client, products)
    if duplicates or conflicts["skus"] or conflicts["handles"]:
        raise RuntimeError(json.dumps({"duplicates": duplicates, "conflicts": conflicts}, ensure_ascii=False, indent=2))


def duplicate_skus(products: list[SimpleNamespace]) -> list[str]:
    skus = [variant.sku for product in products for variant in product.variants]
    return sorted({sku for sku in skus if skus.count(sku) > 1})


def shopify_conflicts(client, products: list[SimpleNamespace]) -> dict:
    sku_conflicts = [variant.sku for product in products for variant in product.variants if variant_sku_exists(client, variant.sku)]
    handle_conflicts = [product.handle for product in products if product_handle_exists(client, product.handle)]
    return {"skus": sku_conflicts, "handles": handle_conflicts}


def create_products(client, collection: dict, products: list[SimpleNamespace]) -> list[dict]:
    created = []
    for product in products:
        product_id = sync_product(client, product)
        update_product_seo(client, product_id, product.handle, product.seo["title"], product.seo["description"])
        add_products_to_collection(client, collection["id"], [product_id])
        created.append(verify_product(client, product_id, product))
    return created


VERIFY_QUERY = "query VerifyProduct($id: ID!) { product(id: $id) { id title handle status variants(first: 50) { nodes { sku barcode price selectedOptions { name value } } } media(first: 100) { nodes { status alt mediaContentType } } collections(first: 20) { nodes { title handle } } seo { title description } } }"


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
    return [{"title": product.title, "handle": product.handle, "optionName": product.option_name, "variantCount": len(product.variants), "skus": [variant.sku for variant in product.variants], "variantValues": [variant.option_value for variant in product.variants]} for product in products]


def slugify(value: str) -> str:
    value = value.lower().translate(POLISH_TRANS)
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


if __name__ == "__main__":
    main()
