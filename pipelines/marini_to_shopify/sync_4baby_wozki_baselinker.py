import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from baselinker_store.core.client import BaselinkerClient
from baselinker_store.core.credentials import load_baselinker_credentials
from baselinker_store.inventory.context_resolver import get_inventory_context
from baselinker_store.inventory.product_index import inventory_sku_index
from baselinker_store.inventory.sync import sync_products
from shopify_store.core.credentials import load_shopify_access
from shopify_store.core.graphql import ShopifyGraphQL

SOURCE_REPORT = Path(__file__).with_name("forbaby_wozki_shopify_sync_report.json")
REPORT_DIR = ROOT / "store_reports" / "baselinker" / "2026-05-09"
REPORT_PATH = REPORT_DIR / "forbaby_wozki_baselinker_create_link_20260509.json"
PARENT_CATEGORY_ID = 2920334
CATEGORY_NAME = "Spacerówki"

PRODUCT_QUERY = """
query ProductForBaselinker($id: ID!) {
  product(id: $id) {
    id title handle status descriptionHtml vendor productType tags legacyResourceId
    media(first: 16) { nodes { ... on MediaImage { image { url } } } }
    variants(first: 250) {
      nodes {
        id legacyResourceId sku barcode price selectedOptions { name value }
        media(first: 10) { nodes { ... on MediaImage { image { url } } } }
      }
    }
  }
}
"""

def main():
    source = load_source_report()
    settings = load_baselinker_credentials(ROOT)
    bl = BaselinkerClient(settings.token)
    shopify_access = load_shopify_access(ROOT)
    shopify = ShopifyGraphQL(shopify_access)
    category = ensure_category(bl, settings.inventory_id)
    context = replace(get_inventory_context(bl, settings, shopify_access.store_domain), category_id=category["category_id"])
    products = [to_synced_product(fetch_product(shopify, item["product"]["id"])) for item in source["created"]]
    created_ids = sync_products(bl, context, products)
    parent_price_fixes = fix_parent_prices(bl, context, products, created_ids)
    index = inventory_sku_index(bl, context)
    details = fetch_details(bl, context, products, index, created_ids)
    verification = verify_links(context, products, index, details)
    save_report(source, context, category, created_ids, products, parent_price_fixes, details, verification)
    if not verification["allOk"]:
        raise RuntimeError("BaseLinker verification failed")
    print(f"BaseLinker synced {len(products)} products / {sum(len(p.variants) for p in products)} SKU.")

def load_source_report():
    return json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))

def ensure_category(client, inventory_id):
    categories = client.execute("getInventoryCategories", {"inventory_id": inventory_id}).get("categories", [])
    for item in categories:
        if item.get("name") == CATEGORY_NAME and int(item.get("parent_id") or 0) == PARENT_CATEGORY_ID:
            return {**item, "created": False}
    data = client.execute("addInventoryCategory", {"inventory_id": inventory_id, "name": CATEGORY_NAME, "parent_id": PARENT_CATEGORY_ID})
    return {"category_id": int(data["category_id"]), "name": CATEGORY_NAME, "parent_id": PARENT_CATEGORY_ID, "created": True}

def fetch_product(client, product_id):
    node = client.execute(PRODUCT_QUERY, {"id": product_id})["product"]
    if not node or node["status"] != "DRAFT":
        raise RuntimeError(f"Shopify product is not DRAFT: {product_id}")
    return node

def to_synced_product(node):
    variants = tuple(to_synced_variant(item) for item in node["variants"]["nodes"])
    return SimpleNamespace(
        handle=node["handle"], title=node["title"], description_html=node["descriptionHtml"],
        vendor=node["vendor"], product_type=node["productType"], tags=(),
        option_name=option_name(variants), option_values=tuple(v.option_value for v in variants),
        shopify_id=node["id"], legacy_resource_id=int(node["legacyResourceId"]),
        status=node["status"], media_urls=media_urls(node["media"]["nodes"]), variants=variants,
    )

