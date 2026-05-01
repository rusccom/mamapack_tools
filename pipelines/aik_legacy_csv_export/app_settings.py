BASE_URL = "https://e.aico.com.pl/"
SEARCH_PATH = "ProduktyWyszukiwanie.aspx"
IMAGE_AUTH_BASE = "https://b2b:aico2012@e.aico.com.pl/"

DETAIL_AUTH = ("b2b", "aico2012")
FORM_LOGIN = "smarttradeorg"
FORM_PASSWORD = "Vectra321"

EXCLUDE_TOKENS = (
    "POJEMNIK",
    "PUDE",
    "KLIPS",
    "DO BUTELEK",
    "UCHWYT",
    "BUTELKA",
    "CHUSTA",
    "KUBK",
    "OBIADOWY",
)

GROUP_OVERRIDES = {
    "212110101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CAPEL BLUSH MIX",
    "222110101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CAPEL BLUSH MIX",
    "212112101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CHAMOMILE LAWN/VIOLET SKY MIX",
    "222112101": "SMOCZEK LIBERTY PACIFIER KOLOR 2 PAK LATEX SYMETRYCZNY CHAMOMILE LAWN/VIOLET SKY MIX",
    "2111417": "SMOCZEK 2 PAK LATEX ANATOMICZNY KOŚĆ SŁONIOWA/RÓŻ",
    "2211417": "SMOCZEK 2 PAK LATEX ANATOMICZNY KOŚĆ SŁONIOWA/RÓŻ",
    "11017101": "SMOCZEK STUDIO KOLOR 2 PAK LATEX KOŚĆ SŁONIOWA/JAŚMIN",
    "12017101": "SMOCZEK STUDIO KOLOR 2 PAK LATEX KOŚĆ SŁONIOWA/JAŚMIN",
    "11017103": "SMOCZEK STUDIO KOLOR 2 PAK LATEX JAŚMIN/RÓŻ",
    "12017103": "SMOCZEK STUDIO KOLOR 2 PAK LATEX JAŚMIN/RÓŻ",
    "11033101": "SMOCZEK MUMINKI MARZĄCY 2 PAK LATEX BABY PINK",
    "12033101": "SMOCZEK MUMINKI MARZĄCY 2 PAK LATEX BABY PINK",
}

SIZE_OVERRIDES = {"222110101": "2"}

SHOPIFY_HEADERS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Option3 Name",
    "Option3 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare-at Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Variant Barcode",
    "Image Src",
    "Image Alt Text",
]
