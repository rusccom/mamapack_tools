import html


ROOT_STYLE = "font-family:Arial,Helvetica,sans-serif;color:#33252f;line-height:1.65;"
PANEL_STYLE = "background:#ffffff;border:1px solid #f1d8de;border-radius:22px;padding:22px;margin:0 0 18px;"
BADGE_STYLE = "display:inline-block;margin:0 8px 8px 0;padding:8px 12px;border-radius:999px;background:#ffffff;border:1px solid #efc7d1;font-size:13px;color:#7a4b5c;font-weight:700;"
CARD_STYLE = "display:block;box-sizing:border-box;margin:0;padding:18px;border-radius:20px;background:#fffafb;border:1px solid #f1d8de;"
GRID_STYLE = "display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:0 0 18px;"


def build_product_description(spec):
    parts = [
        f'<div style="{ROOT_STYLE}">',
        hero_section(spec),
        text_panel(spec.get("introTitle"), spec.get("introText")),
        item_panel(spec.get("producerTitle"), spec.get("producerItems")),
        feature_section(spec.get("cards")),
        details_section(spec.get("detailsTitle"), spec.get("details")),
        steps_panel(spec.get("careTitle"), spec.get("careSteps")),
        text_panel(spec.get("safetyTitle"), spec.get("safetyText")),
        source_note(spec.get("sourceNote")),
        "</div>",
    ]
    return "".join(item for item in parts if item)


def hero_section(spec):
    title = spec.get("title")
    if not title:
        return ""
    eyebrow = hero_eyebrow(spec.get("eyebrow"))
    heading = f'<h2 style="margin:0 0 10px;font-size:28px;line-height:1.2;color:#2f1f29;">{escape(title)}</h2>'
    subtitle = hero_subtitle(spec.get("subtitle"))
    badges = badges_html(spec.get("badges"))
    style = "background:linear-gradient(135deg,#fde8ee 0%,#fff7f3 100%);border:1px solid #f4cbd6;border-radius:24px;padding:28px;margin:0 0 18px;"
    return f'<section style="{style}">{eyebrow}{heading}{subtitle}<div>{badges}</div></section>'


def hero_eyebrow(value):
    if not value:
        return ""
    style = "margin:0 0 10px;font-size:12px;letter-spacing:1.2px;text-transform:uppercase;color:#b3657c;font-weight:700;"
    return f'<p style="{style}">{escape(value)}</p>'


def hero_subtitle(value):
    if not value:
        return ""
    return f'<p style="margin:0 0 16px;font-size:16px;color:#5f4954;">{escape(value)}</p>'


def text_panel(title, text):
    if not title or not text:
        return ""
    return panel_html(title, escape(text))


def item_panel(title, items):
    values = as_list(items)
    if not title or not values:
        return ""
    body = "".join(check_item(item) for item in values)
    return panel_html(title, body)


def feature_section(cards):
    values = as_list(cards)
    if not values:
        return ""
    return f'<section style="{GRID_STYLE}">' + "".join(feature_card(item) for item in values) + "</section>"


def feature_card(card):
    icon = str(card.get("icon") or "&#10003;")
    title = escape(card.get("title"))
    text = escape(card.get("text"))
    icon_html = f'<div style="font-size:20px;color:#c16580;margin:0 0 10px;">{icon}</div>'
    heading = f'<h3 style="margin:0 0 8px;font-size:17px;color:#342630;">{title}</h3>'
    body = f'<p style="margin:0;font-size:14px;color:#604955;">{text}</p>'
    return f'<div style="{CARD_STYLE}">{icon_html}{heading}{body}</div>'


def details_section(title, rows):
    values = as_list(rows)
    if not title or not values:
        return ""
    body = '<div style="margin-top:12px;">' + "".join(detail_row(item) for item in values) + "</div>"
    return panel_html(title, body)


def detail_row(row):
    style = "display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #f1d8de;"
    label = f'<strong style="color:#503743;">{escape(row.get("label"))}</strong>'
    value = f'<span style="color:#6a5260;text-align:right;">{escape(row.get("value"))}</span>'
    return f'<div style="{style}">{label}{value}</div>'


def steps_panel(title, steps):
    values = as_list(steps)
    if not title or not values:
        return ""
    return panel_html(title, "".join(step_html(item) for item in values))


def step_html(text):
    style = "display:inline-block;width:24px;height:24px;border-radius:50%;background:#f7d7df;color:#8f5368;font-weight:700;text-align:center;line-height:24px;"
    dot = f'<span style="{style}">&#8226;</span>'
    body = f'<span style="color:#5f4954;">{escape(text)}</span>'
    return f'<div style="display:flex;gap:10px;margin:0 0 8px;">{dot}{body}</div>'


def check_item(text):
    mark = '<span style="color:#c16580;font-weight:700;">&#10003;</span>'
    body = f'<span style="color:#5f4954;">{escape(text)}</span>'
    return f'<div style="display:flex;gap:10px;margin:0 0 8px;">{mark}{body}</div>'


def badges_html(items):
    return "".join(badge_html(item) for item in as_list(items))


def badge_html(text):
    return f'<span style="{BADGE_STYLE}">{escape(text)}</span>'


def panel_html(title, body):
    heading = f'<h3 style="margin:0 0 10px;font-size:20px;color:#342630;">{escape(title)}</h3>'
    return f'<section style="{PANEL_STYLE}">{heading}{body}</section>'


def source_note(text):
    if not text:
        return ""
    return f'<p style="margin:18px 0 0;font-size:12px;color:#826775;">{escape(text)}</p>'


def as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return value if isinstance(value, list) else list(value)


def escape(value):
    return html.escape(str(value or ""))
