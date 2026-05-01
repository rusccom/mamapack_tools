PRODUCT_BY_HANDLE_QUERY = """
query productLookup($query: String!) {
  products(first: 1, query: $query) {
    nodes { id handle }
  }
}
"""

VARIANT_BY_SKU_QUERY = """
query variantLookup($query: String!) {
  productVariants(first: 1, query: $query) {
    nodes { id sku }
  }
}
"""


def search_query(field: str, value: str) -> str:
    safe = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"{field}:'{safe}'"


def product_handle_exists(client, handle: str) -> bool:
    variables = {"query": search_query("handle", handle)}
    data = client.execute(PRODUCT_BY_HANDLE_QUERY, variables)
    return bool(data["products"]["nodes"])


def variant_sku_exists(client, sku: str) -> bool:
    variables = {"query": search_query("sku", sku)}
    data = client.execute(VARIANT_BY_SKU_QUERY, variables)
    return bool(data["productVariants"]["nodes"])


def suffixed_value(base: str, index: int, limit: int) -> str:
    if index == 1:
        return base[:limit]
    suffix = f"-{index}"
    root = base[: max(1, limit - len(suffix))].rstrip("-")
    return f"{root}{suffix}"


def make_unique_handle(client, base: str, used_handles: set[str]) -> str:
    index = 1
    while True:
        candidate = suffixed_value(base, index, 120)
        if is_available_handle(client, candidate, used_handles):
            used_handles.add(candidate)
            return candidate
        index += 1


def make_unique_sku(client, base: str, used_skus: set[str]) -> str:
    index = 1
    while True:
        candidate = suffixed_value(base, index, 40)
        if is_available_sku(client, candidate, used_skus):
            used_skus.add(candidate)
            return candidate
        index += 1


def is_available_handle(client, handle: str, used_handles: set[str]) -> bool:
    return handle not in used_handles and not product_handle_exists(client, handle)


def is_available_sku(client, sku: str, used_skus: set[str]) -> bool:
    return sku not in used_skus and not variant_sku_exists(client, sku)
