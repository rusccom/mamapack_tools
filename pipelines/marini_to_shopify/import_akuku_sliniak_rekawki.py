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

XML_PATH = ROOT / "wholesale_sources" / "marini" / "marini-b2b.xml"
IMAGE_DIR = ROOT / "wholesale_sources" / "marini" / "images" / "akuku_sliniak_rekawki"
REPORT_PATH = Path(__file__).with_name("akuku_sliniak_rekawki_shopify_sync_report.json")
COLLECTION_TITLE = "Śliniaki"
COLLECTION_HANDLE = "sliniaki"
PRODUCT_TITLE = "AKUKU Śliniak z rękawkiem"
SOURCE_NAMES = ("AKUKU A0517 Śliniak z rękawkiem BORSUK", "AKUKU A0518 Śliniak z rękawkiem MISIO")
SKU_MAP = {"BORSUK": "A0517", "MISIO": "A0518"}
POLISH_TRANS = str.maketrans({"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z"})


def main() -> None:
    items = load_items()
    product = build_product(items)
    client = build_shopify_client(ROOT)
    collection = ensure_collection(client, COLLECTION_TITLE, COLLECTION_HANDLE)
    validate_no_conflicts(client, product)
    created = create_product(client, collection, product)
    save_report(collection, items, product, created)
    print(f"Created Shopify draft product with {len(items)} variants.")


def load_items() -> list[dict]:
    nodes = xml_nodes_by_name()
    return [enrich_item(nodes[name]) for name in SOURCE_NAMES]


def xml_nodes_by_name() -> dict[str, dict]:
    result = {}
    root = ET.parse(XML_PATH).getroot()
    for node in root.findall("b2b"):
        data = {child.tag: (child.text or "").strip() for child in node}
        if data.get("nazwa") in SOURCE_NAMES:
            result[data["nazwa"]] = data
    missing = [name for name in SOURCE_NAMES if name not in result]
    if missing:
        raise RuntimeError(f"Missing Marini XML items: {missing}")
    return result


def enrich_item(data: dict) -> dict:
    pattern = pattern_name(data["nazwa"])
    return {
        "sourceSku": data["kod"],
        "sku": SKU_MAP[pattern.upper()],
        "barcode": data.get("EAN", ""),
        "sourceTitle": data["nazwa"],
        "pattern": pattern,
        "purchaseNet": float(data.get("cena") or 0),
        "salePrice": f"{float(data.get('cena') or 0) * 1.6:.2f}",
        "stockText": data.get("stan", ""),
        "description": data.get("opis", ""),
        "imagePaths": image_paths_for(data),
    }


def pattern_name(title: str) -> str:
    return title.rsplit(" ", 1)[-1].title()


def image_paths_for(data: dict) -> list[str]:
    urls = (data.get("zdjecia") or "").split()[:1]
    return [path for path in download_all(urls, SKU_MAP[pattern_name(data["nazwa"]).upper()]) if path]


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
    return SimpleNamespace(title=PRODUCT_TITLE, handle=slugify(PRODUCT_TITLE), description_html=build_product_description(description_spec(items)), vendor="AKUKU", product_type=COLLECTION_TITLE, tags=("AKUKU", "Marini", COLLECTION_TITLE), option_name="Wzór", option_values=[item["pattern"] for item in items], variants=tuple(variants), file_map=file_map, seo=seo_fields(items), source_items=items)


def media_and_variants(items: list[dict]) -> tuple[dict[str, str], list[SimpleNamespace]]:
    file_map, variants = {}, []
    for item in items:
        key = item["sku"]
        file_map[key] = item["imagePaths"][0]
        variants.append(SimpleNamespace(sku=item["sku"], barcode=item["barcode"], price=item["salePrice"], option_value=item["pattern"], file_key=key))
    return file_map, variants


