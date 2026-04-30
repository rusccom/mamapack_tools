import time
from pathlib import Path

from shopify_seo.api import ShopifyGraphQL, load_shopify_access

from .content import build_description_html
from .media import download_images, stage_media


ARTICLE = "1001000244"
PRODUCT_ID = "gid://shopify/Product/10489556992333"

PRODUCT_QUERY = """
query ProductCard($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    descriptionHtml
    media(first: 20) {
      nodes {
        __typename
        ... on MediaImage {
          id
          alt
          image { url }
        }
      }
    }
  }
}
"""

PRODUCT_UPDATE_MUTATION = """
mutation UpdateProductCard($product: ProductUpdateInput!, $media: [CreateMediaInput!]) {
  productUpdate(product: $product, media: $media) {
    product {
      id
      title
      handle
      descriptionHtml
      media(first: 20) {
        nodes {
          __typename
          ... on MediaImage {
            id
            alt
            image { url }
          }
        }
      }
    }
    userErrors { field message }
  }
}
"""

PRODUCT_DELETE_MEDIA_MUTATION = """
mutation DeleteProductMedia($productId: ID!, $mediaIds: [ID!]!) {
  productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
    deletedMediaIds
    mediaUserErrors { field message }
  }
}
"""


def run(root: Path) -> dict:
    client = build_client(root)
    before = fetch_product(client)
    local_files = download_images(root, ARTICLE)
    media = stage_media(client, local_files, before["title"])
    updated = update_product(client, media)
    remove_media(client, updated["id"], before["media_ids"])
    final_state = wait_for_media(client, len(local_files))
    return summary(before, final_state, local_files)


def build_client(root: Path) -> ShopifyGraphQL:
    domain, token, version = load_shopify_access(root)
    return ShopifyGraphQL(domain, token, version)


def fetch_product(client: ShopifyGraphQL) -> dict:
    product = client.execute(PRODUCT_QUERY, {"id": PRODUCT_ID})["product"]
    if not product:
        raise RuntimeError(f"Shopify product not found: {PRODUCT_ID}")
    return product_snapshot(product)


def product_snapshot(product: dict) -> dict:
    media = media_nodes(product["media"]["nodes"])
    return {
        "id": product["id"],
        "title": product["title"],
        "handle": product["handle"],
        "description_html": product.get("descriptionHtml", "") or "",
        "media_ids": [item["id"] for item in media],
        "media_urls": [item["url"] for item in media],
    }


def media_nodes(nodes: list[dict]) -> list[dict]:
    items = []
    for node in nodes:
        image = node.get("image") or {}
        url = image.get("url", "")
        if url:
            items.append({"id": node["id"], "url": url, "alt": node.get("alt", "") or ""})
    return items


def update_product(client: ShopifyGraphQL, media: list[dict]) -> dict:
    product_input = {"id": PRODUCT_ID, "descriptionHtml": build_description_html(ARTICLE)}
    result = client.execute(
        PRODUCT_UPDATE_MUTATION,
        {"product": product_input, "media": media},
    )["productUpdate"]
    raise_for_errors(result["userErrors"])
    return product_snapshot(result["product"])


def remove_media(client: ShopifyGraphQL, product_id: str, media_ids: list[str]) -> None:
    if not media_ids:
        return
    result = client.execute(
        PRODUCT_DELETE_MEDIA_MUTATION,
        {"productId": product_id, "mediaIds": media_ids},
    )["productDeleteMedia"]
    raise_for_errors(result["mediaUserErrors"])


def wait_for_media(client: ShopifyGraphQL, expected_count: int) -> dict:
    for _ in range(12):
        current = fetch_product(client)
        if len(current["media_urls"]) == expected_count:
            return current
        time.sleep(5)
    return fetch_product(client)


def summary(before: dict, after: dict, local_files: list[Path]) -> dict:
    return {
        "product_id": after["id"],
        "handle": after["handle"],
        "downloaded_files": [str(path) for path in local_files],
        "old_media_count": len(before["media_urls"]),
        "new_media_count": len(after["media_urls"]),
        "media_urls": after["media_urls"],
    }


def raise_for_errors(errors: list[dict]) -> None:
    if not errors:
        return
    messages = [error_text(item) for item in errors]
    raise RuntimeError("; ".join(messages))


def error_text(error: dict) -> str:
    field = ".".join(error.get("field") or [])
    message = error.get("message") or "Unknown Shopify error"
    return f"{field}: {message}".strip(": ")
