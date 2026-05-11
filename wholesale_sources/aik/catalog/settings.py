import os
from pathlib import Path
from urllib.parse import quote


PROJECT_ROOT = Path(__file__).resolve().parents[3]
KEY_VALUES = {}


def key_file_values(path):
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = split_key_value(line)
        if key:
            values[key] = value
    return values


def split_key_value(line):
    if "=" not in line:
        return "", ""
    key, value = line.split("=", 1)
    return key.strip(), value.strip().strip('"').strip("'")


def config_value(name, default=""):
    return os.getenv(name, "").strip() or KEY_VALUES.get(name, default).strip()


def required_config(name):
    value = config_value(name)
    if value:
        return value
    raise RuntimeError(f"Missing required config value: {name}")


def image_auth_base():
    user = quote(DETAIL_AUTH[0], safe="")
    password = quote(DETAIL_AUTH[1], safe="")
    return BASE_URL.replace("https://", f"https://{user}:{password}@")


KEY_VALUES = key_file_values(PROJECT_ROOT / "key.md")
BASE_URL = config_value("AICO_BASE_URL", "https://e.aico.com.pl/")
SEARCH_PATH = config_value("AICO_SEARCH_PATH", "ProduktyWyszukiwanie.aspx")
DETAIL_AUTH = (
    required_config("AICO_DETAIL_AUTH_USER"),
    required_config("AICO_DETAIL_AUTH_PASSWORD"),
)
FORM_LOGIN = required_config("AICO_FORM_LOGIN")
FORM_PASSWORD = required_config("AICO_FORM_PASSWORD")
IMAGE_AUTH_BASE = image_auth_base()
