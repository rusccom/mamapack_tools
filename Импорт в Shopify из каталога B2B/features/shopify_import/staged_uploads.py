import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_IMAGE_ROOT = PROJECT_ROOT / "data" / "shopify_import" / "images"


def is_remote_source(source):
    scheme = urlparse(source).scheme.lower()
    return scheme in {"http", "https"}


def local_source_path(source):
    path = Path(source)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def source_filename(source, fallback):
    if not is_remote_source(source):
        return local_source_path(source).name or fallback
    name = Path(urlparse(source).path).name
    return name or fallback


def mime_type(filename):
    guessed = mimetypes.guess_type(filename)[0]
    return guessed or "image/jpeg"


def stage_target(client, filename, file_mime):
    query = """
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
    variables = {
        "input": [{
            "filename": filename,
            "mimeType": file_mime,
            "resource": "IMAGE",
            "httpMethod": "POST",
        }]
    }
    data = client.execute(query, variables)["stagedUploadsCreate"]
    ensure_user_errors(data["userErrors"])
    return data["stagedTargets"][0]


def ensure_user_errors(errors):
    if errors:
        raise RuntimeError(str(errors))


def download_source_bytes(source_url):
    response = requests.get(source_url, verify=False, timeout=60)
    response.raise_for_status()
    return response.content


def read_local_source_bytes(source):
    path = local_source_path(source)
    if path.exists():
        return path.read_bytes()
    message = f"Local image not found: {path}"
    hint = f" Store images in {LOCAL_IMAGE_ROOT} or pass an absolute path."
    raise FileNotFoundError(message + hint)


def source_bytes(source):
    if is_remote_source(source):
        return download_source_bytes(source)
    return read_local_source_bytes(source)


def upload_to_stage(target, filename, file_mime, content):
    payload = {item["name"]: item["value"] for item in target["parameters"]}
    files = {"file": (filename, content, file_mime)}
    response = requests.post(target["url"], data=payload, files=files, timeout=120)
    response.raise_for_status()


def staged_file_payload(source, alt, client, index):
    filename = source_filename(source, f"catalog-image-{index}.jpg")
    file_mime = mime_type(filename)
    content = source_bytes(source)
    target = stage_target(client, filename, file_mime)
    upload_to_stage(target, filename, file_mime, content)
    return {
        "filename": filename,
        "originalSource": target["resourceUrl"],
        "contentType": "IMAGE",
        "alt": alt,
        "duplicateResolutionMode": "REPLACE",
    }


def staged_files_map(product, client):
    staged = {}
    for index, (file_key, source) in enumerate(product.file_map.items(), start=1):
        staged[file_key] = staged_file_payload(source, product.title, client, index)
    return staged
