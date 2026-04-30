import csv
import json
from dataclasses import asdict
from pathlib import Path


def write_backup_csv(target: Path, rows: list[dict]) -> None:
    if not rows:
        target.write_text("", encoding="utf-8")
        return
    with target.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_backup_json(target: Path, payload: dict) -> None:
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def dataclass_rows(items: list) -> list[dict]:
    return [asdict(item) for item in items]
