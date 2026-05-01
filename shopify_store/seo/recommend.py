from .description_rules import build_seo_description
from .handle_rules import choose_handle
from .models import ProductRecommendation, ProductRecord
from .title_rules import build_base_title, build_seo_title


def build_recommendations(products: list[ProductRecord]) -> list[ProductRecommendation]:
    used_handles = set()
    results: list[ProductRecommendation] = []
    for product in products:
        base_title = build_base_title(product)
        handle, reason = choose_handle(products, product, base_title, used_handles)
        seo_title = build_seo_title(base_title)
        seo_description = build_seo_description(base_title, product.description)
        results.append(new_recommendation(product, handle, reason, seo_title, seo_description))
    return results


def new_recommendation(
    product: ProductRecord,
    handle: str,
    reason: str,
    seo_title: str,
    seo_description: str,
) -> ProductRecommendation:
    fields = product_fields(product)
    fields.update(recommendation_fields(product, handle, reason, seo_title, seo_description))
    return ProductRecommendation(**fields)


def product_fields(product: ProductRecord) -> dict:
    return dict(
        product_id=product.id,
        legacy_id=product.legacy_id,
        status=product.status,
        title=product.title,
        handle=product.handle,
        vendor=product.vendor,
        product_type=product.product_type,
        description=product.description,
        current_seo_title=product.seo_title,
        current_seo_description=product.seo_description,
        online_store_url=product.online_store_url,
    )


def recommendation_fields(
    product: ProductRecord,
    handle: str,
    reason: str,
    seo_title: str,
    seo_description: str,
) -> dict:
    return dict(
        recommended_handle=handle,
        recommended_seo_title=seo_title,
        recommended_seo_description=seo_description,
        change_handle=bool(reason),
        handle_change_reason=reason,
        change_seo_title=seo_title != product.seo_title,
        change_seo_description=seo_description != product.seo_description,
    )
