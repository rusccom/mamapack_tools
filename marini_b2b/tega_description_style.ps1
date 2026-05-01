Set-StrictMode -Version Latest

function Convert-HtmlText {
  param([string]$Value)
  return [System.Net.WebUtility]::HtmlEncode($Value)
}

function New-TegaDescriptionHtml {
  param($Product)
  $parts = @(
    '<div style="font-family:Arial,Helvetica,sans-serif;color:#33252f;line-height:1.65;">',
    (New-HeroSection $Product),
    (New-IntroSection $Product),
    (New-ProducerDescriptionSection $Product),
    (New-FeatureSection),
    (New-DetailsSection $Product),
    (New-CareSection),
    (New-SafetySection),
    (New-SourceNote $Product),
    '</div>'
  )
  return ($parts -join "")
}

function New-HeroSection {
  param($Product)
  $badges = $Product.badges | ForEach-Object { New-Badge $_ }
  return @(
    '<section style="background:linear-gradient(135deg,#e8f4f7 0%,#fff8f1 100%);',
    'border:1px solid #cfe6ea;border-radius:24px;padding:28px;margin:0 0 18px;">',
    '<p style="margin:0 0 10px;font-size:12px;letter-spacing:1.2px;text-transform:uppercase;',
    'color:#367988;font-weight:700;">Tega Baby</p>',
    '<h2 style="margin:0 0 10px;font-size:28px;line-height:1.2;color:#263238;">',
    (Convert-HtmlText $Product.title),
    '</h2><p style="margin:0 0 16px;font-size:16px;color:#526269;">',
    (Convert-HtmlText $Product.subtitle),
    '</p><div>',
    ($badges -join ""),
    '</div></section>'
  ) -join ""
}

function New-Badge {
  param([string]$Text)
  return @(
    '<span style="display:inline-block;margin:0 8px 8px 0;padding:8px 12px;',
    'border-radius:999px;background:#ffffff;border:1px solid #cfe6ea;',
    'font-size:13px;color:#476d75;font-weight:700;">',
    (Convert-HtmlText $Text),
    '</span>'
  ) -join ""
}

function New-IntroSection {
  param($Product)
  $body = @(
    (Convert-HtmlText $Product.title),
    ' to wygodna wanienka dla niemowląt i małych dzieci, zaprojektowana z myślą ',
    'o spokojnej codziennej kąpieli. Anatomiczny kształt ułatwia stabilne ułożenie ',
    'maluszka, a lekka konstrukcja pomaga rodzicom wygodnie przygotować kąpiel w domu.'
  ) -join ""
  return New-Panel "Komfortowa kąpiel każdego dnia" $body
}

function New-FeatureSection {
  $cards = @(
    (New-FeatureCard "Anatomiczny kształt" "Wyprofilowana forma wspiera wygodne ułożenie dziecka podczas kąpieli." "&#10003;"),
    (New-FeatureCard "Trwała grafika IML" "Niezmywalny motyw jest wykonany w technologii IML, więc pozostaje estetyczny przy codziennym użyciu." "&#10024;"),
    (New-FeatureCard "Łatwe czyszczenie" "Gładka powierzchnia z tworzywa pozwala szybko wypłukać i wytrzeć wanienkę po kąpieli." "&#9728;"),
    (New-FeatureCard "Jakość Tega Baby" "Produkt marki Tega Baby posiada potwierdzenie jakości TÜV Rheinland." "&#10084;")
  )
  return '<section style="margin:0 0 18px;">' + ($cards -join "") + '</section>'
}

function New-ProducerDescriptionSection {
  param($Product)
  $items = Convert-SourceDescriptionToItems $Product.sourceDescription
  if (!$items -or $items.Count -eq 0) { return "" }
  $body = @($items | ForEach-Object { New-SourceDescriptionItem $_ }) -join ""
  return New-Panel "Opis producenta" $body
}

function Convert-SourceDescriptionToItems {
  param([string]$Text)
  if (!$Text) { return @() }
  $decoded = [System.Net.WebUtility]::HtmlDecode($Text)
  $plain = $decoded -replace "<[^>]+>", " "
  $plain = $plain -replace "Fukcjonalna", "Funkcjonalna"
  $parts = $plain -split "[`r`n•]+"
  return @($parts | ForEach-Object { Normalize-SourceItem $_ } | Where-Object { $_ })
}

