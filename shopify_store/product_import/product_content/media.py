import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests


IMAGE_DIR = Path("shopify_store") / "product_import" / "data" / "product_content"
IMAGE_URLS = (
    "https://us.bibsworld.com/cdn/shop/files/bibs-colour-pacifier-blush_8f2f91d0-2e81-4d08-a0cb-10545b64fba9_grande.png?v=1733321868",
    "https://us.bibsworld.com/cdn/shop/files/211244_5713795240197_BIBS_COLOUR_Ana_Latex_S2_Blush_1_1000x1000_98421d57-41f8-4673-a6c6-14b8d5e2bf9e_grande.png?v=1693208682",
)

STAGED_UPLOADS_MUTATION = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters { name value }
    }
    userErrors { field message }
  }
}
"""


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
        media.append(stage_single_media(client, file_path, alt))
    return media


def image_alt(title: str, index: int) -> str:
    labels = {
        1: "glowne zdjecie produktu",
        2: "detal smoczka anatomicznego",
    }
    suffix = labels.get(index, f"zdjecie {index}")
    return f"{title} - {suffix}"


def stage_single_media(client, file_path: Path, alt: str) -> dict:
    content = file_path.read_bytes()
    filename = file_path.name
    file_mime = guess_mime(filename)
    target = staged_target(client, filename, file_mime)
    upload_to_stage(target, filename, file_mime, content)
    return {"originalSource": target["resourceUrl"], "alt": alt, "mediaContentType": "IMAGE"}


def guess_mime(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "image/png"


def staged_target(client, filename: str, file_mime: str) -> dict:
    variables = {
        "input": [{
            "filename": filename,
            "mimeType": file_mime,
            "resource": "IMAGE",
            "httpMethod": "POST",
        }]
    }
    result = client.execute(STAGED_UPLOADS_MUTATION, variables)["stagedUploadsCreate"]
    raise_for_errors(result["userErrors"])
    return result["stagedTargets"][0]


def upload_to_stage(target: dict, filename: str, file_mime: str, content: bytes) -> None:
    payload = {item["name"]: item["value"] for item in target["parameters"]}
    files = {"file": (filename, content, file_mime)}
    response = requests.post(target["url"], data=payload, files=files, timeout=120)
    response.raise_for_status()


def raise_for_errors(errors: list[dict]) -> None:
    if not errors:
        return
    messages = [error_text(item) for item in errors]
    raise RuntimeError("; ".join(messages))


def error_text(error: dict) -> str:
    field = ".".join(error.get("field") or [])
    message = error.get("message") or "Unknown Shopify error"
    return f"{field}: {message}".strip(": ")
