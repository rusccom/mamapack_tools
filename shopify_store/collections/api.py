from shopify_store.core.user_errors import raise_for_user_errors


COLLECTION_BY_HANDLE_QUERY = """
query CollectionByHandle($query: String!) {
  collections(first: 1, query: $query) {
    nodes { id title handle }
  }
}
"""

COLLECTION_CREATE_MUTATION = """
mutation CreateCollection($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id title handle }
    userErrors { field message }
  }
}
"""

COLLECTION_ADD_PRODUCTS_MUTATION = """
mutation AddProductsToCollection($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id title handle }
    userErrors { field message }
  }
}
"""


def get_collection_by_handle(client, handle: str) -> dict | None:
    data = client.execute(COLLECTION_BY_HANDLE_QUERY, {"query": f"handle:{handle}"})
    nodes = data["collections"]["nodes"]
    return nodes[0] if nodes else None


def create_collection(client, title: str, handle: str) -> dict:
    result = client.execute(COLLECTION_CREATE_MUTATION, {"input": collection_payload(title, handle)})
    created = result["collectionCreate"]
    raise_for_user_errors(created["userErrors"])
    return created["collection"]


def ensure_collection(client, title: str, handle: str) -> dict:
    collection = get_collection_by_handle(client, handle)
    if collection:
        return collection
    return create_collection(client, title, handle)


def add_products_to_collection(client, collection_id: str, product_ids: list[str]) -> None:
    if not product_ids:
        return
    variables = {"id": collection_id, "productIds": product_ids}
    result = client.execute(COLLECTION_ADD_PRODUCTS_MUTATION, variables)
    raise_for_user_errors(result["collectionAddProducts"]["userErrors"])


def collection_payload(title: str, handle: str) -> dict:
    return {"title": title, "handle": handle}
