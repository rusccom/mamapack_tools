from dataclasses import replace

from shopify_store.products.identity import make_unique_handle, make_unique_sku


def assign_unique_identities(client, products):
    used_handles = set()
    used_skus = set()
    result = []
    for product in products:
        handle = make_unique_handle(client, product.handle, used_handles)
        result.append(replace(product, handle=handle, variants=unique_variants(client, product, used_skus)))
    return result


def unique_variants(client, product, used_skus):
    variants = []
    for variant in product.variants:
        sku = make_unique_sku(client, variant.sku, used_skus)
        variants.append(replace(variant, sku=sku))
    return tuple(variants)
