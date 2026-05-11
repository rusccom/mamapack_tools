from collections import defaultdict
from decimal import Decimal

from .billing import amount
from .classify import category
from .currency import currency_of
from .summary import round_map, type_key


def summarize_pln(entries: list[dict], rates: dict) -> dict:
    totals = defaultdict(Decimal)
    by_type = defaultdict(Decimal)
    by_currency = defaultdict(Decimal)
    for entry in entries:
        value = amount(entry)
        if value >= 0:
            continue
        converted = -value * rate_value(rates, currency_of(entry))
        totals[category(entry)] += converted
        by_type[type_key(entry)] += converted
        by_currency[currency_of(entry)] += converted
    totals["all"] = sum(totals.values(), Decimal("0"))
    return pln_report(totals, by_type, by_currency)


def rate_value(rates: dict, currency: str) -> Decimal:
    return Decimal(str(rates[currency]["rate"]))


def pln_report(totals: dict, by_type: dict, by_currency: dict) -> dict:
    return {
        "totals": round_map(totals),
        "by_type": round_map(by_type),
        "by_currency": round_map(by_currency),
    }
