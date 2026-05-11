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
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from shopify_store.collections import add_products_to_collection, ensure_collection
from shopify_store.core.graphql import build_shopify_client
from shopify_store.products import build_product_description, sync_product, update_product_seo
from shopify_store.products.identity import product_handle_exists, variant_sku_exists
SOURCE_URL = "https://b2b.marini.pl/items/12?parent=10"
LIVE_PATH = ROOT / "wholesale_sources" / "marini" / "forbaby_wozki_live_extract.json"; XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "forbaby_wozki_12"; REPORT_PATH = Path(__file__).with_name("forbaby_wozki_shopify_sync_report.json")
COLLECTION_TITLE = "Spacerówki"; COLLECTION_HANDLE = "spacerowki"
REQUESTED_MODELS = ("COSMO", "RAPID", "STINGER", "TWIZZY", "TWEETY")
COLOR_NAMES = {
    "BLACK": "czarny",
    "GRAPHITE": "grafitowy",
    "KHAKI": "khaki",
    "MOKKA": "mokka",
    "OLIVE": "oliwkowy",
    "GREEN": "zielony",
    "GREY": "szary",
    "LIGHT GREY": "jasnoszary",
    "MELANGE GREY": "melange szary",
    "MELANGE LIGHT GREY": "melange jasnoszary",
    "DARK TURKUS": "ciemny turkus",
}
MODEL_TITLES = {
    "RAPID XXIV": "4 Baby Rapid XXIV wózek spacerowy",
    "STINGER PRO": "4 Baby Stinger PRO wózek spacerowy",
    "STINGER XXIII": "4 Baby Stinger XXIII wózek spacerowy",
    "STINGER XXIV": "4 Baby Stinger XXIV wózek spacerowy",
    "TWIZZY XXIII": "4 Baby Twizzy XXIII wózek spacerowy",
    "COSMO 2W1": "4 Baby Cosmo 2w1 wózek dziecięcy",
}
def main() -> None:
    live = load_live_items()
    xml = load_xml_metadata()
    selected, skipped = select_available_items(live, xml)
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
    return {
        "id": article["id"],
        "sku": article["code"]["value"],
        "title": article["name"],
        "imageId": (article.get("image") or {}).get("imageId"),
        "stock": int(stock.get("value") or 0),
        "purchaseNet": float(price.get("netPrice") or 0),
        "barcode": detail.get("ean") or "",
        "priceList": bool(detail.get("itemExistsInCurrentPriceList")),
    }
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
        reason = skip_reason(item)
        if reason:
            skipped.append({**item, "reason": reason})
            continue
        item.update(xml_enrichment(xml.get(item["sku"], {}), item))
        reason = skip_reason(item)
        if reason:
            skipped.append({**item, "reason": reason})
            continue
        selected.append(item)
    return selected, skipped
def xml_enrichment(xml_item: dict, item: dict) -> dict:
    title = xml_item.get("nazwa") or item["title"]
    model, color = split_model_color(title)
    return {
        "sourceTitle": title,
        "model": model,
        "color": color,
        "colorName": color_name(color),
        "imageUrls": image_urls(xml_item, item),
        "sourceDescription": xml_item.get("opis", ""),
        "salePrice": f"{item['purchaseNet'] * 1.6:.2f}",
    }
def skip_reason(item: dict) -> str:
    title = item["title"].upper()
    if not any(model in title for model in REQUESTED_MODELS):
        return "not requested model"
    if item["stock"] <= 0:
        return "stock is zero"
    if not item["priceList"] or item["purchaseNet"] <= 0:
        return "missing price"
    if "imageUrls" in item and not item["imageUrls"]:
        return "missing image"
    return ""
