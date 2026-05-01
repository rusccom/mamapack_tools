from pathlib import Path
from urllib.parse import urlparse

import requests

from shopify_store.media.staged_uploads import create_media_input


IMAGE_DIR = Path("shopify_store") / "product_import" / "data" / "product_content"
IMAGE_URLS = (
    "https://us.bibsworld.com/cdn/shop/files/bibs-colour-pacifier-blush_8f2f91d0-2e81-4d08-a0cb-10545b64fba9_grande.png?v=1733321868",
    "https://us.bibsworld.com/cdn/shop/files/211244_5713795240197_BIBS_COLOUR_Ana_Latex_S2_Blush_1_1000x1000_98421d57-41f8-4673-a6c6-14b8d5e2bf9e_grande.png?v=1693208682",
)


def download_images(root: Path, article: str) -> list[Path]:
    target_dir = (root / IMAGE_DIR / article).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for index, source_url in enumerate(IMAGE_URLS, start=1):
        files.append(download_image(source_url, target_dir, article, index))
    return files


def download_image(source_url: str, target_dir: Path, article: str, index: int) -> Path:
    target = target_dir / local_name(source_url, article, index)
    if target.exists():
        return target
    response = requests.get(source_url, timeout=60)
    response.raise_for_status()
    target.write_bytes(response.content)
    return target


def local_name(source_url: str, article: str, index: int) -> str:
    suffix = Path(urlparse(source_url).path).suffix or ".png"
    return f"{article}-{index}{suffix}"


def stage_media(client, local_files: list[Path], title: str) -> list[dict]:
    media = []
    for index, file_path in enumerate(local_files, start=1):
        alt = image_alt(title, index)
        media.append(create_media_input(client, file_path, alt, file_path.name))
    return media


def image_alt(title: str, index: int) -> str:
    labels = {
        1: "glowne zdjecie produktu",
        2: "detal smoczka anatomicznego",
    }
    suffix = labels.get(index, f"zdjecie {index}")
    return f"{title} - {suffix}"
