from .linking import shopify_link


def main_payload(context, product, product_id=""):
    payload = {
        "inventory_id": context.inventory_id,
        "product_id": product_id,
        "text_fields": text_fields(product.title, product.description_html),
        "tags": [item for item in product.tags if item],
        "images": product_images(effective_media_urls(product)),
        "links": main_link(context, product),
    }
    payload.update(main_category(context))
    payload.update(single_variant_fields(context, product))
    return clean_payload(payload)


def variant_payload(context, parent_id, product, variant, product_id=""):
    payload = {
        "inventory_id": context.inventory_id,
        "product_id": product_id,
        "parent_id": parent_id,
        "sku": variant.sku,
        "ean": variant.barcode,
        "prices": prices_map(context, variant.price),
        "text_fields": text_fields(variant_name(product, variant), product.description_html),
        "links": shopify_link(context.shopify_storage_id, product.legacy_resource_id, variant.legacy_resource_id),
    }
    return clean_payload(payload)


def main_link(context, product):
    variant_id = product.variants[0].legacy_resource_id if len(product.variants) == 1 else 0
    return shopify_link(context.shopify_storage_id, product.legacy_resource_id, variant_id)


def main_category(context):
    return {"category_id": context.category_id} if context.category_id else {}


def single_variant_fields(context, product):
    if len(product.variants) != 1:
        return {}
    variant = product.variants[0]
    return {
        "sku": variant.sku,
        "ean": variant.barcode,
        "prices": prices_map(context, variant.price),
    }


def product_images(urls):
    return {str(index): f"url:{url}" for index, url in enumerate(urls[:16])}


def text_fields(name, description):
    return {
        "name": name,
        "description": description,
    }


def prices_map(context, price):
    if not context.default_price_group or not price:
        return {}
    return {str(context.default_price_group): float(price)}


def variant_name(product, variant):
    if product.option_name == "Title":
        return product.title
    return variant.option_value


def effective_media_urls(product):
    if product.media_urls:
        return product.media_urls
    urls = []
    for variant in product.variants:
        urls.extend(variant.media_urls)
    return tuple(dict.fromkeys(urls))


def clean_payload(value):
    return {key: item for key, item in value.items() if item not in ("", None, [], {})}
