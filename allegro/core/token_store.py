import json
from pathlib import Path


TOKEN_PATH = Path("data/allegro_token.json")


def load_token(path: Path = TOKEN_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_token(token: dict, path: Path = TOKEN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token, indent=2), encoding="utf-8")
