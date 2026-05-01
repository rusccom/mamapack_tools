param([switch]$DryRun)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "shopify_graphql.ps1")

$PlanPath = Join-Path $PSScriptRoot "tega_wanny_shopify_plan.json"
$SyncReportPath = Join-Path $PSScriptRoot "tega_wanny_shopify_sync_report.json"
$SeoReportPath = Join-Path $PSScriptRoot "tega_wanny_seo_update_report.json"

function Read-JsonFile {
  param([string]$Path)
  return Get-Content -Raw -Encoding UTF8 $Path | ConvertFrom-Json
}

function New-PlanMap {
  param($Plan)
  $map = @{}
  foreach ($product in $Plan.products) {
    $map[[string]$product.sku] = $product
  }
  return $map
}

function New-SeoItems {
  param($Report, $PlanMap)
  foreach ($item in $Report.products) {
    $product = $PlanMap[[string]$item.sourceSku]
    if ($product) { New-SeoItem $item $product }
  }
}

function New-SeoItem {
  param($SyncItem, $Product)
  $seo = New-SeoFields $Product
  [ordered]@{
    productId = [string]$SyncItem.productId
    sourceSku = [string]$SyncItem.sourceSku
    shopifySku = [string]$SyncItem.shopifySku
    title = [string]$Product.title
    oldHandle = [string]$SyncItem.handle
    handle = [string]$seo.handle
    seoTitle = [string]$seo.title
    seoDescription = [string]$seo.description
  }
}

function New-SeoFields {
  param($Product)
  $title = Limit-Text (New-SeoTitle $Product) 68
  [ordered]@{
    handle = Convert-ToSlug "$(New-SeoHandlePhrase $Product) $($Product.sku)"
    title = $title
    description = Limit-Text (New-SeoDescription $Product) 155
  }
}

function New-SeoTitle {
  param($Product)
  if (Is-FoldedBath $Product) {
    return Clean-Text "Wanienka składana Tega Baby z odpływem $(Get-SeoTitleAttribute $Product)"
  }
  $drain = if (Has-Drain $Product) { "z odpływem" } else { "" }
  return Clean-Text "Wanienka Tega Baby $($Product.collectionName) $($Product.size) $drain $(Get-SeoTitleAttribute $Product)"
}

function New-SeoHandlePhrase {
  param($Product)
  if (Is-FoldedBath $Product) {
    return Clean-Text "wanienka składana Tega Baby z odpływem $(Get-SeoColor $Product)"
  }
  $drain = if (Has-Drain $Product) { "z odpływem" } else { "" }
  return Clean-Text "wanienka Tega Baby $($Product.collectionName) $($Product.size) $drain $(Get-SeoHandleAttribute $Product)"
}

function New-SeoDescription {
  param($Product)
  if (Is-FoldedBath $Product) { return New-FoldedDescription $Product }
  $main = Clean-Text "Wanienka Tega Baby $($Product.collectionName) $($Product.size) $(Get-DrainText $Product)"
  $detail = New-AttributeSentence $Product
  $benefit = "Anatomiczny kształt, trwała grafika IML i łatwe czyszczenie."
  return Clean-Text "$main$detail. $benefit Idealna do codziennej kąpieli dziecka."
}

function New-FoldedDescription {
  param($Product)
  $attribute = New-AttributeSentence $Product
  $benefit = "Łatwa do składania, czyszczenia i przechowywania."
  return Clean-Text "Składana wanienka Tega Baby z odpływem$attribute. $benefit Praktyczna do codziennej kąpieli dziecka."
}

function New-AttributeSentence {
  param($Product)
  $motif = Get-DzikiMotif $Product.title
  if ($motif) { return " z motywem $motif" }
  $color = Get-SeoColorCase $Product
  if ($color) { return " w kolorze $color" }
  return ""
}

function Get-SeoTitleAttribute {
  param($Product)
  $motif = Get-DzikiMotif $Product.title
  if ($motif) { return "motyw $motif" }
  $color = Get-SeoColorTitle $Product
  return $color
}

function Get-SeoHandleAttribute {
  param($Product)
  $motif = Get-DzikiMotif $Product.title
  if ($motif) { return "motyw $motif" }
  return Get-SeoColor $Product
}

function Get-SeoColor {
  param($Product)
  $color = ([string]$Product.color).Trim()
  if (!$color -or $color -eq "ZACHÓD") { return "" }
  if ($color -eq "róż") { return "różowy" }
  return $color.ToLowerInvariant()
}

