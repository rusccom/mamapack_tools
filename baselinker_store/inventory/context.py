from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaselinkerInventoryContext:
    inventory_id: int
    default_language: str
    default_price_group: int
    category_id: int
    shopify_storage_id: str
