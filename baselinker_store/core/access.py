from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BaselinkerAccess:
    token: str
    inventory_id: int
    shopify_storage_id: str
    shopify_storage_name: str
    category_id: int
