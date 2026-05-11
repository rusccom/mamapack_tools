def currency_of(entry: dict) -> str:
    return str(entry.get("value", {}).get("currency", "")).strip()


def currencies(entries: list[dict]) -> list[str]:
    return sorted({currency_of(entry) for entry in entries if currency_of(entry)})
