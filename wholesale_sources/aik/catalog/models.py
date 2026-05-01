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
