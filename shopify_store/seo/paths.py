from pathlib import Path


def project_root_from(file_path: str) -> Path:
    current = Path(file_path).resolve()
    for candidate in [current.parent, *current.parents]:
        if (candidate / "shopify_store").is_dir():
            return candidate
    return current.parent


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def mamapack_report_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "store_reports" / "mamapack_seo" / stamp)


def shopify_recommendations_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "recommendations" / stamp)


def shopify_backup_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "backups" / stamp)


def shopify_apply_dir(root: Path, stamp: str) -> Path:
    return ensure_dir(root / "shopify_store" / "seo" / "reports" / "apply" / stamp)
