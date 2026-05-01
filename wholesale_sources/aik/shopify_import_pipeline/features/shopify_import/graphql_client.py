import requests


class ShopifyGraphQLClient:
    def __init__(self, credentials):
        self._credentials = credentials
        self._session = requests.Session()

    def endpoint(self):
        version = self._credentials.api_version
        store = self._credentials.store_domain
        return f"https://{store}/admin/api/{version}/graphql.json"

    def headers(self):
        return {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._credentials.access_token,
        }

    def execute(self, query, variables=None):
        payload = {"query": query, "variables": variables or {}}
        response = self._session.post(self.endpoint(), json=payload, headers=self.headers(), timeout=60)
        response.raise_for_status()
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
        return data["data"]