function Get-SeoColorCase {
  param($Product)
  $color = Get-SeoColor $Product
  $map = @{
    "biały" = "białym"; "beżowy" = "beżowym"; "granatowy" = "granatowym"
    "niebieska" = "niebieskim"; "różowy" = "różowym"; "szary" = "szarym"
    "turkusowy" = "turkusowym"; "zielona" = "zielonym"; "zielony" = "zielonym"
    "żółta" = "żółtym"; "żółty" = "żółtym"; "biała perła" = "białej perle"
  }
  if ($map.ContainsKey($color)) { return $map[$color] }
  return $color
}

function Get-SeoColorTitle {
  param($Product)
  $color = Get-SeoColor $Product
  $map = @{
    "beżowy" = "beżowa"; "biały" = "biała"; "granatowy" = "granatowa"
    "niebieska" = "niebieska"; "różowy" = "różowa"; "szary" = "szara"
    "turkusowy" = "turkusowa"; "zielona" = "zielona"; "zielony" = "zielona"
    "żółta" = "żółta"; "żółty" = "żółta"
  }
  if ($map.ContainsKey($color)) { return $map[$color] }
  return $color
}

function Get-DzikiMotif {
  param([string]$Title)
  if ($Title -match "JELONEK") { return "Jelonek" }
  if ($Title -match "SŁONIK") { return "Słonik" }
  return ""
}

function Get-DrainText {
  param($Product)
  if (Has-Drain $Product) { return "z odpływem" }
  return ""
}

function Has-Drain {
  param($Product)
  return ([string]$Product.title) -match "odpływ"
}

function Is-FoldedBath {
  param($Product)
  return ([string]$Product.collectionName) -eq "Składana"
}

function Clean-Text {
  param([string]$Value)
  return ($Value -replace "\s+", " ").Trim()
}

function Limit-Text {
  param([string]$Value, [int]$Limit)
  $clean = Clean-Text $Value
  if ($clean.Length -le $Limit) { return $clean }
  return Trim-ToWord $clean $Limit
}

function Trim-ToWord {
  param([string]$Value, [int]$Limit)
  $text = $Value.Substring(0, $Limit).Trim()
  $lastSpace = $text.LastIndexOf(" ")
  if ($lastSpace -gt 35) { $text = $text.Substring(0, $lastSpace) }
  return $text.Trim(" ,.-")
}

function Convert-ToSlug {
  param([string]$Value)
  $normalized = $Value.Normalize([Text.NormalizationForm]::FormD)
  $chars = foreach ($char in $normalized.ToCharArray()) {
    if ((Get-CharCategory $char) -ne [Globalization.UnicodeCategory]::NonSpacingMark) { $char }
  }
  $plain = (-join $chars).ToLowerInvariant()
  $plain = $plain -replace "ł", "l" -replace "Ł", "l"
  $slug = $plain -replace "[^a-z0-9]+", "-"
  return ($slug -replace "-{2,}", "-").Trim("-")
}

function Get-CharCategory {
  param([char]$Value)
  return [Globalization.CharUnicodeInfo]::GetUnicodeCategory($Value)
}

function Update-ShopifySeo {
  param($Item)
  return Update-ShopifyProductSeo `
    ([string]$Item.productId) `
    ([string]$Item.handle) `
    ([string]$Item.seoTitle) `
    ([string]$Item.seoDescription)
}

function New-UpdatedItem {
  param($Item, $Node)
  [ordered]@{
    productId = [string]$Item.productId
    sourceSku = [string]$Item.sourceSku
    shopifySku = [string]$Item.shopifySku
    handle = [string]$Node.handle
    seoTitle = [string]$Node.seo.title
    seoDescription = [string]$Node.seo.description
  }
}

function Save-SeoReport {
  param($Items)
  [ordered]@{
    updatedAt = (Get-Date).ToString("o")
    dryRun = [bool]$DryRun
    productCount = @($Items).Count
    products = @($Items)
  } | ConvertTo-Json -Depth 20 | Set-Content $SeoReportPath -Encoding UTF8
}

function Main {
  $plan = Read-JsonFile $PlanPath
  $syncReport = Read-JsonFile $SyncReportPath
  $items = @(New-SeoItems $syncReport (New-PlanMap $plan))
  if ($DryRun) { Save-SeoReport $items; return "Saved $SeoReportPath" }
  $updated = foreach ($item in $items) {
    $node = Update-ShopifySeo $item
    New-UpdatedItem $item $node
  }
  Save-SeoReport $updated
  "Saved $SeoReportPath"
}

Main
