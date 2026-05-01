import os
from dataclasses import dataclass


@dataclass(slots=True)
class BaselinkerCredentials:
    token: str
    inventory_id: int
    shopify_storage_id: str
    shopify_storage_name: str
    category_id: int


@dataclass(slots=True)
class BaselinkerInventoryContext:
    inventory_id: int
    default_language: str
    default_price_group: int
    category_id: int
    shopify_storage_id: str


def load_baselinker_credentials():
    token = os.getenv("BASELINKER_TOKEN", "").strip()
    inventory = os.getenv("BASELINKER_INVENTORY_ID", "").strip()
    storage_id = os.getenv("BASELINKER_SHOPIFY_STORAGE_ID", "").strip()
    storage_name = os.getenv("BASELINKER_SHOPIFY_STORAGE_NAME", "").strip()
    category = os.getenv("BASELINKER_CATEGORY_ID", "").strip()
    if not token or not inventory:
        return None
    category_id = int(category) if category else 0
    return BaselinkerCredentials(
        token=token,
        inventory_id=int(inventory),
        shopify_storage_id=storage_id,
        shopify_storage_name=storage_name,
        category_id=category_id,
    )
