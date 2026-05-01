from pathlib import Path

from shopify_store.core.credentials import load_shopify_access as load_access
from shopify_store.core.graphql import ShopifyGraphQL
from shopify_store.products.seo import update_product_seo

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


def load_shopify_access(project_root: Path) -> tuple[str, str, str]:
    access = load_access(project_root)
    return access.store_domain, access.access_token, access.api_version


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
    product = update_product_seo(client, product_id, handle, seo_title, seo_description)
    return {"product": product, "userErrors": []}


def create_redirect(client: ShopifyGraphQL, path: str, target: str) -> dict:
    payload = {"path": path, "target": target}
    data = client.execute(REDIRECT_CREATE_MUTATION, {"urlRedirect": payload})
    return data["urlRedirectCreate"]


def build_records(nodes: list[dict]) -> list[ProductRecord]:
    records: list[ProductRecord] = []
    for node in nodes:
        records.append(build_record(node))
    return records


def build_record(node: dict) -> ProductRecord:
    seo = node.get("seo") or {}
    return ProductRecord(
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


def build_redirects(nodes: list[dict]) -> list[RedirectRecord]:
    records: list[RedirectRecord] = []
    for node in nodes:
        records.append(build_redirect(node))
    return records


def build_redirect(node: dict) -> RedirectRecord:
    return RedirectRecord(
        id=node["id"],
        path=(node.get("path") or "").strip(),
        target=(node.get("target") or "").strip(),
    )