def image_urls(xml_item: dict, item: dict) -> list[str]:
    urls = (xml_item.get("zdjecia") or "").split()
    if urls:
        return [str(download_image(url, item["sku"], 1)) for url in urls[:1]]
    image_id = item.get("imageId")
    if not image_id:
        return []
    url = f"https://b2b.marini.pl/imagehandler.ashx?id={image_id}&width=1000&height=1000"
    return [str(download_image(url, item["sku"], 1))]
def download_image(url: str, sku: str, index: int) -> Path:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(url.split("?", 1)[0]).suffix or ".jpg"
    path = IMAGE_DIR / f"{sku}-{index}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return path
    subprocess.run(["curl.exe", "-sS", "-L", "--http1.1", "--ssl-no-revoke", "--retry", "5", "--retry-all-errors", "-k", "-A", "Mozilla/5.0", "-o", str(path), url], check=True)
    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError(f"Image download failed for {sku}: {url}")
    return path
def split_model_color(title: str) -> tuple[str, str]:
    text = title.upper().replace("4 BABY WÓZEK SPACEROWY ", "")
    text = text.replace("4 BABY WÓZEK ", "").replace(" PROMOCJA", "")
    models = ["STINGER PRO", "STINGER XXIII", "STINGER XXIV", "STINGER AIR",
              "RAPID XXIII", "RAPID XXIV", "TWIZZY XXIII", "COSMO 2W1"]
    for model in models:
        if text.startswith(model):
            return model, text.replace(model, "", 1).strip()
    return text, ""
def color_name(color: str) -> str:
    return COLOR_NAMES.get(color, color.lower())
