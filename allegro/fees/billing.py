from decimal import Decimal

from allegro.core.client import AllegroClient


def fetch_entries(client: AllegroClient, start: str, end: str, marketplace: str = "") -> list[dict]:
    rows = []
    offset = 0
    while True:
        batch = fetch_page(client, start, end, offset, marketplace)
        rows.extend(batch)
        if len(batch) < 100:
            return rows
        offset += len(batch)


def fetch_page(client: AllegroClient, start: str, end: str, offset: int, marketplace: str) -> list[dict]:
    data = client.get("/billing/billing-entries", params(start, end, offset, marketplace))
    return list(data.get("billingEntries", []))


def params(start: str, end: str, offset: int, marketplace: str) -> dict:
    query = {
        "occurredAt.gte": start,
        "occurredAt.lte": end,
        "limit": 100,
        "offset": offset,
    }
    if marketplace:
        query["marketplaceId"] = marketplace
    return query


def amount(entry: dict) -> Decimal:
    value = entry.get("value", {})
    return Decimal(str(value.get("amount", "0")))
