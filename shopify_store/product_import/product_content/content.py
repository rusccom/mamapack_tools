def build_description_html(article: str) -> str:
    parts = [
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#33252f;line-height:1.65;">',
        hero_section(),
        intro_section(),
        features_section(),
        details_section(article),
        care_section(),
        safety_section(),
        source_note(),
        "</div>",
    ]
    return "".join(parts)


def hero_section() -> str:
    badges = "".join(badge(text) for text in hero_badges())
    title = "BIBS Colour Blush 1001000244"
    subtitle = "Smoczek anatomiczny z naturalnego lateksu dla dzieci od pierwszych dni życia."
    return (
        '<section style="background:linear-gradient(135deg,#fde8ee 0%,#fff7f3 100%);'
        'border:1px solid #f4cbd6;border-radius:24px;padding:28px;margin:0 0 18px;">'
        '<p style="margin:0 0 10px;font-size:12px;letter-spacing:1.2px;text-transform:uppercase;'
        'color:#b3657c;font-weight:700;">BIBS Denmark</p>'
        f'<h2 style="margin:0 0 10px;font-size:28px;line-height:1.2;color:#2f1f29;">{title}</h2>'
        f'<p style="margin:0 0 16px;font-size:16px;color:#5f4954;">{subtitle}</p>'
        f'<div>{badges}</div>'
        "</section>"
    )


def hero_badges() -> tuple[str, ...]:
    return (
        "anatomiczny ksztalt",
        "naturalny lateks",
        "rozmiar 1 / 0+ mies.",
        "kolor blush",
        "1 sztuka",
    )


def badge(text: str) -> str:
    return (
        '<span style="display:inline-block;margin:0 8px 8px 0;padding:8px 12px;'
        'border-radius:999px;background:#ffffff;border:1px solid #efc7d1;'
        'font-size:13px;color:#7a4b5c;font-weight:700;">'
        f"{text}</span>"
    )


def intro_section() -> str:
    paragraph = (
        "BIBS Colour to kultowy smoczek zaprojektowany i produkowany w Danii. "
        "Wariant Blush w wersji anatomicznej laczy delikatny, skandynawski wyglad "
        "z miekkim smoczkiem z naturalnego kauczuku, ktory przypomina dziecku "
        "cieplo i elastycznosc naturalnego karmienia."
    )
    return panel("Dlaczego rodzice wybieraja ten model", paragraph)


def features_section() -> str:
    cards = "".join(feature_card(title, text, icon) for title, text, icon in feature_rows())
    return f'<section style="margin:0 0 18px;">{cards}</section>'


def feature_rows() -> tuple[tuple[str, str, str], ...]:
    return (
        ("Anatomiczny smoczek", "Profilowany ksztalt wspiera naturalne ulozenie jezyka i ogranicza nacisk na podniebienie, dziasla i zabki.", "&#10003;"),
        ("Naturalna miekkosc", "Lateks z naturalnego kauczuku jest elastyczny, przyjemny w kontakcie ze skora i dobrze reaguje na ssanie.", "&#10084;"),
        ("Mniej podraznien", "Lekka oslonka z otworami wentylacyjnymi ogranicza kontakt ze skora i pomaga zmniejszyc gromadzenie wilgoci.", "&#9728;"),
        ("Jakosc BIBS", "Produkt jest wolny od BPA, PFAS i ftalanow oraz zgodny z europejska norma EN 1400+A2.", "&#10024;"),
    )


def feature_card(title: str, text: str, icon: str) -> str:
    return (
        '<div style="display:inline-block;vertical-align:top;width:48%;min-width:240px;'
        'box-sizing:border-box;margin:0 2% 14px 0;padding:18px;border-radius:20px;'
        'background:#fffafb;border:1px solid #f1d8de;">'
        f'<div style="font-size:20px;color:#c16580;margin:0 0 10px;">{icon}</div>'
        f'<h3 style="margin:0 0 8px;font-size:17px;color:#342630;">{title}</h3>'
        f'<p style="margin:0;font-size:14px;color:#604955;">{text}</p>'
        "</div>"
    )


def details_section(article: str) -> str:
    rows = "".join(detail_row(label, value) for label, value in detail_rows(article))
    return panel("Najwazniejsze informacje", f'<div style="margin-top:12px;">{rows}</div>')


def detail_rows(article: str) -> tuple[tuple[str, str], ...]:
    return (
        ("Linia", "BIBS Colour"),
        ("Kolor", "Blush / rozowy"),
        ("Ksztalt smoczka", "anatomiczny / ortodontyczny"),
        ("Material smoczka", "naturalny lateks"),
        ("Rozmiar", "1, rekomendowany od 0+ miesiecy"),
        ("Kraj projektu i produkcji", "Dania / UE"),
        ("Artykul sklepu", article),
    )


def detail_row(label: str, value: str) -> str:
    return (
        '<div style="display:flex;justify-content:space-between;gap:12px;padding:10px 0;'
        'border-bottom:1px solid #f1d8de;">'
        f'<strong style="color:#503743;">{label}</strong>'
        f'<span style="color:#6a5260;text-align:right;">{value}</span>'
        "</div>"
    )


def care_section() -> str:
    steps = "".join(care_step(text) for text in care_steps())
    text = (
        "<p style=\"margin:0 0 12px;\">Przed pierwszym uzyciem wysterylizuj smoczek przez "
        "5 minut we wrzatku. Do codziennej higieny BIBS rekomenduje metode zalewania "
        "wrzatkiem zamiast gotowania w garnku czy sterylizacji w mikrofalowce.</p>"
        f"{steps}"
    )
    return panel("Pielegnacja i higiena", text)


def care_steps() -> tuple[str, ...]:
    return (
        "Wloz smoczek do czystej miseczki.",
        "Zalej wrzatkiem tak, aby byl calkowicie przykryty.",
        "Pozostaw na okolo 5 minut.",
        "Wyjmij i odloz na czysty recznik do wyschniecia.",
        "Delikatnie wycisnij nadmiar wody ze smoczka.",
    )


def care_step(text: str) -> str:
    return (
        '<div style="display:flex;gap:10px;margin:0 0 8px;">'
        '<span style="display:inline-block;width:24px;height:24px;border-radius:50%;'
        'background:#f7d7df;color:#8f5368;font-weight:700;text-align:center;line-height:24px;">'
        '&#8226;</span>'
        f'<span style="color:#5f4954;">{text}</span>'
        "</div>"
    )


def safety_section() -> str:
    note = (
        "Naturalny lateks jest surowcem pochodzenia naturalnego, dlatego moze delikatnie "
        "roznic sie kolorem i z czasem zmieniac ksztalt. Smoczek trzeba regularnie "
        "kontrolowac i wymieniac co 4-6 tygodni lub szybciej, jezeli pojawia sie slady zuzycia."
    )
    return panel("Wazne wskazowki", note)


def source_note() -> str:
    text = (
        "Opis zostal opracowany na podstawie oficjalnych materialow BIBS dla produktu "
        "Colour Blush oraz wytycznych marki dotyczacych materialow, pielegnacji i bezpieczenstwa."
    )
    return f'<p style="margin:18px 0 0;font-size:12px;color:#826775;">{text}</p>'


def panel(title: str, body: str) -> str:
    return (
        '<section style="background:#ffffff;border:1px solid #f1d8de;border-radius:22px;'
        'padding:22px;margin:0 0 18px;">'
        f'<h3 style="margin:0 0 10px;font-size:20px;color:#342630;">{title}</h3>'
        f"{body}"
        "</section>"
    )