function Normalize-SourceItem {
  param([string]$Text)
  $value = ($Text -replace "\s+", " ").Trim(" .-")
  if (!$value) { return "" }
  return "$value."
}

function New-SourceDescriptionItem {
  param([string]$Text)
  return @(
    '<div style="display:flex;gap:10px;margin:0 0 8px;">',
    '<span style="color:#4d9bae;font-weight:700;">&#10003;</span>',
    '<span style="color:#526269;">',
    (Convert-HtmlText $Text),
    '</span></div>'
  ) -join ""
}

function New-FeatureCard {
  param([string]$Title, [string]$Text, [string]$Icon)
  return @(
    '<div style="display:inline-block;vertical-align:top;width:48%;min-width:240px;',
    'box-sizing:border-box;margin:0 2% 14px 0;padding:18px;border-radius:20px;',
    'background:#fbfeff;border:1px solid #d9edf1;">',
    '<div style="font-size:20px;color:#4d9bae;margin:0 0 10px;">',
    $Icon,
    '</div><h3 style="margin:0 0 8px;font-size:17px;color:#2d3840;">',
    (Convert-HtmlText $Title),
    '</h3><p style="margin:0;font-size:14px;color:#526269;">',
    (Convert-HtmlText $Text),
    '</p></div>'
  ) -join ""
}

function New-DetailsSection {
  param($Product)
  $rows = @(
    (New-DetailRow "Marka" "Tega Baby"),
    (New-DetailRow "Kolekcja" $Product.collectionName),
    (New-DetailRow "Kolor" $Product.color),
    (New-DetailRow "Długość wanienki" $Product.size),
    (New-DetailRow "Materiał" "tworzywo sztuczne"),
    (New-DetailRow "EAN" $Product.ean),
    (New-DetailRow "Artykuł Marini" $Product.sku)
  )
  return New-Panel "Najważniejsze informacje" ('<div style="margin-top:12px;">' + ($rows -join "") + '</div>')
}

function New-DetailRow {
  param([string]$Label, [string]$Value)
  return @(
    '<div style="display:flex;justify-content:space-between;gap:12px;padding:10px 0;',
    'border-bottom:1px solid #d9edf1;"><strong style="color:#34424a;">',
    (Convert-HtmlText $Label),
    '</strong><span style="color:#526269;text-align:right;">',
    (Convert-HtmlText $Value),
    '</span></div>'
  ) -join ""
}

function New-CareSection {
  $steps = @(
    (New-CareStep "Po kąpieli wylej wodę i wypłucz wanienkę czystą wodą."),
    (New-CareStep "Przetrzyj powierzchnię delikatną ściereczką."),
    (New-CareStep "Przechowuj w suchym miejscu, z dala od bezpośrednich źródeł ciepła.")
  )
  return New-Panel "Pielęgnacja i użytkowanie" (($steps -join ""))
}

function New-CareStep {
  param([string]$Text)
  return @(
    '<div style="display:flex;gap:10px;margin:0 0 8px;">',
    '<span style="display:inline-block;width:24px;height:24px;border-radius:50%;',
    'background:#dff0f3;color:#357987;font-weight:700;text-align:center;line-height:24px;">',
    '&#8226;</span><span style="color:#526269;">',
    (Convert-HtmlText $Text),
    '</span></div>'
  ) -join ""
}

function New-SafetySection {
  $text = @(
    'Wanienki należy używać wyłącznie pod nadzorem osoby dorosłej. Przed kąpielą ',
    'zawsze sprawdź temperaturę wody i ustaw wanienkę na stabilnej powierzchni.'
  ) -join ""
  return New-Panel "Ważne wskazówki" $text
}

function New-SourceNote {
  param($Product)
  $text = @(
    'Opis opracowano na podstawie danych Marini B2B oraz materiałów producenta ',
    'Tega Baby dla kolekcji ',
    $Product.collectionName,
    '.'
  ) -join ""
  return '<p style="margin:18px 0 0;font-size:12px;color:#6f7f86;">' + (Convert-HtmlText $text) + '</p>'
}

function New-Panel {
  param([string]$Title, [string]$Body)
  return @(
    '<section style="background:#ffffff;border:1px solid #d9edf1;border-radius:22px;',
    'padding:22px;margin:0 0 18px;"><h3 style="margin:0 0 10px;font-size:20px;color:#2d3840;">',
    (Convert-HtmlText $Title),
    '</h3>',
    $Body,
    '</section>'
  ) -join ""
}
