from shopify_store.core.user_errors import raise_for_user_errors
from shopify_store.media.staged_uploads import staged_files_map


PRODUCT_SET_MUTATION = """
mutation productSetSync($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      handle
      title
      status
      variants(first: 250) {
        nodes {
          id
          sku
          barcode
          price
          selectedOptions { name value }
        }
      }
    }
    userErrors { field message }
  }
}
"""


def sync_products(client, products) -> list[str]:
    results = []
    total = len(products)
    for index, product in enumerate(products, start=1):
        print(f"[{index}/{total}] {product.title}")
        results.append(sync_product(client, product))
    return results


def sync_product(client, product) -> str:
    staged_files = staged_files_map(product, client)
    variables = {"input": product_payload(product, staged_files), "synchronous": True}
    result = client.execute(PRODUCT_SET_MUTATION, variables)["productSet"]
    raise_for_user_errors(result["userErrors"])
    return result["product"]["id"]


def product_payload(product, staged_files: dict) -> dict:
    payload = {
        "title": product.title,
        "handle": product.handle,
        "descriptionHtml": product.description_html,
        "vendor": product.vendor,
        "productType": product.product_type,
        "status": "DRAFT",
        "tags": list(product.tags),
        "productOptions": option_input(product),
        "files": list(staged_files.values()),
        "variants": variant_payloads(product, staged_files),
    }
    return clean_payload(payload)


def variant_payloads(product, staged_files: dict) -> list[dict]:
    return [variant_payload(product, item, staged_files) for item in product.variants]


def option_input(product) -> list[dict]:
    if product.option_name == "Title":
        return []
    values = [{"name": item} for item in product.option_values]
    return [{"name": product.option_name, "position": 1, "values": values}]


def variant_payload(product, variant, staged_files: dict) -> dict:
    payload = {
        "sku": variant.sku,
        "barcode": variant.barcode,
        "price": variant.price,
        "taxable": True,
        "inventoryPolicy": "DENY",
        "optionValues": variant_option_values(product, variant),
        "file": staged_files.get(variant.file_key, {}),
    }
    return clean_payload(payload)


def variant_option_values(product, variant) -> list[dict]:
    if product.option_name == "Title":
        return []
    return [{"optionName": product.option_name, "name": variant.option_value}]


def clean_payload(value: dict) -> dict:
    return {key: item for key, item in value.items() if item not in ("", None, [], {})}
