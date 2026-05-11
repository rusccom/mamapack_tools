from .payloads import main_payload, variant_payload
from .product_index import inventory_sku_index, item_ref
from .product_match import existing_variant_id, resolve_parent_id, validate_source_skus


def sync_products(client, context, products):
    validate_source_skus(products)
    sku_index = inventory_sku_index(client, context)
    created = []
    total = len(products)
    for index, product in enumerate(products, start=1):
        print(f"[BL {index}/{total}] {product.title}")
        created.append(sync_product(client, context, sku_index, product))
    return created


def sync_product(client, context, sku_index, product):
    parent_id = resolve_parent_id(product, sku_index)
    base_id = add_product(client, main_payload(context, product, parent_id))
    remember_main_sku(sku_index, product, base_id)
    if len(product.variants) == 1:
        return base_id
    sync_variants(client, context, sku_index, product, base_id)
    return base_id


def sync_variants(client, context, sku_index, product, parent_id):
    for variant in product.variants:
        existing_id = existing_variant_id(sku_index, variant)
        payload = variant_payload(context, parent_id, product, variant, existing_id)
        variant_id = add_product(client, payload)
        sku_index[variant.sku] = item_ref(variant_id, parent_id)


def remember_main_sku(sku_index, product, base_id):
    if len(product.variants) != 1:
        return
    sku = product.variants[0].sku
    sku_index[sku] = item_ref(base_id, 0)


def add_product(client, payload):
    data = client.execute("addInventoryProduct", payload)
    if data.get("warnings"):
        print(f"[BL warning] {data['warnings']}")
    return str(data["product_id"])
