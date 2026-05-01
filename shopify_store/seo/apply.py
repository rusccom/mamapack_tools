from .api import create_redirect, update_product
from .models import ApplyResult, ProductRecommendation, ProductRecord, RedirectRecord


def build_product_index(products: list[ProductRecord]) -> dict[int, ProductRecord]:
    return {item.legacy_id: item for item in products}


def build_handle_index(products: list[ProductRecord]) -> dict[str, ProductRecord]:
    return {item.handle: item for item in products}


def build_redirect_index(redirects: list[RedirectRecord]) -> dict[str, RedirectRecord]:
    return {item.path: item for item in redirects}


def validate_plan(
    recommendations: list[ProductRecommendation],
    products: list[ProductRecord],
    redirects: list[RedirectRecord],
) -> list[str]:
    errors = []
    errors.extend(find_recommended_duplicates(recommendations))
    errors.extend(find_handle_conflicts(recommendations, build_handle_index(products)))
    errors.extend(find_redirect_conflicts(recommendations, build_redirect_index(redirects)))
    return errors


def find_recommended_duplicates(recommendations: list[ProductRecommendation]) -> list[str]:
    seen: dict[str, int] = {}
    errors = []
    for item in recommendations:
        if not item.change_handle:
            continue
        if item.recommended_handle in seen:
            errors.append(f"Duplicate recommended handle: {item.recommended_handle}")
            continue
        seen[item.recommended_handle] = item.legacy_id
    return errors


def find_handle_conflicts(
    recommendations: list[ProductRecommendation],
    handle_index: dict[str, ProductRecord],
) -> list[str]:
    errors = []
    for item in recommendations:
        if not item.change_handle:
            continue
        conflict = handle_index.get(item.recommended_handle)
        if conflict and conflict.legacy_id != item.legacy_id:
            errors.append(f"Handle exists on product {conflict.legacy_id}: {item.recommended_handle}")
    return errors


def find_redirect_conflicts(
    recommendations: list[ProductRecommendation],
    redirect_index: dict[str, RedirectRecord],
) -> list[str]:
    errors = []
    for item in recommendations:
        if not item.change_handle:
            continue
        errors.extend(check_redirect_path(item, redirect_index, item.handle))
        errors.extend(check_redirect_path(item, redirect_index, item.recommended_handle))
    return errors


def check_redirect_path(
    item: ProductRecommendation,
    redirect_index: dict[str, RedirectRecord],
    handle: str,
) -> list[str]:
    path = f"/products/{handle}"
    redirect = redirect_index.get(path)
    if not redirect:
        return []
    return [f"Redirect path exists for {item.legacy_id}: {path} -> {redirect.target}"]


def ordered_recommendations(items: list[ProductRecommendation]) -> list[ProductRecommendation]:
    return sorted(items, key=lambda item: (not item.change_handle, item.legacy_id))


def apply_recommendations(
    client,
    products: list[ProductRecord],
    recommendations: list[ProductRecommendation],
) -> list[ApplyResult]:
    product_index = build_product_index(products)
    results = []
    for item in ordered_recommendations(recommendations):
        results.append(apply_single(client, product_index[item.legacy_id], item))
    return results


def apply_single(client, product: ProductRecord, item: ProductRecommendation) -> ApplyResult:
    old_path = f"/products/{product.handle}"
    new_path = f"/products/{item.recommended_handle}"
    try:
        update_recommendation(client, product, item)
        redirect_created = create_redirect_if_needed(client, item, old_path, new_path)
        return success_result(product, item, redirect_created)
    except Exception as exc:
        return error_result(product, item, exc)


def update_recommendation(client, product: ProductRecord, item: ProductRecommendation) -> None:
    handle = item.recommended_handle if item.change_handle else product.handle
    payload = update_product(
        client,
        item.product_id,
        handle,
        item.recommended_seo_title,
        item.recommended_seo_description,
    )
    raise_for_user_errors(payload["userErrors"])


def success_result(product: ProductRecord, item: ProductRecommendation, redirect_created: bool) -> ApplyResult:
    fields = result_fields(product, item)
    fields.update(
        seo_title_updated=item.change_seo_title,
        seo_description_updated=item.change_seo_description,
        handle_updated=item.change_handle,
        redirect_created=redirect_created,
        success=True,
        error="",
    )
    return ApplyResult(**fields)


def error_result(product: ProductRecord, item: ProductRecommendation, exc: Exception) -> ApplyResult:
    fields = result_fields(product, item)
    fields.update(
        seo_title_updated=False,
        seo_description_updated=False,
        handle_updated=False,
        redirect_created=False,
        success=False,
        error=str(exc),
    )
    return ApplyResult(**fields)


def result_fields(product: ProductRecord, item: ProductRecommendation) -> dict:
    return dict(
        legacy_id=item.legacy_id,
        title=item.title,
        old_handle=product.handle,
        new_handle=item.recommended_handle,
    )


def create_redirect_if_needed(client, item: ProductRecommendation, old_path: str, new_path: str) -> bool:
    if not item.change_handle:
        return False
    payload = create_redirect(client, old_path, new_path)
    raise_for_user_errors(payload["userErrors"])
    return True


def raise_for_user_errors(errors: list[dict]) -> None:
    if not errors:
        return
    messages = [build_error_text(item) for item in errors]
    raise RuntimeError("; ".join(messages))


def build_error_text(error: dict) -> str:
    field = ".".join(error.get("field") or [])
    message = error.get("message") or "Unknown user error"
    return f"{field}: {message}".strip(": ")
