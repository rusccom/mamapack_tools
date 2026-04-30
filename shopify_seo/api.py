from pathlib import Path

import requests

from .models import ProductRecord, RedirectRecord


PRODUCTS_QUERY = """
query ProductsPage($first: Int!, $after: String) {
  products(first: $first, after: $after, sortKey: ID) {
    nodes {
      id
      legacyResourceId
      status
      title
      handle
      vendor
      productType
      description(truncateAt: 6000)
      seo { title description }
      onlineStoreUrl
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

REDIRECTS_QUERY = """
query RedirectsPage($first: Int!, $after: String) {
  urlRedirects(first: $first, after: $after) {
    nodes {
      id
      path
      target
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

PRODUCT_UPDATE_MUTATION = """
mutation UpdateProduct($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      legacyResourceId
      title
      handle
      seo {
        title
        description
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

REDIRECT_CREATE_MUTATION = """
mutation CreateRedirect($urlRedirect: UrlRedirectInput!) {
  urlRedirectCreate(urlRedirect: $urlRedirect) {
    urlRedirect {
      id
      path
      target
    }
    userErrors {
      field
      message
    }
  }
}
"""


class ShopifyGraphQL:
    def __init__(self, store_domain: str, access_token: str, api_version: str):
        self._store_domain = store_domain
        self._access_token = access_token
        self._api_version = api_version
        self._session = requests.Session()

    def execute(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        response = self._session.post(
            self.endpoint(),
            json=payload,
            headers=self.headers(),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data["data"]

    def endpoint(self) -> str:
        return f"https://{self._store_domain}/admin/api/{self._api_version}/graphql.json"

    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._access_token,
        }


def load_shopify_access(project_root: Path) -> tuple[str, str, str]:
    key_path = project_root / "key.md"
    lines = [line.strip() for line in key_path.read_text(encoding="utf-8").splitlines()]
    token = text_after_label(lines, "Admin API access token")
    domain = text_after_label(lines, "SHOPIFY_STORE_DOMAIN")
    if not domain:
        domain = "c1e90d-4.myshopify.com"
    return domain, token, "2026-04"


def text_after_label(lines: list[str], label: str) -> str:
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line != label:
            continue
        for next_line in lines[index + 1 :]:
            value = next_line.strip()
            if value:
                return value
    return ""


def fetch_all_products(client: ShopifyGraphQL) -> list[ProductRecord]:
    items: list[ProductRecord] = []
    cursor = None
    while True:
        data = client.execute(PRODUCTS_QUERY, {"first": 100, "after": cursor})["products"]
        items.extend(build_records(data["nodes"]))
        if not data["pageInfo"]["hasNextPage"]:
            return items
        cursor = data["pageInfo"]["endCursor"]


def fetch_all_redirects(client: ShopifyGraphQL) -> list[RedirectRecord]:
    items: list[RedirectRecord] = []
    cursor = None
    while True:
        data = client.execute(REDIRECTS_QUERY, {"first": 100, "after": cursor})["urlRedirects"]
        items.extend(build_redirects(data["nodes"]))
        if not data["pageInfo"]["hasNextPage"]:
            return items
        cursor = data["pageInfo"]["endCursor"]


def update_product(
    client: ShopifyGraphQL,
    product_id: str,
    handle: str,
    seo_title: str,
    seo_description: str,
) -> dict:
    payload = {
        "id": product_id,
        "handle": handle,
        "seo": {"title": seo_title, "description": seo_description},
    }
    return client.execute(PRODUCT_UPDATE_MUTATION, {"product": payload})["productUpdate"]


def create_redirect(client: ShopifyGraphQL, path: str, target: str) -> dict:
    payload = {"path": path, "target": target}
    return client.execute(REDIRECT_CREATE_MUTATION, {"urlRedirect": payload})["urlRedirectCreate"]


def build_records(nodes: list[dict]) -> list[ProductRecord]:
    records: list[ProductRecord] = []
    for node in nodes:
        seo = node.get("seo") or {}
        records.append(
            ProductRecord(
                id=node["id"],
                legacy_id=int(node["legacyResourceId"]),
                status=node["status"],
                title=node["title"].strip(),
                handle=node["handle"].strip(),
                vendor=(node.get("vendor") or "").strip(),
                product_type=(node.get("productType") or "").strip(),
                description=(node.get("description") or "").strip(),
                seo_title=(seo.get("title") or "").strip(),
                seo_description=(seo.get("description") or "").strip(),
                online_store_url=(node.get("onlineStoreUrl") or "").strip(),
            )
        )
    return records


def build_redirects(nodes: list[dict]) -> list[RedirectRecord]:
    records: list[RedirectRecord] = []
    for node in nodes:
        records.append(
            RedirectRecord(
                id=node["id"],
                path=(node.get("path") or "").strip(),
                target=(node.get("target") or "").strip(),
            )
        )
    return records
