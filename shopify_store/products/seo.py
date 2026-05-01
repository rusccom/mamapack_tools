from shopify_store.core.user_errors import raise_for_user_errors


PRODUCT_SEO_UPDATE_MUTATION = """
mutation UpdateProductSeo($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      handle
      seo { title description }
    }
    userErrors { field message }
  }
}
"""


def update_product_seo(
    client,
    product_id: str,
    handle: str,
    seo_title: str,
    seo_description: str,
) -> dict:
    payload = product_seo_payload(product_id, handle, seo_title, seo_description)
    result = client.execute(PRODUCT_SEO_UPDATE_MUTATION, {"product": payload})
    update = result["productUpdate"]
    raise_for_user_errors(update["userErrors"])
    return update["product"]


def product_seo_payload(product_id: str, handle: str, title: str, description: str) -> dict:
    return {
        "id": product_id,
        "handle": handle,
        "seo": {"title": title, "description": description},
    }
