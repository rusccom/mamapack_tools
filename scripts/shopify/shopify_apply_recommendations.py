import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    (candidate for candidate in [SCRIPT_PATH.parent, *SCRIPT_PATH.parents] if (candidate / "shopify_seo").is_dir()),
    SCRIPT_PATH.parent,
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shopify_seo.api import ShopifyGraphQL, fetch_all_products, fetch_all_redirects, load_shopify_access
from shopify_seo.apply import apply_recommendations, validate_plan
from shopify_seo.backup import write_backup_csv, write_backup_json
from shopify_seo.paths import project_root_from, shopify_apply_dir
from shopify_seo.recommend import build_recommendations


def main() -> None:
    root = project_root_from(__file__)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    client = build_client(root)
    products = fetch_all_products(client)
    redirects = fetch_all_redirects(client)
    recommendations = build_recommendations(products)
    errors = validate_plan(recommendations, products, redirects)
    target_dir = shopify_apply_dir(root, stamp)
    save_plan(target_dir, stamp, recommendations, errors)
    if errors:
        raise RuntimeError("\n".join(errors))
    results = apply_recommendations(client, products, recommendations)
    save_results(target_dir, stamp, results)
    print_summary(results, stamp)


def build_client(root: Path) -> ShopifyGraphQL:
    store_domain, token, api_version = load_shopify_access(root)
    return ShopifyGraphQL(store_domain, token, api_version)


def save_plan(target_dir: Path, stamp: str, recommendations: list, errors: list[str]) -> None:
    rows = [asdict(item) for item in recommendations]
    csv_path = target_dir / f"shopify_apply_plan_{stamp}.csv"
    json_path = target_dir / f"shopify_apply_plan_{stamp}.json"
    write_backup_csv(csv_path, rows)
    write_backup_json(json_path, {"items": rows, "errors": errors, "count": len(rows)})


def save_results(target_dir: Path, stamp: str, results: list) -> None:
    rows = [asdict(item) for item in results]
    csv_path = target_dir / f"shopify_apply_results_{stamp}.csv"
    json_path = target_dir / f"shopify_apply_results_{stamp}.json"
    write_backup_csv(csv_path, rows)
    write_backup_json(json_path, {"items": rows, "count": len(rows)})


def print_summary(results: list, stamp: str) -> None:
    success = [item for item in results if item.success]
    failed = [item for item in results if not item.success]
    print(f"Apply stamp: {stamp}")
    print(f"Updated products: {len(success)}")
    print(f"Failed products: {len(failed)}")


if __name__ == "__main__":
    main()
