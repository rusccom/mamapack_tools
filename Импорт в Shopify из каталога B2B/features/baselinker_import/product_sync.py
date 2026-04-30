from .settings import BaselinkerInventoryContext


def get_inventory_context(client, settings, store_domain):
    inventory = resolve_inventory(client, settings.inventory_id)
    storage_id = resolve_storage_id(client, settings, store_domain)
    return BaselinkerInventoryContext(
        inventory_id=settings.inventory_id,
        default_language=inventory["default_language"],
        default_price_group=int(inventory.get("default_price_group") or 0),
        category_id=settings.category_id,
        shopify_storage_id=storage_id,
    )


def resolve_inventory(client, inventory_id):
    data = client.execute("getInventories", {})
    for inventory in data["inventories"]:
        if int(inventory["inventory_id"]) == int(inventory_id):
            return inventory
    raise RuntimeError(f"BaseLinker inventory not found: {inventory_id}")


def resolve_storage_id(client, settings, store_domain):
    if settings.shopify_storage_id:
        return settings.shopify_storage_id
    storages = client.execute("getExternalStoragesList", {})["storages"]
    hint = settings.shopify_storage_name or store_domain.split(".")[0]
    matched = [item for item in storages if item["storage_id"].startswith("shop_") and hint.lower() in item["name"].lower()]
    if len(matched) == 1:
        return matched[0]["storage_id"]
    raise RuntimeError("Set BASELINKER_SHOPIFY_STORAGE_ID or BASELINKER_SHOPIFY_STORAGE_NAME.")


def inventory_skus(client, context):
    page = 1
    result = set()
    while True:
        params = {
            "inventory_id": context.inventory_id,
            "include_variants": True,
            "page": page,
            "filter_sort": "id ASC",
        }
        products = client.execute("getInventoryProductsList", params).get("products", {})
        if not products:
            return result
        for item in products.values():
            sku = item.get("sku", "")
            if sku:
                result.add(sku)
        if len(products) < 1000:
            return result
        page += 1


def ensure_unique_skus(client, context, products):
    existing = inventory_skus(client, context)
    for product in products:
        for variant in product.variants:
            if variant.sku in existing:
                raise RuntimeError(f"BaseLinker duplicate SKU: {variant.sku}")
            existing.add(variant.sku)


def product_images(urls):
    result = {}
    for index, url in enumerate(urls[:16]):
        result[str(index)] = f"url:{url}"
    return result


def text_fields(name, description):
    return {
        "name": name,
        "description": description,
    }


def prices_map(context, price):
    if not context.default_price_group or not price:
        return {}
    return {str(context.default_price_group): float(price)}


def link_map(context, product_id, variant_id):
    value = {"product_id": str(product_id)}
    if variant_id:
        value["variant_id"] = str(variant_id)
    return {context.shopify_storage_id: value}


def variant_name(product, variant):
    if product.option_name == "Title":
        return product.title
    return f"{product.title} - {product.option_name}: {variant.option_value}"


def effective_media_urls(product):
    if product.media_urls:
        return product.media_urls
    urls = []
    for variant in product.variants:
        urls.extend(variant.media_urls)
    return tuple(dict.fromkeys(urls))


def main_payload(context, product):
    payload = {
        "inventory_id": context.inventory_id,
        "text_fields": text_fields(product.title, product.description_html),
        "tags": [item for item in product.tags if item],
        "images": product_images(effective_media_urls(product)),
        "links": link_map(context, product.legacy_resource_id, 0 if len(product.variants) > 1 else product.variants[0].legacy_resource_id),
    }
    if context.category_id:
        payload["category_id"] = context.category_id
    if len(product.variants) == 1:
        variant = product.variants[0]
        payload["sku"] = variant.sku
        payload["ean"] = variant.barcode
        payload["prices"] = prices_map(context, variant.price)
    return {key: value for key, value in payload.items() if value not in ("", None, [], {})}


def variant_payload(context, parent_id, product, variant):
    payload = {
        "inventory_id": context.inventory_id,
        "parent_id": parent_id,
        "sku": variant.sku,
        "ean": variant.barcode,
        "prices": prices_map(context, variant.price),
        "text_fields": text_fields(variant_name(product, variant), product.description_html),
        "links": link_map(context, product.legacy_resource_id, variant.legacy_resource_id),
    }
    return {key: value for key, value in payload.items() if value not in ("", None, [], {})}


def add_product(client, payload):
    data = client.execute("addInventoryProduct", payload)
    return str(data["product_id"])


def sync_product(client, context, product):
    parent_id = add_product(client, main_payload(context, product))
    if len(product.variants) == 1:
        return parent_id
    for variant in product.variants:
        add_product(client, variant_payload(context, parent_id, product, variant))
    return parent_id


def sync_products(client, context, products):
    ensure_unique_skus(client, context, products)
    created = []
    total = len(products)
    for index, product in enumerate(products, start=1):
        print(f"[BL {index}/{total}] {product.title}")
        created.append(sync_product(client, context, product))
    return created
