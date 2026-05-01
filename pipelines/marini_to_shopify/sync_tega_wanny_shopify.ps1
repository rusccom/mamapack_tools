$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
. (Join-Path $ProjectRoot "shopify_store\powershell\shopify_graphql.ps1")

$PlanPath = Join-Path $PSScriptRoot "tega_wanny_shopify_plan.json"
$ReportPath = Join-Path $PSScriptRoot "tega_wanny_shopify_sync_report.json"
$ParentCollectionId = "gid://shopify/Collection/616586740045"
$ChildCollectionTitle = "Wanienki"
$ChildCollectionHandle = "wanienki"

function Read-Plan {
  if (!(Test-Path $PlanPath)) {
    & (Join-Path $PSScriptRoot "build_tega_wanny_plan.ps1") | Out-Null
  }
  return Get-Content -Raw -Encoding UTF8 $PlanPath | ConvertFrom-Json
}

function Assert-PlanReady {
  param($Plan)
  if (@($Plan.products).Count -gt 0) { return }
  throw "No products are ready to sync."
}

function Get-ProductsWithoutImages {
  param($Plan)
  return @($Plan.products | Where-Object { !$_.imageUrls -or $_.imageUrls.Count -eq 0 })
}

function New-FilteredPlan {
  param($Plan)
  $products = @($Plan.products | Where-Object { $_.imageUrls -and $_.imageUrls.Count -gt 0 })
  [pscustomobject][ordered]@{
    sourceCategoryUrl = $Plan.sourceCategoryUrl
    parentCollectionId = $Plan.parentCollectionId
    childCollectionTitle = $Plan.childCollectionTitle
    productCount = $products.Count
    products = $products
  }
}

function New-ProductFiles {
  param($Product)
  $files = @()
  for ($index = 0; $index -lt $Product.imageUrls.Count; $index++) {
    $number = $index + 1
    $url = [string]$Product.imageUrls[$index]
    $files += @{
      originalSource = $url
      filename = Get-ImageFilename $url $Product.sku $number
      contentType = "IMAGE"
      alt = "$($Product.title) - zdjęcie $number"
      duplicateResolutionMode = "REPLACE"
    }
  }
  return $files
}

function Get-ImageFilename {
  param([string]$Url, [string]$Sku, [int]$Number)
  $name = [System.IO.Path]::GetFileName(([uri]$Url).AbsolutePath)
  if ($name) { return $name }
  return "$Sku-$Number.jpg"
}

function New-VariantInput {
  param($Product, [string]$Sku)
  return @{
    sku = $Sku
    barcode = [string]$Product.ean
    price = [string]$Product.price
    taxable = $true
    inventoryPolicy = "DENY"
    optionValues = @(New-DefaultOptionValue)
  }
}

function New-DefaultOptionValue {
  return @{ optionName = "Title"; name = "Default Title" }
}

function New-DefaultProductOption {
  return @{
    name = "Title"
    position = 1
    values = @(@{ name = "Default Title" })
  }
}

function New-ProductSetInput {
  param($Product, [string]$Sku, [string]$Handle)
  $payload = [ordered]@{
    title = [string]$Product.title
    handle = $Handle
    descriptionHtml = [string]$Product.descriptionHtml
    vendor = [string]$Product.vendor
    productType = [string]$Product.productType
    status = "DRAFT"
    tags = @($Product.tags)
    productOptions = @((New-DefaultProductOption))
    files = @(New-ProductFiles $Product)
    variants = @((New-VariantInput $Product $Sku))
  }
  return Remove-EmptyProperties $payload
}

function Remove-EmptyProperties {
  param($Payload)
  $clean = [ordered]@{}
  foreach ($key in $Payload.Keys) {
    $value = $Payload[$key]
    if ($null -eq $value) { continue }
    if ($value -is [string] -and !$value) { continue }
    if ($value -is [array] -and $value.Count -eq 0) { continue }
    $clean[$key] = $value
  }
  return $clean
}

function Sync-ShopifyProduct {
  param($Product, [string]$Sku, [string]$Handle)
  return Invoke-ShopifyProductSet (New-ProductSetInput $Product $Sku $Handle)
}

function Sync-PlanProducts {
  param($Plan)
  $usedSkus = [System.Collections.Generic.HashSet[string]]::new()
  $usedHandles = [System.Collections.Generic.HashSet[string]]::new()
  $items = @()
  foreach ($product in $Plan.products) {
    $sku = Get-UniqueShopifySku ([string]$product.sku) $usedSkus
    $handle = Get-UniqueShopifyHandle ([string]$product.handle) $usedHandles
    $node = Sync-ShopifyProduct $product $sku $handle
    $items += New-SyncItem $product $sku $handle $node
    Write-Host "Created draft: $($node.title) [$sku]"
  }
  return $items
}

function New-SyncItem {
  param($SourceProduct, [string]$Sku, [string]$Handle, $Node)
  [ordered]@{
    sourceSku = [string]$SourceProduct.sku
    shopifySku = $Sku
    handle = $Handle
    productId = [string]$Node.id
    legacyResourceId = [string]$Node.legacyResourceId
    title = [string]$Node.title
    status = [string]$Node.status
    sourceUrl = [string]$SourceProduct.sourceUrl
  }
}

function New-SyncReport {
  param($Plan, $ChildCollection, $Items, $Skipped)
  [ordered]@{
    syncedAt = (Get-Date).ToString("o")
    parentCollectionId = $ParentCollectionId
    childCollection = $ChildCollection
    productCount = @($Items).Count
    skippedWithoutImagesCount = @($Skipped).Count
    skippedWithoutImages = @(New-SkippedItems $Skipped)
    products = @($Items)
    sourceCategoryUrl = [string]$Plan.sourceCategoryUrl
  }
}

function New-SkippedItems {
  param($Products)
  foreach ($product in $Products) {
    [ordered]@{
      sku = [string]$product.sku
      title = [string]$product.title
      sourceUrl = [string]$product.sourceUrl
    }
  }
}

function Save-SyncReport {
  param($Report)
  $Report | ConvertTo-Json -Depth 20 | Set-Content $ReportPath -Encoding UTF8
}

function Main {
  $plan = Read-Plan
  $skipped = Get-ProductsWithoutImages $plan
  $syncPlan = New-FilteredPlan $plan
  Assert-PlanReady $syncPlan
  $child = Ensure-ShopifyCollection $ChildCollectionTitle $ChildCollectionHandle
  $items = Sync-PlanProducts $syncPlan
  $productIds = @($items | ForEach-Object { [string]$_.productId })
  Add-ProductsToCollection $ParentCollectionId $productIds
  Add-ProductsToCollection ([string]$child.id) $productIds
  $report = New-SyncReport $plan $child $items $skipped
  Save-SyncReport $report
  "Saved $ReportPath"
}

Main
