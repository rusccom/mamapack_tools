from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

from .billing import amount
from .classify import category, type_id_of, type_name_of


def summarize(entries: list[dict]) -> dict:
    totals = defaultdict(Decimal)
    by_type = defaultdict(Decimal)
    counts = Counter()
    for entry in entries:
        value = amount(entry)
        if value >= 0:
            continue
        key = category(entry)
        totals[key] += -value
        by_type[type_key(entry)] += -value
        counts[key] += 1
    totals["all"] = sum(totals.values(), Decimal("0"))
    return {"totals": round_map(totals), "by_type": round_map(by_type), "counts": dict(counts)}


def type_key(entry: dict) -> str:
    return f"{type_id_of(entry)} {type_name_of(entry)}".strip()


def round_map(values: dict) -> dict[str, str]:
    return {key: str(round_money(value)) for key, value in sorted(values.items())}


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), ROUND_HALF_UP)
