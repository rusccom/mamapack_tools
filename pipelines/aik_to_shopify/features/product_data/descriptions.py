from shared.text_tools import list_text
from shopify_store.products.description_style import build_product_description


def material_label(title):
    upper = title.upper()
    if "LATEX" in upper or "KAUCZUK" in upper or "LATEKS" in upper:
        return "naturalny lateks"
    if "SILIKON" in upper:
        return "silikon"
    return "materiał zgodny z opisem produktu"


def pack_label(title):
    upper = title.upper()
    if "TRY-IT" in upper:
        return "zestaw Try-It"
    if "ZESTAW" in upper:
        return "zestaw"
    if "2 PAK" in upper:
        return "2-pak"
    if "1 SZT" in upper:
        return "1 sztuka"
    return "produkt dla dziecka"


def ean_list(variants):
    return list_text(sorted({item.barcode for item in variants if item.barcode}))


def sku_list(variants):
    return list_text(sorted({item.sku for item in variants if item.sku}))


def age_label(title):
    upper = title.upper()
    if "0+" in upper:
        return "od pierwszych dni życia"
    if "6+" in upper:
        return "od około 6. miesiąca"
    if "18+" in upper:
        return "od około 18. miesiąca"
    return "zgodnie z oznaczeniem producenta"


def shape_label(title):
    upper = title.upper()
    if "ANATOMICZ" in upper:
        return "anatomiczny"
    if "SYMETRYCZ" in upper:
        return "symetryczny"
    if "OKRĄG" in upper or "OKRAG" in upper:
        return "okrągły"
    return "dopasowany do produktu"


def build_description(title, vendor, option, variants):
    return build_product_description(description_spec(title, vendor, option, variants))


def description_spec(title, vendor, option, variants):
    return {
        "eyebrow": vendor,
        "title": title,
        "subtitle": subtitle_text(title),
        "badges": badge_items(title, option, variants),
        "introTitle": "Dlaczego rodzice wybierają ten model",
        "introText": intro_text(title, vendor),
        "cards": feature_cards(title),
        "detailsTitle": "Najważniejsze informacje",
        "details": detail_rows(title, vendor, option, variants),
        "careTitle": "Pielęgnacja i higiena",
        "careSteps": care_steps(title),
        "safetyTitle": "Ważne wskazówki",
        "safetyText": safety_text(),
    }


def badge_items(title, option, variants):
    option_name, option_values = option
    values = [shape_label(title), material_label(title), pack_label(title)]
    if option_name != "Title":
        values.append(list_text(option_values))
    label = "wariant" if len(variants) == 1 else "warianty"
    return [item for item in values + [f"{len(variants)} {label}"] if item]


def subtitle_text(title):
    base = pack_label(title).capitalize()
    return f"{base} dla dziecka, przygotowany z myślą o codziennym komforcie."


def intro_text(title, vendor):
    return (
        f"{title} to starannie dobrany produkt marki {vendor}, który łączy praktyczne "
        "zastosowanie z delikatnym wyglądem. Sprawdzi się w codziennej wyprawce i "
        "pomaga rodzicom wygodnie zadbać o potrzeby dziecka."
    )


def feature_cards(title):
    return [
        card("Wygoda na co dzień", "Przemyślana forma ułatwia regularne używanie produktu w domu i poza nim.", "&#10003;"),
        card("Delikatny wybór", f"{material_label(title).capitalize()} dobrze wpisuje się w potrzeby dziecięcej wyprawki.", "&#10084;"),
        card("Łatwe dopasowanie", f"Wariant {shape_label(title)} pomaga dobrać produkt do wieku i preferencji dziecka.", "&#9728;"),
        card("Czytelne informacje", "Najważniejsze cechy, warianty i kody są zebrane w jednym miejscu, aby ułatwić wybór.", "&#10024;"),
    ]


def card(title, text, icon):
    return {"title": title, "text": text, "icon": icon}


def detail_rows(title, vendor, option, variants):
    return [
        row("Marka", vendor),
        row("Materiał", material_label(title)),
        row("Wiek / rozmiar", age_or_option(title, option)),
        row("SKU", sku_list(variants) or "uzupełniane automatycznie"),
        row("EAN", ean_list(variants) or "brak danych"),
    ]


def age_or_option(title, option):
    option_name, option_values = option
    if option_name == "Title":
        return age_label(title)
    return list_text(option_values) or age_label(title)


def row(label, value):
    return {"label": label, "value": value}


def care_steps(title):
    steps = [
        "Przed użyciem sprawdź stan produktu i przygotuj go zgodnie z zaleceniami producenta.",
        "Czyść delikatnie, używając metody odpowiedniej dla materiału produktu.",
        "Przechowuj w suchym, czystym miejscu, z dala od bezpośrednich źródeł ciepła.",
    ]
    if "SMOCZ" in title.upper():
        steps[1] = "W przypadku smoczka dbaj o regularną higienę i wymieniaj go zgodnie z zaleceniami producenta."
    return steps


def safety_text():
    return (
        "Produkt powinien być używany pod opieką osoby dorosłej. Przed każdym użyciem "
        "sprawdź, czy nie ma uszkodzeń, i nie używaj produktu, jeśli jego stan budzi wątpliwości."
    )
