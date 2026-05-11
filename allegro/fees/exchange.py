from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache

import requests


NBP_URL = "https://api.nbp.pl/api/exchangerates/rates/a"


def rates_to_pln(currencies: list[str], end_date: str) -> dict:
    return {currency: rate_to_pln(currency, end_date) for currency in currencies}


@lru_cache(maxsize=64)
def rate_to_pln(currency: str, end_date: str) -> dict:
    if currency == "PLN":
        return fixed_pln_rate(end_date)
    body = fetch_nbp(currency, start_date(end_date), end_date)
    rates = body.get("rates", [])
    if not rates:
        raise RuntimeError(f"No NBP rate for {currency} up to {end_date}")
    return rate_from_nbp(currency, rates[-1])


def fixed_pln_rate(end_date: str) -> dict:
    return {"currency": "PLN", "rate": "1", "effective_date": end_date, "source": "PLN"}


def fetch_nbp(currency: str, start: str, end: str) -> dict:
    url = f"{NBP_URL}/{currency}/{start}/{end}/"
    response = requests.get(url, params={"format": "json"}, timeout=30)
    response.raise_for_status()
    return response.json()


def start_date(end_date: str) -> str:
    value = date.fromisoformat(end_date) - timedelta(days=14)
    return value.isoformat()


def rate_from_nbp(currency: str, row: dict) -> dict:
    rate = Decimal(str(row["mid"]))
    return {
        "currency": currency,
        "rate": str(rate),
        "effective_date": row["effectiveDate"],
        "source": "NBP table A",
    }
