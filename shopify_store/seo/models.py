from dataclasses import dataclass


@dataclass(slots=True)
class ProductRecord:
    id: str
    legacy_id: int
    status: str
    title: str
    handle: str
    vendor: str
    product_type: str
    description: str
    seo_title: str
    seo_description: str
    online_store_url: str


@dataclass(slots=True)
class RedirectRecord:
    id: str
    path: str
    target: str


@dataclass(slots=True)
class ProductRecommendation:
    product_id: str
    legacy_id: int
    status: str
    title: str
    handle: str
    vendor: str
    product_type: str
    description: str
    current_seo_title: str
    current_seo_description: str
    online_store_url: str
    recommended_handle: str
    recommended_seo_title: str
    recommended_seo_description: str
    change_handle: bool
    handle_change_reason: str
    change_seo_title: bool
    change_seo_description: bool


@dataclass(slots=True)
class ApplyResult:
    legacy_id: int
    title: str
    old_handle: str
    new_handle: str
    seo_title_updated: bool
    seo_description_updated: bool
    handle_updated: bool
    redirect_created: bool
    success: bool
    error: str