def group_items(items: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        groups.setdefault(item["model"], []).append(item)
    return groups
def build_products(groups: dict[str, list[dict]]) -> list[SimpleNamespace]:
    return [build_product(model, items) for model, items in sorted(groups.items())]
def build_product(model: str, items: list[dict]) -> SimpleNamespace:
    title = MODEL_TITLES.get(model, f"4 Baby {model.title()} wózek spacerowy")
    file_map, variants = product_media_and_variants(items)
    return SimpleNamespace(
        title=title,
        handle=slugify(title),
        description_html=build_product_description(description_spec(title, model, items)),
        vendor="4 Baby",
        product_type="Wózki spacerowe",
        tags=("4 Baby", "Marini", "Spacerówki", "Wózki spacerowe"),
        option_name="Kolor" if len(items) > 1 else "Title",
        option_values=[item["colorName"] for item in items] if len(items) > 1 else ["Default Title"],
        variants=variants,
        file_map=file_map,
        seo=seo_fields(title, items),
        source_items=items,
    )
def product_media_and_variants(items: list[dict]) -> tuple[dict[str, str], tuple[SimpleNamespace, ...]]:
    file_map, variants = {}, []
    for item in items:
        keys = []
        for index, url in enumerate(item["imageUrls"], start=1):
            key = f"{item['sku']}-{index}"
            file_map[key] = url
            keys.append(key)
        variants.append(SimpleNamespace(
            sku=item["sku"], barcode=item["barcode"], price=item["salePrice"],
            option_value=item["colorName"], file_key=keys[0],
        ))
    return file_map, tuple(variants)
def description_spec(title: str, model: str, items: list[dict]) -> dict:
    colors = ", ".join(item["colorName"] for item in items)
    load = "od 6 miesiąca do 22 kg" if model.startswith("TWIZZY") else "do 22 kg"
    return {
        "eyebrow": "4 Baby",
        "title": title,
        "subtitle": f"Praktyczna spacerówka {model} do codziennych spacerów i wyjazdów.",
        "badges": ["Spacerówka", load, f"{len(items)} kolory" if len(items) > 1 else items[0]["colorName"]],
        "introTitle": "Dlaczego warto?",
        "introText": "Lekka i wygodna spacerówka z regulacją siedziska, osłoną na nogi oraz koszem na potrzebne akcesoria.",
        "producerTitle": "Najważniejsze cechy",
        "producerItems": feature_items(model),
        "cards": feature_cards(model),
        "detailsTitle": "Szczegóły",
        "details": detail_rows(model, colors, load),
        "safetyTitle": "Bezpieczeństwo",
        "safetyText": "Produkt należy użytkować zgodnie z instrukcją producenta i zawsze pod opieką osoby dorosłej.",
        "sourceNote": "Opis przygotowany na podstawie danych Marini B2B i materiałów producenta 4 Baby.",
    }
def feature_items(model: str) -> list[str]:
    if model.startswith("TWIZZY"):
        return ["Wielofunkcyjna budka z ochroną UPF 50+.", "Oparcie rozkładane do pozycji leżącej.", "Torba transportowa w zestawie."]
    if model == "STINGER PRO":
        return ["Aluminiowa rama i duże bezobsługowe koła żelowe.", "Regulowane oparcie i podnóżek.", "Ocieplana osłona na nogi."]
    if model.startswith("STINGER"):
        return ["Aluminiowa rama i amortyzowane koła EVA.", "Szybkie składanie jedną ręką.", "Przedłużana budka z wentylacją."]
    return ["Regulowana rączka, oparcie i podnóżek.", "Amortyzacja przód i tył.", "Uchwyt na kubek i osłona na nogi."]
def feature_cards(model: str) -> list[dict]:
    travel = "Kompaktowa forma sprawdza się w podróży." if model.startswith("TWIZZY") else "Stabilna konstrukcja pomaga w codziennym prowadzeniu."
    return [
        {"title": "Komfort dziecka", "text": "Regulowane elementy ułatwiają dopasowanie pozycji podczas spaceru."},
        {"title": "Wygoda rodzica", "text": travel},
    ]
def detail_rows(model: str, colors: str, load: str) -> list[dict]:
    return [
        {"label": "Producent", "value": "4 Baby"},
        {"label": "Model", "value": model},
        {"label": "Przeznaczenie", "value": "wózek spacerowy"},
        {"label": "Zakres użytkowania", "value": load},
        {"label": "Kolory", "value": colors},
    ]
def seo_fields(title: str, items: list[dict]) -> dict:
    colors = ", ".join(item["colorName"] for item in items)
    desc = f"{title} od 4 Baby: spacerówka do 22 kg. Dostępne kolory: {colors}."
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
VERIFY_QUERY = """
query VerifyProduct($id: ID!) {
  product(id: $id) {
    id title handle status
    variants(first: 50) { nodes { sku barcode price selectedOptions { name value } } }
    media(first: 100) { nodes { status } }
    collections(first: 20) { nodes { title handle } }
    seo { title description }
  }
}
"""
def verify_product(client, product_id: str, product: SimpleNamespace) -> dict:
    data = {}
    for _ in range(12):
        data = client.execute(VERIFY_QUERY, {"id": product_id})["product"]
        statuses = [node["status"] for node in data["media"]["nodes"]]
        if statuses and all(status == "READY" for status in statuses):
            break
        time.sleep(5)
    return {"product": data, "sourceItems": product.source_items}
def save_report(collection: dict, selected: list[dict], skipped: list[dict], products: list[SimpleNamespace], created: list[dict]) -> None:
    report = {
        "createdAt": datetime.now().astimezone().isoformat(),
        "sourceUrl": SOURCE_URL,
        "collection": collection,
        "availableSkuCount": len(selected),
        "skippedCount": len(skipped),
        "skipped": skipped,
        "productCountAfterGrouping": len(products),
        "products": product_report(products),
        "created": created,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
def product_report(products: list[SimpleNamespace]) -> list[dict]:
    return [{
        "title": product.title,
        "handle": product.handle,
        "optionName": product.option_name,
        "variantCount": len(product.variants),
        "skus": [variant.sku for variant in product.variants],
        "variantValues": [variant.option_value for variant in product.variants],
    } for product in products]
def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
if __name__ == "__main__":
    main()
