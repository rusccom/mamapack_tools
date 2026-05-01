from .staged_uploads import staged_files_map


PRODUCT_SET = """
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

def option_input(product):
    if product.option_name == "Title":
        return []
    values = [{"name": item} for item in product.option_values]
    return [{"name": product.option_name, "position": 1, "values": values}]


def variant_option_values(product, variant):
    if product.option_name == "Title":
        return []
    return [{"optionName": product.option_name, "name": variant.option_value}]


def clean_payload(value):
    result = {}
    for key, item in value.items():
        if item in ("", None, [], {}):
            continue
        result[key] = item
    return result


def variant_payload(product, variant, staged_files):
    file_payload = staged_files.get(variant.file_key, {})
    payload = {
        "sku": variant.sku,
        "barcode": variant.barcode,
        "price": variant.price,
        "taxable": True,
        "inventoryPolicy": "DENY",
        "optionValues": variant_option_values(product, variant),
        "file": file_payload,
    }
    return clean_payload(payload)


def product_payload(product, staged_files):
    files = list(staged_files.values())
    payload = {
        "title": product.title,
        "handle": product.handle,
        "descriptionHtml": product.description_html,
        "vendor": product.vendor,
        "productType": product.product_type,
        "status": "DRAFT",
        "tags": list(product.tags),
        "productOptions": option_input(product),
        "files": files,
        "variants": [variant_payload(product, item, staged_files) for item in product.variants],
    }
    return clean_payload(payload)


def ensure_user_errors(errors):
    if errors:
        raise RuntimeError(str(errors))


def sync_product(client, product):
    staged_files = staged_files_map(product, client)
    variables = {
        "input": product_payload(product, staged_files),
        "synchronous": True,
    }
    result = client.execute(PRODUCT_SET, variables)["productSet"]
    ensure_user_errors(result["userErrors"])
    return result["product"]["id"]


def sync_products(client, products):
    results = []
    total = len(products)
    for index, product in enumerate(products, start=1):
        print(f"[{index}/{total}] {product.title}")
        results.append(sync_product(client, product))
    return results
