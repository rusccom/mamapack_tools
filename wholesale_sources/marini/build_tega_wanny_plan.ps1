$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "tega_description_style.ps1")

$XmlUrl = "https://marini.pl/b2b/marini-b2b.xml"
$XmlPath = Join-Path $PSScriptRoot "marini-b2b.xml"
$PageExtractPath = Join-Path $PSScriptRoot "tega_wanny_page_extract.json"
$StockRecheckPath = Join-Path $PSScriptRoot "tega_wanny_stock_recheck.json"
$OutputPath = Join-Path $PSScriptRoot "tega_wanny_shopify_plan.json"

function Ensure-MariniXml {
  if (Test-Path $XmlPath) { return }
  Invoke-WebRequest -Uri $XmlUrl -OutFile $XmlPath -UseBasicParsing
}

function Read-MariniXml {
  Ensure-MariniXml
  return [xml](Get-Content -Raw -Encoding UTF8 $XmlPath)
}

function Read-PositiveRows {
  $path = if (Test-Path $StockRecheckPath) { $StockRecheckPath } else { $PageExtractPath }
  $data = Get-Content -Raw -Encoding UTF8 $path | ConvertFrom-Json
  return @($data.rows | Where-Object { [int]$_.stock -gt 0 })
}

function Find-XmlItem {
  param($Xml, [string]$Code)
  $item = $Xml.MARINI.b2b | Where-Object { $_.kod -eq $Code } | Select-Object -First 1
  if (!$item) { throw "Marini XML item not found: $Code" }
  return $item
}

function Split-Images {
  param([string]$Value)
  if (!$Value) { return @() }
  return @($Value -split "\s+" | Where-Object { $_ })
}

function Get-XmlValue {
  param($Item, [string]$Name)
  if ($Item.PSObject.Properties.Name -contains $Name) {
    return [string]$Item.$Name
  }
  return ""
}

function Convert-ToSlug {
  param([string]$Value)
  $normalized = $Value.Normalize([Text.NormalizationForm]::FormD)
  $chars = foreach ($char in $normalized.ToCharArray()) {
    $category = [Globalization.CharUnicodeInfo]::GetUnicodeCategory($char)
    if ($category -ne [Globalization.UnicodeCategory]::NonSpacingMark) { $char }
  }
  $plain = (-join $chars).ToLowerInvariant()
  $plain = $plain -replace "ł", "l" -replace "Ł", "l"
  $slug = $plain -replace "[^a-z0-9]+", "-"
  return ($slug -replace "-{2,}", "-").Trim("-")
}

function Get-ProductSpec {
  param($Row)
  $name = Normalize-ProductName $Row.name
  $size = Get-ProductSize $name
  $collection = Get-ProductCollection $name
  $color = Get-ProductColor $name $collection
  [ordered]@{
    title = "Tega Baby $name"
    subtitle = New-Subtitle $size $collection $color
    collectionName = $collection
    color = $color
    size = $size
    producerCode = Get-ProducerCode $Row.name
    officialUrl = "https://www.tega.com.pl/"
    badges = New-Badges $size $collection $color $name
  }
}

function Normalize-ProductName {
  param([string]$Name)
  $value = ($Name -replace "^TEGA\s+", "").Trim()
  $value = $value -replace "\s+", " "
  return $value
}

function Get-ProductSize {
  param([string]$Name)
  $match = [regex]::Match($Name, "\b(86|102)\s*cm\b", "IgnoreCase")
  if ($match.Success) { return "$($match.Groups[1].Value) cm" }
  return "standard"
}

function Get-ProducerCode {
  param([string]$Name)
  $match = [regex]::Match($Name, "^TEGA\s+(.+?)\s+Wann", "IgnoreCase")
  if ($match.Success) { return $match.Groups[1].Value.Trim() }
  return ""
}

function Get-ProductCollection {
  param([string]$Name)
  foreach ($item in Product-Collections) {
    if ($Name -match [regex]::Escape($item)) { return Format-Collection $item }
  }
  if ($Name -match "składana") { return "Składana" }
  return "Wanienka"
}

function Product-Collections {
  return @("LEŚNA OPOWIEŚĆ", "DZIKI ZACHÓD", "KRÓLICZKI", "KACZKA", "METEO", "Monsters", "MIŚ")
}

