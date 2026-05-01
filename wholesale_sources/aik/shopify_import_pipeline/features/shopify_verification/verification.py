from features.product_data.models import ShopifySyncedProduct, ShopifySyncedVariant


VERIFY_PRODUCT = """
query verifyProduct($id: ID!) {
  product(id: $id) {
    id
    handle
    title
    status
    legacyResourceId
    media(first: 16) {
      nodes {
        __typename
        ... on MediaImage {
          image { url }
        }
      }
    }
    variants(first: 250) {
      nodes {
        id
        legacyResourceId
        sku
        barcode
        price
        media(first: 10) {
          nodes {
            __typename
            ... on MediaImage {
              image { url }
            }
          }
        }
      }
    }
  }
}
"""


def media_urls(nodes):
    urls = []
    for item in nodes:
        image = item.get("image") or {}
        url = image.get("url", "")
        if url:
            urls.append(url)
    return tuple(urls)


def variant_map(node):
    return {item["sku"]: item for item in node["variants"]["nodes"]}


def validate_product(node, draft):
    if not node:
        raise RuntimeError(f"Shopify product not found after create: {draft.title}")
    if node["status"] != "DRAFT":
        raise RuntimeError(f"Shopify product is not draft: {draft.title}")
    if len(node["variants"]["nodes"]) != len(draft.variants):
        raise RuntimeError(f"Shopify variant count mismatch: {draft.title}")


def synced_variant(draft_variant, node):
    return ShopifySyncedVariant(
        option_value=draft_variant.option_value,
        sku=draft_variant.sku,
        barcode=node.get("barcode", "") or "",
        price=node.get("price", "") or draft_variant.price,
        detail_url=draft_variant.detail_url,
        source_code=draft_variant.source_code,
        source_title=draft_variant.source_title,
        source_sku=draft_variant.source_sku,
        shopify_id=node["id"],
        legacy_resource_id=int(node["legacyResourceId"]),
        media_urls=media_urls(node["media"]["nodes"]),
    )


def verify_product(client, product_id, draft):
    data = client.execute(VERIFY_PRODUCT, {"id": product_id})
    node = data["product"]
    validate_product(node, draft)
    variants = variant_map(node)
    synced = []
    for draft_variant in draft.variants:
        node_variant = variants.get(draft_variant.sku)
        if not node_variant:
            raise RuntimeError(f"Shopify variant missing after create: {draft_variant.sku}")
        synced.append(synced_variant(draft_variant, node_variant))
    return ShopifySyncedProduct(
        handle=node["handle"],
        title=draft.title,
        description_html=draft.description_html,
        vendor=draft.vendor,
        product_type=draft.product_type,
        tags=draft.tags,
        option_name=draft.option_name,
        option_values=draft.option_values,
        shopify_id=node["id"],
        legacy_resource_id=int(node["legacyResourceId"]),
        status=node["status"],
        media_urls=media_urls(node["media"]["nodes"]),
        variants=tuple(synced),
    )
