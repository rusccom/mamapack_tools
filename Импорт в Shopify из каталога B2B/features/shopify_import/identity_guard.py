from dataclasses import replace


PRODUCT_BY_QUERY = """
query productLookup($query: String!) {
  products(first: 1, query: $query) {
    nodes { id handle }
  }
}
"""


VARIANT_BY_QUERY = """
query variantLookup($query: String!) {
  productVariants(first: 1, query: $query) {
    nodes { id sku }
  }
}
"""


def search_query(field, value):
    safe = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"{field}:'{safe}'"


def exists_product_handle(client, handle):
    data = client.execute(PRODUCT_BY_QUERY, {"query": search_query("handle", handle)})
    return bool(data["products"]["nodes"])


def exists_variant_sku(client, sku):
    data = client.execute(VARIANT_BY_QUERY, {"query": search_query("sku", sku)})
    return bool(data["productVariants"]["nodes"])


def suffixed_value(base, index, limit):
    if index == 1:
        return base[:limit]
    suffix = f"-{index}"
    root = base[: max(1, limit - len(suffix))].rstrip("-")
    return f"{root}{suffix}"


def unique_handle(client, base, used_handles):
    index = 1
    while True:
        candidate = suffixed_value(base, index, 120)
        if candidate not in used_handles and not exists_product_handle(client, candidate):
            used_handles.add(candidate)
            return candidate
        index += 1


def unique_sku(client, base, used_skus):
    index = 1
    while True:
        candidate = suffixed_value(base, index, 40)
        if candidate not in used_skus and not exists_variant_sku(client, candidate):
            used_skus.add(candidate)
            return candidate
        index += 1


def assign_unique_identities(client, products):
    used_handles = set()
    used_skus = set()
    result = []
    for product in products:
        handle = unique_handle(client, product.handle, used_handles)
        variants = []
        for variant in product.variants:
            sku = unique_sku(client, variant.sku, used_skus)
            variants.append(replace(variant, sku=sku))
        result.append(replace(product, handle=handle, variants=tuple(variants)))
    return result