function Format-Collection {
  param([string]$Value)
  $map = @{
    "LEŚNA OPOWIEŚĆ" = "Leśna Opowieść"
    "DZIKI ZACHÓD" = "Dziki Zachód"
    "KRÓLICZKI" = "Króliczki"
    "KACZKA" = "Kaczka"
    "METEO" = "Meteo"
    "Monsters" = "Monsters"
    "MIŚ" = "Miś"
  }
  return $map[$Value]
}

function Get-ProductColor {
  param([string]$Name, [string]$Collection)
  $tail = ($Name -replace ".*$([regex]::Escape($Collection))", "").Trim()
  $tail = $tail -replace "^(j\.|LUX|z odpływem)\s*", ""
  if (!$tail -or $tail -eq $Name) { $tail = Last-ColorToken $Name }
  return Normalize-Color $tail
}

function Last-ColorToken {
  param([string]$Name)
  $parts = $Name -split "\s+"
  return $parts[-1]
}

function Normalize-Color {
  param([string]$Value)
  $color = ($Value -replace "\s+", " ").Trim(" -")
  if ($color -eq "j.szary") { return "jasny szary" }
  if ($color -match "^j\.") { return "jasny " + $color.Substring(2) }
  return $color
}

function New-Subtitle {
  param([string]$Size, [string]$Collection, [string]$Color)
  $base = "Wanienka dla dziecka $Size"
  if ($Collection -and $Collection -ne "Wanienka") { $base += " z kolekcji $Collection" }
  if ($Color) { $base += " w kolorze $Color" }
  return "$base."
}

function New-Badges {
  param([string]$Size, [string]$Collection, [string]$Color, [string]$Name)
  $badges = @($Size, "kolekcja $Collection", $Color, "IML", "TÜV Rheinland")
  if ($Name -match "odpływ") { $badges = @($badges[0], "z odpływem") + $badges[1..4] }
  return @($badges | Where-Object { $_ -and $_ -ne "standard" })
}

function New-PlanProduct {
  param($Row, $XmlItem)
  $spec = Get-ProductSpec $Row
  $model = New-ProductModel $Row $XmlItem $spec
  $model.descriptionHtml = New-TegaDescriptionHtml $model
  Assert-PolishText $model.title
  Assert-PolishText $model.descriptionHtml
  return $model
}

function Assert-PolishText {
  param([string]$Value)
  if ($Value -match "[РДЕГСЃЃЉЊЋ]") {
    throw "Broken encoding detected in generated Polish text."
  }
}

function New-ProductModel {
  param($Row, $XmlItem, $Spec)
  [pscustomobject][ordered]@{
    source = "marini"
    sourceUrl = $Row.href
    officialSourceUrl = $Spec.officialUrl
    sku = [string]$XmlItem.kod
    producerCode = $Spec.producerCode
    title = $Spec.title
    supplierTitle = [string]$XmlItem.nazwa
    subtitle = $Spec.subtitle
    handle = Convert-ToSlug $Spec.title
    vendor = "Tega Baby"
    productType = "Wanienki"
    status = "DRAFT"
    price = [string]$XmlItem.cena
    ean = [string]$XmlItem.EAN
    stock = [int]$Row.stock
    sourceStockLabel = Get-XmlValue $XmlItem "stan"
    sourceCategory = Get-XmlValue $XmlItem "grupa"
    sourceDescription = Get-XmlValue $XmlItem "opis"
    collectionName = $Spec.collectionName
    color = $Spec.color
    size = $Spec.size
    badges = @($Spec.badges)
    imageUrls = @(Split-Images (Get-XmlValue $XmlItem "zdjecia"))
    tags = @("Tega Baby", "Wanienki", "Dla dziecka", "Marini B2B", (Get-XmlValue $XmlItem "grupa"))
    descriptionHtml = ""
  }
}

function New-Plan {
  $xml = Read-MariniXml
  $rows = Read-PositiveRows
  $products = foreach ($row in $rows) {
    New-PlanProduct $row (Find-XmlItem $xml $row.code)
  }
  [ordered]@{
    createdAt = (Get-Date).ToString("o")
    sourceCategoryUrl = "https://b2b.marini.pl/items/352?parent=0"
    parentCollectionId = "gid://shopify/Collection/616586740045"
    childCollectionTitle = "Wanienki"
    productCount = @($products).Count
    products = @($products)
  }
}

$plan = New-Plan
$plan | ConvertTo-Json -Depth 20 | Set-Content $OutputPath -Encoding UTF8
"Saved $OutputPath"
