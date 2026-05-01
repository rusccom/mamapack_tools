from dataclasses import dataclass


@dataclass(slots=True)
class CatalogVariant:
    title: str
    vendor: str
    source_code: str
    supplier_sku: str
    barcode: str
    price: str
    detail_url: str
    image_urls: tuple[str, ...]
    main_category: str
    source_category: str


@dataclass(slots=True)
class ShopifyVariantDraft:
    option_value: str
    sku: str
    barcode: str
    price: str
    detail_url: str
    source_code: str
    source_title: str
    file_key: str
    source_sku: str


@dataclass(slots=True)
class ShopifyProductDraft:
    handle: str
    title: str
    description_html: str
    vendor: str
    product_type: str
    tags: tuple[str, ...]
    option_name: str
    option_values: tuple[str, ...]
    variants: tuple[ShopifyVariantDraft, ...]
    source_links: tuple[str, ...]
    file_map: dict[str, str]


@dataclass(slots=True)
class ShopifySyncedVariant:
    option_value: str
    sku: str
    barcode: str
    price: str
    detail_url: str
    source_code: str
    source_title: str
    source_sku: str
    shopify_id: str
    legacy_resource_id: int
    media_urls: tuple[str, ...]


@dataclass(slots=True)
class ShopifySyncedProduct:
    handle: str
    title: str
    description_html: str
    vendor: str
    product_type: str
    tags: tuple[str, ...]
    option_name: str
    option_values: tuple[str, ...]
    shopify_id: str
    legacy_resource_id: int
    status: str
    media_urls: tuple[str, ...]
    variants: tuple[ShopifySyncedVariant, ...]
