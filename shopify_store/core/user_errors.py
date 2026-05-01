def raise_for_user_errors(errors: list[dict] | None) -> None:
    if not errors:
        return
    messages = [user_error_text(item) for item in errors]
    raise RuntimeError("; ".join(messages))


def user_error_text(error: dict) -> str:
    field = ".".join(error.get("field") or [])
    message = error.get("message") or "Unknown Shopify user error"
    return f"{field}: {message}".strip(": ")
