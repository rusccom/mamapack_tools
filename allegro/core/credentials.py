import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AllegroCredentials:
    client_id: str
    client_secret: str


def load_credentials(root: Path | None = None) -> AllegroCredentials:
    values = env_values()
    if not values["client_id"] or not values["client_secret"]:
        values.update(file_values((root or Path.cwd()) / "key.md"))
    if not values["client_id"] or not values["client_secret"]:
        raise RuntimeError("Missing Allegro Client ID or Client_Secret.")
    return AllegroCredentials(values["client_id"], values["client_secret"])


def env_values() -> dict[str, str]:
    return {
        "client_id": os.getenv("ALLEGRO_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("ALLEGRO_CLIENT_SECRET", "").strip(),
    }


def file_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"client_id": "", "client_secret": ""}
    text = path.read_text(encoding="utf-8")
    return {
        "client_id": match_value(text, r"Client ID"),
        "client_secret": match_value(text, r"Client_Secret"),
    }


def match_value(text: str, label: str) -> str:
    pattern = rf"(?im)^\s*{label}\s*[:=]\s*(\S+)\s*$"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""
