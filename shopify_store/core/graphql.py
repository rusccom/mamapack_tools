from pathlib import Path

import requests

from .credentials import ShopifyAccess, load_shopify_access


class ShopifyGraphQL:
    def __init__(self, access: ShopifyAccess | str, token: str = "", version: str = ""):
        self._access = normalize_access(access, token, version)
        self._session = requests.Session()

    def execute(self, query: str, variables: dict | None = None) -> dict:
        response = self._session.post(
            self.endpoint(),
            json={"query": query, "variables": variables or {}},
            headers=self.headers(),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data["data"]

    def endpoint(self) -> str:
        store = self._access.store_domain
        version = self._access.api_version
        return f"https://{store}/admin/api/{version}/graphql.json"

    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._access.access_token,
        }


def normalize_access(access: ShopifyAccess | str, token: str, version: str) -> ShopifyAccess:
    if isinstance(access, ShopifyAccess):
        return access
    return ShopifyAccess(access, token, version or "2026-04")


def build_shopify_client(project_root: Path) -> ShopifyGraphQL:
    return ShopifyGraphQL(load_shopify_access(project_root))
