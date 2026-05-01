import csv
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    (candidate for candidate in [SCRIPT_PATH.parent, *SCRIPT_PATH.parents] if (candidate / "shopify_store").is_dir()),
    SCRIPT_PATH.parent,
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shopify_store.seo.api import ShopifyGraphQL, fetch_all_products, load_shopify_access
from shopify_store.seo.paths import project_root_from, shopify_recommendations_dir
from shopify_store.seo.recommend import build_recommendations


def main() -> None:
    root = project_root_from(__file__)
    store_domain, token, api_version = load_shopify_access(root)
    client = ShopifyGraphQL(store_domain, token, api_version)
    products = fetch_all_products(client)
    recommendations = build_recommendations(products)
    stamp = str(date.today())
    target_dir = shopify_recommendations_dir(root, stamp)
    csv_path = target_dir / f"shopify_products_seo_recommendations_{stamp}.csv"
    json_path = target_dir / f"shopify_products_seo_recommendations_{stamp}.json"
    write_csv(csv_path, recommendations)
    write_json(json_path, recommendations, store_domain)
    print_summary(csv_path, json_path, recommendations)


def write_csv(target: Path, recommendations: list) -> None:
    rows = [asdict(item) for item in recommendations]
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(target: Path, recommendations: list, store_domain: str) -> None:
    payload = {
        "store_domain": store_domain,
        "generated_at": str(date.today()),
        "counts": build_counts(recommendations),
        "products": [asdict(item) for item in recommendations],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_counts(recommendations: list) -> dict:
    flags = Counter()
    statuses = Counter()
    for item in recommendations:
        statuses[item.status] += 1
        if item.change_handle:
            flags["change_handle"] += 1
        if item.change_seo_title:
            flags["change_seo_title"] += 1
        if item.change_seo_description:
            flags["change_seo_description"] += 1
    return {
        "total_products": len(recommendations),
        "statuses": dict(statuses),
        "changes": dict(flags),
    }


def print_summary(csv_path: Path, json_path: Path, recommendations: list) -> None:
    counts = build_counts(recommendations)
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Products: {counts['total_products']}")
    print(f"Statuses: {counts['statuses']}")
    print(f"Changes: {counts['changes']}")


if __name__ == "__main__":
    main()
