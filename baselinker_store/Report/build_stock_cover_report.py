from __future__ import annotations

import argparse
import calendar
import csv
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from baselinker_store.core.client import BaselinkerClient
from baselinker_store.core.credentials import load_baselinker_credentials


ORDER_FIELDS = [
    "sku",
    "name",
    "stock_now",
    "sold_period",
    "avg_daily",
    "needed_for_cover",
    "order_qty",
    "stock_cover_days",
]
REPORT_FIELDS = [
    "product_id",
    "parent_id",
    "sku",
    "name",
    "stock_now",
    "sold_period",
    "avg_daily",
    "needed_for_cover",
    "order_qty",
    "stock_cover_days",
    "status",
]
EXCLUDED_STATUS_WORDS = ("anul", "zwrot", "cancel", "return")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales-months", type=int, default=2)
    parser.add_argument("--sales-days", type=int)
    parser.add_argument("--cover-days", type=int, default=14)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    return parser.parse_args()


def main():
    args = parse_args()
    start_at, end_at = report_period(args)
    sales_days = period_days(start_at, end_at)
    creds = load_baselinker_credentials(PROJECT_ROOT)
    client = BaselinkerClient(creds.token)
    products = fetch_products(client, creds.inventory_id)
    excluded = excluded_status_ids(client)
    orders = fetch_orders(client, start_at, end_at, excluded)
    sales = collect_sales(orders, creds.inventory_id)
    rows = build_rows(products, sales, sales_days, args.cover_days)
    paths = write_outputs(args.output_dir, rows)
    print_summary(rows, orders, paths, start_at, end_at)


def report_period(args):
    end_at = datetime.now().astimezone()
    start_at = end_at - timedelta(days=args.sales_days) if args.sales_days else subtract_months(end_at, args.sales_months)
    return start_at.replace(hour=0, minute=0, second=0, microsecond=0), end_at


def subtract_months(value, months):
    year = value.year
    month = value.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def period_days(start_at, end_at):
    seconds = (end_at - start_at).total_seconds()
    return max(1, seconds / 86400)


def fetch_products(client, inventory_id):
    page = 1
    products = []
    while True:
        batch = inventory_page(client, inventory_id, page)
        products.extend(batch)
        if len(batch) < 1000:
            return products
        page += 1


def inventory_page(client, inventory_id, page):
    params = {
        "inventory_id": inventory_id,
        "include_variants": True,
        "page": page,
        "filter_sort": "id ASC",
    }
    data = client.execute("getInventoryProductsList", params)
    return product_values(data.get("products", {}))


def product_values(products):
    return list(products.values()) if isinstance(products, dict) else list(products)


def excluded_status_ids(client):
    data = client.execute("getOrderStatusList", {})
    result = set()
    for item in data.get("statuses", []):
        if excluded_status(item):
            result.add(int(item.get("id") or 0))
    return result


def excluded_status(item):
    text = f"{item.get('name', '')} {item.get('name_for_customer', '')}".casefold()
    return any(word in text for word in EXCLUDED_STATUS_WORDS)


def fetch_orders(client, start_at, end_at, excluded):
    cursor = int(start_at.timestamp())
    end_ts = int(end_at.timestamp())
    orders, seen = [], set()
    while cursor <= end_ts:
        batch = client.execute("getOrders", {"date_confirmed_from": cursor}).get("orders", [])
        fresh = fresh_orders(batch, seen, end_ts, excluded)
        orders.extend(fresh)
        if len(batch) < 100:
            return orders
        cursor = next_cursor(batch, cursor)
    return orders


def fresh_orders(batch, seen, end_ts, excluded):
    result = []
    for order in batch:
        order_id = int(order.get("order_id") or 0)
        if order_id in seen or not order_allowed(order, end_ts, excluded):
            continue
        seen.add(order_id)
        result.append(order)
    return result


def order_allowed(order, end_ts, excluded):
    if int(order.get("order_status_id") or 0) in excluded:
        return False
    order_ts = int(order.get("date_confirmed") or order.get("date_add") or 0)
    return 0 < order_ts <= end_ts and order.get("order_source") != "order_return"


def next_cursor(batch, current):
    dates = [int(item.get("date_confirmed") or item.get("date_add") or 0) for item in batch]
    return max(max(dates) + 1, current + 1)


