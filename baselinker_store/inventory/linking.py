def shopify_link(storage_id, product_id, variant_id=0):
    value = {"product_id": str(product_id)}
    if variant_id:
        value["variant_id"] = str(variant_id)
    return {storage_id: value}
