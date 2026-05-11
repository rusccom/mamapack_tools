from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .settings import STOCK_DAY, WAREHOUSE_KEY, WARSAW


def build_rows(products, items, orders, suppliers, log_map):
    order_index = {int(row["id"]): row for row in orders}
    product_index = {int(row["id"]): row for row in products}
    temu_ids = temu_product_ids(items, order_index, suppliers)
    cost_map = purchase_cost_map(items, order_index, suppliers)
    parent_ids = variant_parent_ids(products)
    context = row_context(cost_map, log_map, temu_ids, parent_ids, product_index)
    rows = [row for row in spis_rows(products, context) if row]
    rows.sort(key=lambda row: (row["code"].lower(), row["name"].lower()))
    return rows, audit_data(rows, products, temu_ids, parent_ids)


def row_context(cost_map, log_map, temu_ids, parent_ids, product_index):
    return {
        "cost_map": cost_map,
        "log_map": log_map,
        "temu_ids": temu_ids,
        "parent_ids": parent_ids,
        "product_index": product_index,
    }


def spis_rows(products, context):
    for product in products:
        yield spis_row(product, context)


def spis_row(product, context):
    product_id = int(product["id"])
    if product_id in context["parent_ids"] or product_id in context["temu_ids"]:
        return None
    quantity = historical_stock(product, context["log_map"].get(str(product_id), []))
    if quantity <= 0:
        return None
    product_index = context["product_index"]
    cost, source = unit_cost(product, context["cost_map"], product_index)
    value = money(Decimal(str(quantity)) * cost)
    return {
        "code": product_code(product),
        "name": display_name(product, product_index),
        "unit": "szt.",
        "quantity": float(quantity),
        "unit_cost": float(cost),
        "value": float(value),
        "source": source,
        "product_id": product_id,
    }


def product_code(product):
    return str(product.get("sku") or product.get("ean") or product["id"])


def display_name(product, product_index):
    variant = base_name(product)
    parent_id = int(product.get("parent_id") or 0)
    parent = product_index.get(parent_id)
    if not parent:
        return variant
    parent_name = base_name(parent)
    if not variant or variant.lower() == parent_name.lower():
        return parent_name
    return f"{parent_name} - {variant}"


def base_name(product):
    return str(product.get("name") or text_name(product)).strip()


def historical_stock(product, logs):
    current = stock_value(product)
    delta = Decimal("0")
    for group in logs:
        for entry in group.get("entries", []):
            delta += stock_delta(entry)
    return current - delta


def stock_delta(entry):
    if entry.get("type") != 1 or entry.get("info") != WAREHOUSE_KEY:
        return Decimal("0")
    return decimal_value(entry.get("to")) - decimal_value(entry.get("from"))


def stock_value(product):
    stock = product.get("stock") or product.get("detail_stock") or {}
    return decimal_value(stock.get(WAREHOUSE_KEY, 0))


def unit_cost(product, cost_map, product_index):
    product_id = int(product["id"])
    if product_id in cost_map:
        return cost_map[product_id]["cost"], "dostawa"
    landed = decimal_value(product.get("average_landed_cost", 0))
    if landed > 0:
        return landed, "average_landed_cost"
    average = decimal_value(product.get("average_cost", 0))
    if average > 0:
        return average, "average_cost"
    return parent_unit_cost(product, cost_map, product_index)


def parent_unit_cost(product, cost_map, product_index):
    parent_id = int(product.get("parent_id") or 0)
    parent = product_index.get(parent_id, {})
    if parent_id in cost_map:
        return cost_map[parent_id]["cost"], "parent_dostawa"
    landed = decimal_value(parent.get("average_landed_cost", 0))
    if landed > 0:
        return landed, "parent_average_landed_cost"
    return decimal_value(parent.get("average_cost", 0)), "parent_average_cost"


def purchase_cost_map(items, order_index, suppliers):
    result = {}
    for item in items:
        order = order_index.get(int(item["order_id"]), {})
        if accepted_for_cost(order, suppliers):
            remember_cost(result, item, effective_date(order))
    return result


def accepted_for_cost(order, suppliers):
    if supplier_is_temu(order, suppliers):
        return False
    status = int(order.get("status") or 0)
    return status in (2, 3, 4) and effective_date(order) <= stock_timestamp()


def remember_cost(result, item, date_value):
    product_id = int(item.get("product_id") or 0)
    cost = decimal_value(item.get("item_cost", 0))
    quantity = decimal_value(item.get("completed_quantity") or item.get("quantity") or 0)
    if not product_id or cost <= 0 or quantity <= 0:
        return
    if product_id not in result or date_value >= result[product_id]["date"]:
        result[product_id] = {"cost": money(cost), "date": date_value}


def temu_product_ids(items, order_index, suppliers):
    result = set()
    for item in items:
        order = order_index.get(int(item["order_id"]), {})
        if supplier_is_temu(order, suppliers):
            result.add(int(item.get("product_id") or 0))
    return result


def variant_parent_ids(products):
    return {int(row.get("parent_id") or 0) for row in products if int(row.get("parent_id") or 0)}


def supplier_is_temu(order, suppliers):
    name = suppliers.get(str(order.get("supplier_id")), "")
    return "temu" in name.lower()


def effective_date(order):
    keys = ("date_received", "date_completed", "date_created")
    return max(int(order.get(key) or 0) for key in keys)


def audit_data(rows, products, temu_ids, parent_ids):
    costs = Counter(row["source"] for row in rows)
    return {
        "generated_at": datetime.now(WARSAW).isoformat(timespec="seconds"),
        "stock_day": STOCK_DAY,
        "product_count": len(products),
        "reported_rows": len(rows),
        "excluded_temu_products": len([pid for pid in temu_ids if pid]),
        "excluded_parent_products": len([pid for pid in parent_ids if pid]),
        "total_quantity": float(sum(Decimal(str(row["quantity"])) for row in rows)),
        "total_value": float(sum(Decimal(str(row["value"])) for row in rows)),
        "cost_sources": dict(costs),
    }


def stock_timestamp():
    return int(datetime.fromisoformat(f"{STOCK_DAY}T23:59:59").replace(tzinfo=WARSAW).timestamp())


def text_name(product):
    fields = product.get("text_fields") or {}
    return fields.get("name", str(product["id"]))


def decimal_value(value):
    try:
        return Decimal(str(value or 0))
    except InvalidOperation:
        return Decimal("0")


def money(value):
    return value.quantize(Decimal("0.01"))
