def validate_source_skus(products):
    seen = set()
    for product in products:
        remember_product_skus(seen, product)


def remember_product_skus(seen, product):
    for variant in product.variants:
        if not variant.sku:
            raise RuntimeError(f"Shopify variant has no SKU: {product.title}")
        if variant.sku in seen:
            raise RuntimeError(f"Shopify duplicate SKU: {variant.sku}")
        seen.add(variant.sku)


def resolve_parent_id(product, sku_index):
    parent_ids = parent_ids_for_product(product, sku_index)
    if len(parent_ids) > 1:
        raise RuntimeError(f"BaseLinker variants belong to different parents: {product.title}")
    return next(iter(parent_ids), "")


def parent_ids_for_product(product, sku_index):
    ids = set()
    for variant in product.variants:
        row = sku_index.get(variant.sku)
        if row:
            validate_existing_shape(product, variant, row)
            ids.add(parent_id_from_row(row))
    return ids


def validate_existing_shape(product, variant, row):
    if len(product.variants) > 1 and row["parent_id"] == "0":
        raise RuntimeError(f"BaseLinker SKU exists as main product: {variant.sku}")
    if len(product.variants) == 1 and row["parent_id"] != "0":
        raise RuntimeError(f"BaseLinker SKU exists as variant: {variant.sku}")


def parent_id_from_row(row):
    if row["parent_id"] != "0":
        return row["parent_id"]
    return row["id"]


def existing_variant_id(sku_index, variant):
    row = sku_index.get(variant.sku)
    return row["id"] if row else ""