def collect_sales(orders, inventory_id):
    by_id = defaultdict(float)
    by_sku = defaultdict(float)
    for order in orders:
        remember_order_sales(order, inventory_id, by_id, by_sku)
    return {"by_id": by_id, "by_sku": by_sku}


def remember_order_sales(order, inventory_id, by_id, by_sku):
    for item in order.get("products", []):
        if str(item.get("storage_id")) != str(inventory_id):
            continue
        quantity = float(item.get("quantity") or 0)
        by_id[order_item_id(item)] += quantity
        by_sku[str(item.get("sku", "")).strip()] += quantity


def order_item_id(item):
    variant_id = str(item.get("variant_id") or "0")
    return variant_id if variant_id != "0" else str(item.get("product_id") or "")


def build_rows(products, sales, sales_days, cover_days):
    parent_names = {str(item.get("id")): item.get("name", "") for item in products}
    parent_ids = {str(item.get("parent_id")) for item in products if int(item.get("parent_id") or 0)}
    rows = [build_row(item, parent_names, sales, sales_days, cover_days) for item in products]
    rows = [row for row in rows if include_row(row, parent_ids)]
    return sorted(rows, key=report_sort_key)


def build_row(item, parent_names, sales, sales_days, cover_days):
    stock = stock_total(item.get("stock", {}))
    sold = sold_quantity(item, sales)
    avg_daily = sold / sales_days if sales_days else 0
    needed = math.ceil(avg_daily * cover_days) if sold > 0 else 0
    order_qty = max(0, needed - math.floor(stock))
    return row_data(item, parent_names, stock, sold, avg_daily, needed, order_qty)


def row_data(item, parent_names, stock, sold, avg_daily, needed, order_qty):
    return {
        "product_id": str(item.get("id", "")),
        "parent_id": str(item.get("parent_id") or 0),
        "sku": str(item.get("sku", "")).strip(),
        "name": display_name(item, parent_names),
        "stock_now": pretty_number(stock),
        "sold_period": pretty_number(sold),
        "avg_daily": f"{avg_daily:.3f}".replace(".", ","),
        "needed_for_cover": str(needed),
        "order_qty": str(order_qty),
        "stock_cover_days": cover_days(stock, avg_daily),
        "status": "ORDER" if order_qty > 0 else "OK",
    }


def display_name(item, parent_names):
    parent_id = str(item.get("parent_id") or 0)
    if parent_id == "0":
        return str(item.get("name", ""))
    return f"{parent_names.get(parent_id, '')} - {item.get('name', '')}".strip(" -")


def sold_quantity(item, sales):
    product_id = str(item.get("id", ""))
    sku = str(item.get("sku", "")).strip()
    return sales["by_id"].get(product_id) or sales["by_sku"].get(sku, 0)


def stock_total(stock):
    if not isinstance(stock, dict):
        return float(stock or 0)
    return sum(float(value or 0) for value in stock.values())


def cover_days(stock, avg_daily):
    if avg_daily <= 0:
        return ""
    return f"{max(0, stock) / avg_daily:.1f}".replace(".", ",")


def pretty_number(value):
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".replace(".", ",")


def include_row(row, parent_ids):
    if row["product_id"] in parent_ids:
        return False
    return bool(row["sku"] or row["sold_period"] != "0" or row["stock_now"] != "0")


def report_sort_key(row):
    order_first = 0 if row["status"] == "ORDER" else 1
    cover = float(row["stock_cover_days"].replace(",", ".") or 999999)
    return (order_first, cover, row["name"])


def write_outputs(output_dir, rows):
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = output_dir / f"baselinker_stock_cover_{stamp}.csv"
    order_path = output_dir / f"baselinker_order_{stamp}.csv"
    write_csv(report_path, rows, REPORT_FIELDS)
    write_csv(order_path, order_rows(rows), ORDER_FIELDS)
    return {"report": report_path, "order": order_path}


def order_rows(rows):
    return [{field: row[field] for field in ORDER_FIELDS} for row in rows if row["status"] == "ORDER"]


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows, orders, paths, start_at, end_at):
    to_order = sum(1 for row in rows if row["status"] == "ORDER")
    print(f"period: {start_at.date()}..{end_at.date()}")
    print(f"orders: {len(orders)}")
    print(f"products: {len(rows)}")
    print(f"to_order: {to_order}")
    print(f"report: {paths['report']}")
    print(f"order: {paths['order']}")


if __name__ == "__main__":
    main()
