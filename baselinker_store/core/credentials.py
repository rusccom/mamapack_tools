import os
from pathlib import Path

from .access import BaselinkerAccess


KEY_LABELS = {
    "token": ("BASELINKER_TOKEN", "BaseLinker API token", "BaseLinker token"),
    "inventory_id": ("BASELINKER_INVENTORY_ID", "BaseLinker inventory ID"),
    "shopify_storage_id": ("BASELINKER_SHOPIFY_STORAGE_ID", "BaseLinker Shopify storage ID"),
    "shopify_storage_name": ("BASELINKER_SHOPIFY_STORAGE_NAME", "BaseLinker Shopify storage name"),
    "category_id": ("BASELINKER_CATEGORY_ID", "BaseLinker category ID"),
}


def load_baselinker_credentials(project_root: Path | None = None):
    values = env_values()
    if project_root:
        values = merge_values(values, key_file_values(project_root / "key.md"))
    if not values.get("token") or not values.get("inventory_id"):
        return None
    return BaselinkerAccess(
        token=values["token"],
        inventory_id=int(values["inventory_id"]),
        shopify_storage_id=values.get("shopify_storage_id", ""),
        shopify_storage_name=values.get("shopify_storage_name", ""),
        category_id=optional_int(values.get("category_id", "")),
    )


def env_values():
    return {
        "token": os.getenv("BASELINKER_TOKEN", "").strip(),
        "inventory_id": os.getenv("BASELINKER_INVENTORY_ID", "").strip(),
        "shopify_storage_id": os.getenv("BASELINKER_SHOPIFY_STORAGE_ID", "").strip(),
        "shopify_storage_name": os.getenv("BASELINKER_SHOPIFY_STORAGE_NAME", "").strip(),
        "category_id": os.getenv("BASELINKER_CATEGORY_ID", "").strip(),
    }


def key_file_values(path: Path):
    if not path.exists():
        return {}
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    values = inline_values(lines)
    for key, labels in KEY_LABELS.items():
        if not values.get(key):
            values[key] = text_after_labels(lines, labels)
    return values


def inline_values(lines):
    values = {}
    for line in lines:
        key, value = split_inline_value(line)
        if key in KEY_LABELS:
            values[key] = value
    return values


def split_inline_value(line):
    if "=" not in line:
        return "", ""
    key, value = line.split("=", 1)
    normalized = key.strip().lower().removeprefix("baselinker_")
    return normalized, value.strip()


def text_after_labels(lines, labels):
    for label in labels:
        value = text_after_label(lines, label)
        if value:
            return value
    return ""


def text_after_label(lines, label):
    for index, line in enumerate(lines):
        if line != label:
            continue
        return next_non_empty(lines[index + 1 :])
    return ""


def next_non_empty(lines):
    for line in lines:
        value = line.strip()
        if value:
            return value
    return ""


def merge_values(primary, fallback):
    merged = dict(primary)
    for key, value in fallback.items():
        if not merged.get(key):
            merged[key] = value
    return merged


def optional_int(value):
    return int(value) if str(value).strip() else 0
