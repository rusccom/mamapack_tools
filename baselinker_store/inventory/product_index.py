def inventory_sku_index(client, context):
    page = 1
    result = {}
    while True:
        products = inventory_page(client, context, page)
        if not products:
            return result
        remember_skus(result, products)
        if len(products) < 1000:
            return result
        page += 1


def inventory_page(client, context, page):
    params = {
        "inventory_id": context.inventory_id,
        "include_variants": True,
        "page": page,
        "filter_sort": "id ASC",
    }
    return client.execute("getInventoryProductsList", params).get("products", {})


def remember_skus(index, products):
    for item in product_values(products):
        sku = str(item.get("sku", "")).strip()
        if not sku:
            continue
        remember_sku(index, sku, item)


def product_values(products):
    return products.values() if isinstance(products, dict) else products


def remember_sku(index, sku, item):
    current = index.get(sku)
    if current and str(current["id"]) != str(item.get("id")):
        raise RuntimeError(f"BaseLinker duplicate SKU: {sku}")
    index[sku] = item_ref(item.get("id"), item.get("parent_id"))


def item_ref(product_id, parent_id):
    return {
        "id": str(product_id),
        "parent_id": str(parent_id or 0),
    }
