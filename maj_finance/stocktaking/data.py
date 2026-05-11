import json
from datetime import datetime

from baselinker_store.core.client import BaselinkerClient
from baselinker_store.core.credentials import load_baselinker_credentials

from .settings import AFTER_STOCK_DAY, CACHE_PATH, ROOT, WARSAW
from .valuation import build_rows


def base_client():
    access = load_baselinker_credentials(ROOT)
    if not access:
        raise RuntimeError("BaseLinker credentials missing")
    return BaselinkerClient(access.token), access.inventory_id


def load_cache():
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def cached(cache, key, loader):
    if key not in cache:
        cache[key] = loader()
        save_cache(cache)
    return cache[key]


def collect_data():
    client, inventory_id = base_client()
    cache = load_cache()
    suppliers = cached(cache, "suppliers", lambda: suppliers_map(client))
    orders = cached(cache, "purchase_orders", lambda: purchase_orders(client))
    items = cached(cache, "purchase_items", lambda: purchase_items(client, orders))
    products = cached(cache, "products", lambda: products_data(client, inventory_id))
    logs = stock_logs_for_products(client, cache, products)
    save_cache(cache)
    return build_rows(products, items, orders, suppliers, logs), suppliers


def suppliers_map(client):
    data = client.execute("getInventorySuppliers", {})
    raw = data.get("suppliers") or data.get("data", {}).get("suppliers") or []
    rows = raw.values() if isinstance(raw, dict) else raw
    return {str(row.get("supplier_id")): row.get("name", "") for row in rows}


def purchase_orders(client):
    rows = []
    page = 1
    while True:
        batch = client.execute("getInventoryPurchaseOrders", {"page": page})
        orders = values_list(batch.get("purchase_orders", []))
        rows.extend(orders)
        print(f"purchase_orders page={page} count={len(orders)}")
        if len(orders) < 100:
            return rows
        page += 1


def purchase_items(client, orders):
    rows = []
    total = len(orders)
    for index, order in enumerate(orders, start=1):
        rows.extend(order_items(client, int(order["id"])))
        if index % 25 == 0 or index == total:
            print(f"purchase_items {index}/{total}")
    return rows


def order_items(client, order_id):
    rows = []
    page = 1
    while True:
        data = client.execute("getInventoryPurchaseOrderItems", {"order_id": order_id, "page": page})
        items = values_list(data.get("items", []))
        rows.extend(with_order_id(items, order_id))
        if len(items) < 100:
            return rows
        page += 1


def with_order_id(items, order_id):
    result = []
    for item in items:
        item["order_id"] = order_id
        result.append(item)
    return result


def products_data(client, inventory_id):
    listed = product_list(client, inventory_id)
    details = product_details(client, inventory_id, [int(row["id"]) for row in listed])
    return [merge_product(row, details.get(str(row["id"]), {})) for row in listed]


def product_list(client, inventory_id):
    rows = []
    page = 1
    while True:
        params = {"inventory_id": inventory_id, "include_variants": True, "page": page, "filter_sort": "id ASC"}
        products = values_list(client.execute("getInventoryProductsList", params).get("products", []))
        rows.extend(products)
        print(f"products page={page} count={len(products)}")
        if len(products) < 1000:
            return rows
        page += 1


def product_details(client, inventory_id, ids):
    details = {}
    for batch in chunks(ids, 100):
        params = {"inventory_id": inventory_id, "products": batch}
        data = client.execute("getInventoryProductsData", params)
        details.update({str(key): value for key, value in data.get("products", {}).items()})
    return details


def merge_product(row, detail):
    merged = dict(row)
    merged["average_cost"] = detail.get("average_cost", 0)
    merged["average_landed_cost"] = detail.get("average_landed_cost", 0)
    merged["detail_stock"] = detail.get("stock", {})
    return merged


def stock_logs_for_products(client, cache, products):
    logs = cache.setdefault("stock_logs", {})
    ids = [str(row["id"]) for row in products]
    for index, product_id in enumerate(ids, start=1):
        if product_id not in logs:
            logs[product_id] = stock_logs(client, int(product_id))
            if index % 20 == 0:
                save_cache(cache)
        if index % 50 == 0 or index == len(ids):
            print(f"stock_logs {index}/{len(ids)}")
    return logs


def stock_logs(client, product_id):
    rows = []
    page = 1
    while True:
        logs = values_list(client.execute("getInventoryProductLogs", stock_log_params(product_id, page)).get("logs", []))
        rows.extend(logs)
        if len(logs) < 100:
            return rows
        page += 1


def stock_log_params(product_id, page):
    return {
        "product_id": product_id,
        "date_from": timestamp(f"{AFTER_STOCK_DAY}T00:00:00"),
        "date_to": int(datetime.now(WARSAW).timestamp()),
        "log_type": [1],
        "sort": "ASC",
        "page": page,
    }


def timestamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=WARSAW).timestamp())


def values_list(value):
    return list(value.values()) if isinstance(value, dict) else list(value or [])


def chunks(items, size):
    for index in range(0, len(items), size):
        yield items[index:index + size]
