Set-StrictMode -Version Latest

$ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $ProjectRoot "shopify_store\powershell\product_description_renderer.ps1")

function New-TegaDescriptionHtml {
  param($Product)
  return ConvertTo-ShopifyDescriptionHtml (New-TegaDescriptionSpec $Product)
}

function New-TegaDescriptionSpec {
  param($Product)
  return [ordered]@{
    eyebrow = "Tega Baby"; title = [string]$Product.title
    subtitle = [string]$Product.subtitle
    badges = @($Product.badges)
    introTitle = "Komfortowa kąpiel każdego dnia"
    introText = New-TegaIntroText $Product
    producerTitle = "Opis producenta"
    producerItems = Convert-SourceDescriptionToItems $Product.sourceDescription
    cards = @(New-TegaCards)
    detailsTitle = "Najważniejsze informacje"
    details = @(New-TegaDetails $Product)
    careTitle = "Pielęgnacja i użytkowanie"
    careSteps = @(New-TegaCareSteps)
    safetyTitle = "Ważne wskazówki"
    safetyText = New-TegaSafetyText
    sourceNote = New-TegaSourceNote $Product
  }
}

function New-TegaIntroText {
  param($Product)
  return @(
    [string]$Product.title,
    " to wygodna wanienka dla niemowląt i małych dzieci, zaprojektowana z myślą ",
    "o spokojnej codziennej kąpieli. Anatomiczny kształt ułatwia stabilne ułożenie ",
    "maluszka, a lekka konstrukcja pomaga rodzicom wygodnie przygotować kąpiel w domu."
  ) -join ""
}

function New-TegaCards {
  return @(
    (New-CardSpec "Anatomiczny kształt" "Wyprofilowana forma wspiera wygodne ułożenie dziecka podczas kąpieli." "&#10003;"),
    (New-CardSpec "Trwała grafika IML" "Niezmywalny motyw jest wykonany w technologii IML, więc pozostaje estetyczny przy codziennym użyciu." "&#10024;"),
    (New-CardSpec "Łatwe czyszczenie" "Gładka powierzchnia z tworzywa pozwala szybko wypłukać i wytrzeć wanienkę po kąpieli." "&#9728;"),
    (New-CardSpec "Jakość Tega Baby" "Produkt marki Tega Baby posiada potwierdzenie jakości TÜV Rheinland." "&#10084;")
  )
}

function New-CardSpec {
  param([string]$Title, [string]$Text, [string]$Icon)
  return [ordered]@{ title = $Title; text = $Text; icon = $Icon }
}

function New-TegaDetails {
  param($Product)
  return @(
    (New-DetailSpec "Marka" "Tega Baby"),
    (New-DetailSpec "Kolekcja" $Product.collectionName),
    (New-DetailSpec "Kolor" $Product.color),
    (New-DetailSpec "Długość wanienki" $Product.size),
    (New-DetailSpec "Materiał" "tworzywo sztuczne"),
    (New-DetailSpec "EAN" $Product.ean),
    (New-DetailSpec "Artykuł Marini" $Product.sku)
  )
}

function New-DetailSpec {
  param([string]$Label, [string]$Value)
  return [ordered]@{ label = $Label; value = $Value }
}

function New-TegaCareSteps {
  return @(
    "Po kąpieli wylej wodę i wypłucz wanienkę czystą wodą.",
    "Przetrzyj powierzchnię delikatną ściereczką.",
    "Przechowuj w suchym miejscu, z dala od bezpośrednich źródeł ciepła."
  )
}

function New-TegaSafetyText {
  return @(
    "Wanienki należy używać wyłącznie pod nadzorem osoby dorosłej. Przed kąpielą ",
    "zawsze sprawdź temperaturę wody i ustaw wanienkę na stabilnej powierzchni."
  ) -join ""
}

function New-TegaSourceNote {
  param($Product)
  return @(
    "Opis opracowano na podstawie danych Marini B2B oraz materiałów producenta ",
    "Tega Baby dla kolekcji ",
    [string]$Product.collectionName,
    "."
  ) -join ""
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
