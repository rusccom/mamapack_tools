import os
from dataclasses import dataclass


@dataclass(slots=True)
class ShopifyCredentials:
    store_domain: str
    access_token: str
    api_version: str = "2026-04"


def load_shopify_credentials():
    domain = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
    token = os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip()
    version = os.getenv("SHOPIFY_API_VERSION", "2026-04").strip()
    if not domain or not token:
        return None
    return ShopifyCredentials(store_domain=domain, access_token=token, api_version=version)
