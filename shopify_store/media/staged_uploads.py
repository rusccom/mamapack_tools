import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests

from shopify_store.core.user_errors import raise_for_user_errors


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


def create_media_input(client, source: str | Path, alt: str, fallback: str) -> dict:
    target = stage_image_upload(client, source, fallback)
    return {"originalSource": target["resourceUrl"], "alt": alt, "mediaContentType": "IMAGE"}


def product_set_file_input(client, source: str | Path, alt: str, fallback: str) -> dict:
    target = stage_image_upload(client, source, fallback)
    return {
        "filename": target["filename"],
        "originalSource": target["resourceUrl"],
        "contentType": "IMAGE",
        "alt": alt,
        "duplicateResolutionMode": "REPLACE",
    }


def staged_files_map(product, client) -> dict:
    staged = {}
    for index, (file_key, source) in enumerate(product.file_map.items(), start=1):
        fallback = f"catalog-image-{index}.jpg"
        staged[file_key] = product_set_file_input(client, source, product.title, fallback)
    return staged


def stage_image_upload(client, source: str | Path, fallback: str) -> dict:
    filename = source_filename(source, fallback)
    file_mime = mime_type(filename)
    target = stage_target(client, filename, file_mime)
    upload_to_stage(target, filename, file_mime, source_bytes(source))
    return {"filename": filename, "resourceUrl": target["resourceUrl"]}


def stage_target(client, filename: str, file_mime: str) -> dict:
    variables = {"input": [stage_input(filename, file_mime)]}
    data = client.execute(STAGED_UPLOADS_MUTATION, variables)["stagedUploadsCreate"]
    raise_for_user_errors(data["userErrors"])
    return data["stagedTargets"][0]


def stage_input(filename: str, file_mime: str) -> dict:
    return {
        "filename": filename,
        "mimeType": file_mime,
        "resource": "IMAGE",
        "httpMethod": "POST",
    }


def upload_to_stage(target: dict, filename: str, file_mime: str, content: bytes) -> None:
    payload = {item["name"]: item["value"] for item in target["parameters"]}
    files = {"file": (filename, content, file_mime)}
    response = requests.post(target["url"], data=payload, files=files, timeout=120)
    response.raise_for_status()


def source_bytes(source: str | Path) -> bytes:
    if is_remote_source(source):
        return download_source_bytes(str(source))
    return local_source_path(source).read_bytes()


def download_source_bytes(source_url: str) -> bytes:
    response = requests.get(source_url, verify=False, timeout=60)
    response.raise_for_status()
    return response.content


def local_source_path(source: str | Path) -> Path:
    path = Path(source)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def source_filename(source: str | Path, fallback: str) -> str:
    if not is_remote_source(source):
        return local_source_path(source).name or fallback
    name = Path(urlparse(str(source)).path).name
    return name or fallback


def is_remote_source(source: str | Path) -> bool:
    return urlparse(str(source)).scheme.lower() in {"http", "https"}


def mime_type(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "image/jpeg"
