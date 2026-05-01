from .descriptions import build_description
from .grouping import build_product_stub, grouped_variants, ordered_variants, product_type
from .models import ShopifyProductDraft


def build_shopify_products(variants):
    products = []
    for group_key, group in sorted(grouped_variants(variants).items()):
        products.append(build_shopify_product(group_key, group))
    return products


def build_shopify_product(group_key, group):
    ordered = ordered_variants(group)
    handle, title, tags, option_name, option_values, draft_variants, links, file_map = build_product_stub(group_key, ordered)
    sample = ordered[0][1]
    description = build_description(title, sample.vendor, option_name, option_values, draft_variants, links)
    return ShopifyProductDraft(
        handle=handle,
        title=title,
        description_html=description,
        vendor=sample.vendor,
        product_type=product_type(sample),
        tags=tags,
        option_name=option_name,
        option_values=option_values,
        variants=draft_variants,
        source_links=links,
        file_map=file_map,
    )
