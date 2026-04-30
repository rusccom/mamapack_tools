import html

from shared.text_tools import list_text


def material_label(title):
    upper = title.upper()
    if "LATEX" in upper or "KAUCZUK" in upper:
        return "латекс"
    if "SILIKON" in upper:
        return "силикон"
    return "не указан"


def pack_label(title):
    upper = title.upper()
    if "TRY-IT" in upper:
        return "набор Try-It"
    if "ZESTAW" in upper:
        return "набор"
    if "2 PAK" in upper:
        return "комплект из 2 штук"
    return "товар из каталога B2B"


def ean_list(variants):
    return list_text(sorted({item.barcode for item in variants if item.barcode}))


def sku_list(variants):
    return list_text(sorted({item.sku for item in variants if item.sku}))


def source_links_html(links):
    items = [f'<li><a href="{html.escape(link)}">{html.escape(link)}</a></li>' for link in links]
    return "<ul>" + "".join(items) + "</ul>"


def build_description(title, vendor, option_name, option_values, variants, links):
    sizes = list_text(option_values if option_name == "Size" else ())
    intro = f"<p>{html.escape(title)} — {pack_label(title)} бренда {html.escape(vendor)}."
    intro += " Карточка подготовлена для черновика Shopify и уже содержит основные варианты товара.</p>"
    details = [
        f"<li>Бренд: {html.escape(vendor)}</li>",
        f"<li>Материал: {html.escape(material_label(title))}</li>",
        f"<li>Размеры: {html.escape(sizes or 'без разделения по размеру')}</li>",
        f"<li>SKU поставщика: {html.escape(sku_list(variants) or 'будет сгенерирован автоматически')}</li>",
        f"<li>EAN: {html.escape(ean_list(variants) or 'нет данных')}</li>",
    ]
    note = "<p>Описание сформировано автоматически на основе каталога AICO B2B и рассчитано на быструю ручную проверку перед публикацией.</p>"
    source = "<p>Исходные страницы поставщика:</p>" + source_links_html(links)
    return intro + "<ul>" + "".join(details) + "</ul>" + note + source
