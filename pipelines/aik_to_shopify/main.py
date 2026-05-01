import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.baselinker_import.client import BaselinkerClient
from features.baselinker_import.product_sync import get_inventory_context, sync_products as sync_baselinker_products
from features.baselinker_import.settings import load_baselinker_credentials
from features.product_data.build_products import build_shopify_products
from features.shopify_verification.verification import verify_product
from shopify_store.core.credentials import load_shopify_access
from shopify_store.core.graphql import ShopifyGraphQL
from shopify_store.products.identity import assign_unique_identities
from shopify_store.products.sync import sync_products
from shared.text_tools import slugify
from wholesale_sources.aik.catalog.catalog_client import collect_catalog_variants


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_search_text(raw_value):
    if raw_value.strip():
        return raw_value.strip()
    value = input("Что искать в B2B: ").strip()
    if value:
        return value
    raise SystemExit("Поисковая строка не указана.")


def preview_path(search_text):
    slug = slugify(search_text) or "catalog"
    name = f"preview-{slug}.json"
    return Path(__file__).resolve().parent / name


def preview_payload(search_text, products):
    items = []
    for product in products:
        item = {
            "handle": product.handle,
            "title": product.title,
            "vendor": product.vendor,
            "product_type": product.product_type,
            "option_name": product.option_name,
            "option_values": list(product.option_values),
            "tags": list(product.tags),
            "files": product.file_map,
            "variants": [asdict(variant) for variant in product.variants],
        }
        items.append(item)
    return {"search": search_text, "products": items}


def write_preview(search_text, products):
    target = preview_path(search_text)
    payload = preview_payload(search_text, products)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def shopify_client():
    return ShopifyGraphQL(shopify_access())


def shopify_access():
    try:
        return load_shopify_access(PROJECT_ROOT)
    except RuntimeError:
        raise SystemExit("Нужны SHOPIFY_STORE_DOMAIN и SHOPIFY_ADMIN_TOKEN.")


def baselinker_client():
    credentials = load_baselinker_credentials()
    if not credentials:
        raise SystemExit("Нужны BASELINKER_TOKEN и BASELINKER_INVENTORY_ID.")
    return credentials, BaselinkerClient(credentials.token)


def sync_to_shopify(products):
    client = shopify_client()
    guarded = assign_unique_identities(client, products)
    product_ids = sync_products(client, guarded)
    verified = []
    for product_id, draft in zip(product_ids, guarded):
        verified.append(verify_product(client, product_id, draft))
    return client, tuple(guarded), tuple(verified)


def sync_to_baselinker(verified_products):
    shopify = shopify_access()
    settings, client = baselinker_client()
    context = get_inventory_context(client, settings, shopify.store_domain)
    return sync_baselinker_products(client, context, verified_products)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


def main():
    configure_stdout()
    args = parse_args()
    search_text = resolve_search_text(args.search)
    variants = collect_catalog_variants(search_text, args.limit)
    products = build_shopify_products(variants)
    if args.dry_run:
        run_dry(search_text, variants, products)
        return
    try:
        run_sync(search_text, variants, products)
    except RuntimeError as error:
        raise SystemExit(str(error))


def run_dry(search_text, variants, products):
    target = write_preview(search_text, products)
    print(f"Search: {search_text}")
    print(f"Variants: {len(variants)}")
    print(f"Products: {len(products)}")
    print(f"Preview: {target}")


def run_sync(search_text, variants, products):
    _, guarded, verified = sync_to_shopify(products)
    baselinker_ids = sync_to_baselinker(verified)
    print(f"Search: {search_text}")
    print(f"Variants: {len(variants)}")
    print(f"Products: {len(guarded)}")
    print(f"Shopify synced: {len(verified)}")
    print(f"BaseLinker synced: {len(baselinker_ids)}")


if __name__ == "__main__":
    main()