def description_spec(items: list[dict]) -> dict:
    patterns = ", ".join(item["pattern"] for item in items)
    return {"eyebrow": "AKUKU", "title": PRODUCT_TITLE, "subtitle": "Lekki śliniak z rękawkami, który chroni ubranko dziecka podczas jedzenia i zabawy.", "badges": ["100% EVA", "33 x 35 cm", f"Wzory: {patterns}"], "introTitle": "Ochrona ubranka przy posiłkach", "introText": "Fartuszek z rękawkami pomaga ograniczyć zabrudzenia podczas karmienia, malowania i codziennych zabaw. Duża kieszeń zatrzymuje resztki jedzenia, a zapięcie na rzep ułatwia zakładanie.", "producerTitle": "Najważniejsze cechy", "producerItems": ["lekki, miękki i łatwo zmywalny materiał EVA", "długie rękawki chroniące ubranko", "praktyczna kieszeń na resztki pokarmu", "wygodne zapięcie na rzep"], "cards": [{"title": "Do jedzenia", "text": "Pomaga utrzymać ubranko w czystości podczas posiłku."}, {"title": "Do zabawy", "text": "Sprawdza się także przy kreatywnych aktywnościach dziecka."}], "detailsTitle": "Dane produktu", "details": detail_rows(items, patterns), "careTitle": "Pielęgnacja", "careSteps": ["Po jedzeniu umyj śliniak w ciepłej wodzie z mydłem dla dzieci.", "Przed użyciem sprawdź stan produktu i zapięcia."], "safetyTitle": "Ważne", "safetyText": "Produkt należy stosować pod opieką osoby dorosłej i zgodnie z przeznaczeniem.", "sourceNote": "Opis przygotowany na podstawie danych Marini B2B."}


def detail_rows(items: list[dict], patterns: str) -> list[dict]:
    return [{"label": "Marka", "value": "AKUKU"}, {"label": "Materiał", "value": "100% EVA"}, {"label": "Rozmiar", "value": "33 x 35 cm"}, {"label": "Wzory", "value": patterns}, {"label": "SKU wariantów", "value": ", ".join(item["sku"] for item in items)}, {"label": "EAN", "value": ", ".join(item["barcode"] for item in items)}]


def seo_fields(items: list[dict]) -> dict:
    patterns = ", ".join(item["pattern"] for item in items)
    desc = f"{PRODUCT_TITLE} AKUKU z lekkiego EVA. Śliniak z rękawkami, kieszonką i zapięciem na rzep. Wzory: {patterns}."
    return {"title": f"{PRODUCT_TITLE} | MamaPack", "description": desc[:320]}


def validate_no_conflicts(client, product: SimpleNamespace) -> None:
    sku_conflicts = [variant.sku for variant in product.variants if variant_sku_exists(client, variant.sku)]
    handle_conflicts = [product.handle] if product_handle_exists(client, product.handle) else []
    if sku_conflicts or handle_conflicts:
        raise RuntimeError(json.dumps({"skuConflicts": sku_conflicts, "handleConflicts": handle_conflicts}, ensure_ascii=False, indent=2))


def create_product(client, collection: dict, product: SimpleNamespace) -> dict:
    product_id = sync_product(client, product)
    update_product_seo(client, product_id, product.handle, product.seo["title"], product.seo["description"])
    add_products_to_collection(client, collection["id"], [product_id])
    return verify_product(client, product_id, product)


VERIFY_QUERY = "query VerifyProduct($id: ID!) { product(id: $id) { id title handle status variants(first: 20) { nodes { sku barcode price selectedOptions { name value } } } media(first: 20) { nodes { status alt mediaContentType } } collections(first: 20) { nodes { title handle } } seo { title description } } }"


def verify_product(client, product_id: str, product: SimpleNamespace) -> dict:
    data = {}
    for _ in range(18):
        data = client.execute(VERIFY_QUERY, {"id": product_id})["product"]
        statuses = [node["status"] for node in data["media"]["nodes"]]
        if statuses and all(status == "READY" for status in statuses):
            break
        time.sleep(5)
    return {"product": data, "sourceItems": product.source_items}


def save_report(collection: dict, items: list[dict], product: SimpleNamespace, created: dict) -> None:
    report = {"createdAt": datetime.now().astimezone().isoformat(), "collection": collection, "sourceItems": items, "product": {"title": product.title, "handle": product.handle, "optionName": product.option_name, "skus": [v.sku for v in product.variants], "variantValues": [v.option_value for v in product.variants]}, "created": created}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.lower().translate(POLISH_TRANS)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text)).strip("-")


if __name__ == "__main__":
    main()
