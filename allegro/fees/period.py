from datetime import datetime, timezone


def iso_utc(value: str, end: bool = False) -> str:
    suffix = "23:59:59.999" if end else "00:00:00.000"
    date = datetime.fromisoformat(f"{value}T{suffix}+02:00")
    return date.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
