from pathlib import Path


def project_root_from(file_path: str, marker: str = "shopify_store") -> Path:
    current = Path(file_path).resolve()
    for candidate in [current.parent, *current.parents]:
        if (candidate / marker).is_dir():
            return candidate
    return current.parent


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
