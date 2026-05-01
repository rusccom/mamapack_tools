from pathlib import Path

from shopify_store.core.paths import ensure_dir, project_root_from


def mamapack_report_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "store_reports" / "mamapack_seo" / stamp)


def shopify_recommendations_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "recommendations" / stamp)


def shopify_backup_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "backups" / stamp)


def shopify_apply_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "apply" / stamp)