def to_synced_variant(node):
    selected = node["selectedOptions"][0] if node.get("selectedOptions") else {"value": "Default Title"}
    return SimpleNamespace(
        option_value=selected["value"], sku=node["sku"], barcode=node.get("barcode") or "",
        price=node.get("price") or "", detail_url="", source_code="", source_title="",
        source_sku=node["sku"], shopify_id=node["id"], legacy_resource_id=int(node["legacyResourceId"]),
        media_urls=media_urls(node["media"]["nodes"]),
    )

def option_name(variants):
    if len(variants) == 1 and variants[0].option_value == "Default Title":
        return "Title"
    return "Kolor"

def media_urls(nodes):
    return tuple((item.get("image") or {}).get("url") for item in nodes if (item.get("image") or {}).get("url"))

def fix_parent_prices(client, context, products, parent_ids):
    fixes = []
    for product, parent_id in zip(products, parent_ids):
        if len(product.variants) == 1:
            continue
        price = product.variants[0].price
        payload = {"inventory_id": context.inventory_id, "product_id": parent_id, "prices": {str(context.default_price_group): float(price)}}
        fixes.append({"parentProductId": parent_id, "price": float(price), "response": client.execute("addInventoryProduct", payload)})
    return fixes

def fetch_details(client, context, products, index, parent_ids):
    ids = set(parent_ids)
    for product in products:
        ids.update(index[variant.sku]["id"] for variant in product.variants)
    data = client.execute("getInventoryProductsData", {"inventory_id": context.inventory_id, "products": sorted(ids)})
    return data.get("products", {})

def verify_links(context, products, index, details):
    checks = []
    for product in products:
        for variant in product.variants:
            row = index[variant.sku]
            detail = details[str(row["id"])]
            link = (detail.get("links") or {}).get(context.shopify_storage_id, {})
            checks.append(variant_check(product, variant, row, detail, link, context))
    return {"allOk": all(item["linkOk"] and item["priceOk"] for item in checks), "checks": checks}

def variant_check(product, variant, row, detail, link, context):
    expected_product = str(product.legacy_resource_id)
    expected_variant = str(variant.legacy_resource_id)
    price = (detail.get("prices") or {}).get(str(context.default_price_group))
    return {
        "sku": variant.sku, "baselinkerProductId": row["id"], "parentId": row["parent_id"],
        "expectedProductId": expected_product, "actualProductId": str(link.get("product_id", "")),
        "expectedVariantId": expected_variant, "actualVariantId": str(link.get("variant_id", "")),
        "linkOk": str(link.get("product_id", "")) == expected_product and str(link.get("variant_id", "")) == expected_variant,
        "price": detail.get("prices") or {}, "priceOk": float(price or 0) == float(variant.price),
    }

def product_report(products):
    return [{"title": p.title, "shopifyProductId": p.shopify_id, "shopifyLegacyResourceId": p.legacy_resource_id,
             "optionName": p.option_name, "variants": [variant_report(v) for v in p.variants]} for p in products]

def variant_report(variant):
    return {"sku": variant.sku, "barcode": variant.barcode, "optionValue": variant.option_value,
            "shopifyVariantId": variant.shopify_id, "shopifyVariantLegacyResourceId": variant.legacy_resource_id}

def save_report(source, context, category, created_ids, products, fixes, details, verification):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "createdAt": datetime.now().astimezone().isoformat(), "sourceReport": str(SOURCE_REPORT),
        "inventoryId": context.inventory_id, "shopifyStorageId": context.shopify_storage_id,
        "priceGroupId": context.default_price_group, "category": category,
        "productCount": len(products), "variantSkuCount": sum(len(p.variants) for p in products),
        "createdOrUpdatedParentIds": created_ids, "parentPriceFixes": fixes,
        "shopifyProducts": product_report(products), "baselinkerDetails": details, "verification": verification,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
