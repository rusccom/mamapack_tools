from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_DOMAIN = "c1e90d-4.myshopify.com"
DEFAULT_API_VERSION = "2026-04"


@dataclass(frozen=True, slots=True)
class ShopifyAccess:
    store_domain: str
    access_token: str
    api_version: str = DEFAULT_API_VERSION


def load_shopify_access(project_root: Path | None = None) -> ShopifyAccess:
    values = env_values()
    if project_root:
        values = merge_values(values, key_file_values(project_root / "key.md"))
    domain = values.get("store_domain") or DEFAULT_DOMAIN
    token = values.get("access_token") or ""
    version = values.get("api_version") or DEFAULT_API_VERSION
    if not token:
        raise RuntimeError("Missing SHOPIFY_ADMIN_TOKEN or key.md Admin API access token.")
    return ShopifyAccess(domain, token, version)


def env_values() -> dict[str, str]:
    return {
        "store_domain": os.getenv("SHOPIFY_STORE_DOMAIN", "").strip(),
        "access_token": os.getenv("SHOPIFY_ADMIN_TOKEN", "").strip(),
        "api_version": os.getenv("SHOPIFY_API_VERSION", DEFAULT_API_VERSION).strip(),
    }


def key_file_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return {
        "store_domain": text_after_label(lines, "SHOPIFY_STORE_DOMAIN"),
        "access_token": text_after_label(lines, "Admin API access token"),
    }


def merge_values(primary: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    merged = dict(primary)
    for key, value in fallback.items():
        if not merged.get(key):
            merged[key] = value
    return merged


def text_after_label(lines: list[str], label: str) -> str:
    for index, line in enumerate(lines):
        if line != label:
            continue
        return next_non_empty(lines[index + 1 :])
    return ""


def next_non_empty(lines: list[str]) -> str:
    for line in lines:
        value = line.strip()
        if value:
            return value
    return ""
