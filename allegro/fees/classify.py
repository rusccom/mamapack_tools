ADS_IDS = {"NSP"}
PROMO_IDS = {"ALP", "DPG", "FHB", "PUK"}


def category(entry: dict) -> str:
    type_id = type_id_of(entry)
    description = type_name_of(entry).lower()
    if type_id in ADS_IDS:
        return "ads"
    if is_delivery(type_id, description):
        return "delivery"
    if type_id in PROMO_IDS or is_promo(description):
        return "promo"
    return "other"


def is_delivery(type_id: str, description: str) -> bool:
    if type_id.startswith(("D", "H", "I", "O", "P", "U", "W", "X")):
        return "dostaw" in description or "przesy" in description
    return "dostaw" in description or "delivery" in description


def is_promo(description: str) -> bool:
    words = ["prom", "wyróż", "pakiet promo", "stronie działu"]
    return any(word in description for word in words)


def type_id_of(entry: dict) -> str:
    return str(entry.get("type", {}).get("id", ""))


def type_name_of(entry: dict) -> str:
    return str(entry.get("type", {}).get("name", ""))
