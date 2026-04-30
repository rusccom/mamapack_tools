from datetime import datetime
from pathlib import Path
import sys

SCRIPT_PATH = Path(__file__).resolve()
ROOT = next(
    (candidate for candidate in [SCRIPT_PATH.parent, *SCRIPT_PATH.parents] if (candidate / "shopify_seo").is_dir()),
    SCRIPT_PATH.parent,
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shopify_seo.api import ShopifyGraphQL, fetch_all_products, fetch_all_redirects, load_shopify_access
from shopify_seo.backup import dataclass_rows, write_backup_csv, write_backup_json
from shopify_seo.paths import project_root_from, shopify_backup_dir


def main() -> None:
    root = project_root_from(__file__)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    client = build_client(root)
    products = fetch_all_products(client)
    redirects = fetch_all_redirects(client)
    target_dir = shopify_backup_dir(root, stamp)
    save_products(target_dir, stamp, products)
    save_redirects(target_dir, stamp, redirects)
    print_backup_summary(len(products), len(redirects), stamp)


def build_client(root: Path) -> ShopifyGraphQL:
    store_domain, token, api_version = load_shopify_access(root)
    return ShopifyGraphQL(store_domain, token, api_version)


def save_products(target_dir: Path, stamp: str, products: list) -> None:
    rows = dataclass_rows(products)
    csv_path = target_dir / f"shopify_backup_products_{stamp}.csv"
    json_path = target_dir / f"shopify_backup_products_{stamp}.json"
    write_backup_csv(csv_path, rows)
    write_backup_json(json_path, {"items": rows, "count": len(rows)})


def save_redirects(target_dir: Path, stamp: str, redirects: list) -> None:
    rows = dataclass_rows(redirects)
    csv_path = target_dir / f"shopify_backup_redirects_{stamp}.csv"
    json_path = target_dir / f"shopify_backup_redirects_{stamp}.json"
    write_backup_csv(csv_path, rows)
    write_backup_json(json_path, {"items": rows, "count": len(rows)})


def print_backup_summary(product_count: int, redirect_count: int, stamp: str) -> None:
    print(f"Backup stamp: {stamp}")
    print(f"Products backed up: {product_count}")
    print(f"Redirects backed up: {redirect_count}")


if __name__ == "__main__":
    main()
