from .context import BaselinkerInventoryContext


def get_inventory_context(client, settings, store_domain):
    inventory = resolve_inventory(client, settings.inventory_id)
    storage_id = resolve_storage_id(client, settings, store_domain)
    return BaselinkerInventoryContext(
        inventory_id=settings.inventory_id,
        default_language=inventory["default_language"],
        default_price_group=int(inventory.get("default_price_group") or 0),
        category_id=settings.category_id,
        shopify_storage_id=storage_id,
    )


def resolve_inventory(client, inventory_id):
    data = client.execute("getInventories", {})
    for inventory in data.get("inventories", []):
        if int(inventory["inventory_id"]) == int(inventory_id):
            return inventory
    raise RuntimeError(f"BaseLinker inventory not found: {inventory_id}")


def resolve_storage_id(client, settings, store_domain):
    if settings.shopify_storage_id:
        return settings.shopify_storage_id
    storages = external_storages(client)
    matched = matching_shopify_storages(storages, settings, store_domain)
    if len(matched) == 1:
        return str(matched[0]["storage_id"])
    raise RuntimeError(storage_hint_error(storages))


def external_storages(client):
    raw = client.execute("getExternalStoragesList", {}).get("storages", []) or []
    return list(raw.values()) if isinstance(raw, dict) else list(raw)


def matching_shopify_storages(storages, settings, store_domain):
    hint = settings.shopify_storage_name or store_domain.split(".")[0]
    return [item for item in storages if is_shopify_storage(item, hint)]


def is_shopify_storage(item, hint):
    storage_id = str(item.get("storage_id", ""))
    name = str(item.get("name", "")).lower()
    return storage_id.startswith("shop_") and hint.lower() in name


def storage_hint_error(storages):
    names = ", ".join(shop_storage_names(storages)) or "none"
    message = "Set BASELINKER_SHOPIFY_STORAGE_ID or BASELINKER_SHOPIFY_STORAGE_NAME."
    return f"{message} Available shop storages: {names}"


def shop_storage_names(storages):
    return [f"{item.get('storage_id')}:{item.get('name')}" for item in storages if is_shop_storage(item)]


def is_shop_storage(item):
    return str(item.get("storage_id", "")).startswith("shop_")
