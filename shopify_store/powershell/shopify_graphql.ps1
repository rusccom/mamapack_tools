$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Read-ShopifyAccess {
  $domain = [Environment]::GetEnvironmentVariable("SHOPIFY_STORE_DOMAIN")
  $token = [Environment]::GetEnvironmentVariable("SHOPIFY_ADMIN_TOKEN")
  $version = [Environment]::GetEnvironmentVariable("SHOPIFY_API_VERSION")
  $keyPath = Find-ShopifyKeyFile
  if ((!$token -or !$domain) -and $keyPath) {
    $fileAccess = Read-ShopifyKeyFile $keyPath
    if (!$token) { $token = $fileAccess.token }
    if (!$domain) { $domain = $fileAccess.domain }
  }
  if (!$version) { $version = "2026-04" }
  if (!$domain) { $domain = "c1e90d-4.myshopify.com" }
  if (!$token) { throw "Missing SHOPIFY_ADMIN_TOKEN or key.md with Admin API access token." }
  return [pscustomobject]@{ domain = $domain; token = $token; version = $version }
}

function Find-ShopifyKeyFile {
  $candidates = @(
    (Join-Path (Get-Location) "key.md"),
    (Join-Path $PSScriptRoot "key.md"),
    (Join-Path (Split-Path $PSScriptRoot -Parent) "key.md"),
    (Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "key.md")
  )
  foreach ($path in $candidates) {
    if (Test-Path $path) { return $path }
  }
  return ""
}

function Read-ShopifyKeyFile {
  param([string]$Path)
  $lines = Get-Content -Path $Path -Encoding UTF8
  [pscustomobject]@{
    token = Get-ValueAfterLabel $lines "Admin API access token"
    domain = Get-ValueAfterLabel $lines "SHOPIFY_STORE_DOMAIN"
  }
}

function Get-ValueAfterLabel {
  param($Lines, [string]$Label)
  for ($index = 0; $index -lt $Lines.Count; $index++) {
    if ($Lines[$index].Trim() -ne $Label) { continue }
    return Get-NextNonEmptyLine $Lines ($index + 1)
  }
  return ""
}

function Get-NextNonEmptyLine {
  param($Lines, [int]$Start)
  for ($index = $Start; $index -lt $Lines.Count; $index++) {
    $value = $Lines[$index].Trim()
    if ($value) { return $value }
  }
  return ""
}

function Invoke-ShopifyGraphQL {
  param([string]$Query, $Variables)
  $access = Read-ShopifyAccess
  $uri = "https://$($access.domain)/admin/api/$($access.version)/graphql.json"
  $safeVariables = @{}
  if ($null -ne $Variables) { $safeVariables = $Variables }
  $body = @{ query = $Query; variables = $safeVariables } |
    ConvertTo-Json -Depth 80
  $bodyBytes = [Text.Encoding]::UTF8.GetBytes($body)
  $headers = @{
    "X-Shopify-Access-Token" = $access.token
    "Content-Type" = "application/json; charset=utf-8"
  }
  $response = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $bodyBytes -TimeoutSec 120
  if (Has-GraphQLErrors $response) { throw ($response.errors | ConvertTo-Json -Depth 20) }
  return $response.data
}

function Has-GraphQLErrors {
  param($Response)
  if (!($Response.PSObject.Properties.Name -contains "errors")) { return $false }
  return [bool]$Response.errors
}

function Assert-ShopifyUserErrors {
  param($Errors)
  if (!$Errors -or $Errors.Count -eq 0) { return }
  throw ($Errors | ConvertTo-Json -Depth 12)
}

function Search-ShopifyVariantSku {
  param([string]$Sku)
  $query = @'
query VariantBySku($query: String!) {
  productVariants(first: 1, query: $query) {
    nodes { id sku product { id title handle } }
  }
}
'@
  $safe = $Sku.Replace("\", "\\").Replace("'", "\'")
  $data = Invoke-ShopifyGraphQL $query @{ query = "sku:'$safe'" }
  return @($data.productVariants.nodes)
}

function Search-ShopifyProductHandle {
  param([string]$Handle)
  $query = @'
query ProductByHandle($query: String!) {
  products(first: 1, query: $query) {
    nodes { id handle title }
  }
}
'@
  $safe = $Handle.Replace("\", "\\").Replace("'", "\'")
  $data = Invoke-ShopifyGraphQL $query @{ query = "handle:'$safe'" }
  return @($data.products.nodes)
}

function Get-UniqueShopifySku {
  param([string]$BaseSku, $UsedSkus)
  $index = 1
  while ($true) {
    $candidate = New-SuffixedValue $BaseSku $index 40
    if (!$UsedSkus.Contains($candidate) -and !(Search-ShopifyVariantSku $candidate)) {
      [void]$UsedSkus.Add($candidate)
      return $candidate
    }
    $index += 1
  }
}

function Get-UniqueShopifyHandle {
  param([string]$BaseHandle, $UsedHandles)
  $index = 1
  while ($true) {
    $candidate = New-SuffixedValue $BaseHandle $index 120
    if (!$UsedHandles.Contains($candidate) -and !(Search-ShopifyProductHandle $candidate)) {
      [void]$UsedHandles.Add($candidate)
      return $candidate
    }
    $index += 1
  }
}

function New-SuffixedValue {
  param([string]$Base, [int]$Index, [int]$Limit)
  if ($Index -eq 1) { return $Base.Substring(0, [Math]::Min($Base.Length, $Limit)) }
  $suffix = "-$Index"
  $rootLimit = [Math]::Max(1, $Limit - $suffix.Length)
  $root = $Base.Substring(0, [Math]::Min($Base.Length, $rootLimit)).TrimEnd("-")
  return "$root$suffix"
}

function Get-ShopifyCollectionByHandle {
  param([string]$Handle)
  $query = @'
query CollectionByHandle($query: String!) {
  collections(first: 1, query: $query) {
    nodes { id title handle }
  }
}
'@
  $data = Invoke-ShopifyGraphQL $query @{ query = "handle:$Handle" }
  return @($data.collections.nodes) | Select-Object -First 1
}

function New-ShopifyCollection {
  param([string]$Title, [string]$Handle)
  $mutation = @'
mutation CreateCollection($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id title handle }
    userErrors { field message }
  }
}
'@
  $input = @{ title = $Title; handle = $Handle }
  $result = Invoke-ShopifyGraphQL $mutation @{ input = $input }
  Assert-ShopifyUserErrors $result.collectionCreate.userErrors
  return $result.collectionCreate.collection
}

function Ensure-ShopifyCollection {
  param([string]$Title, [string]$Handle)
  $collection = Get-ShopifyCollectionByHandle $Handle
  if ($collection) { return $collection }
  return New-ShopifyCollection $Title $Handle
}

function Add-ProductsToCollection {
  param([string]$CollectionId, [string[]]$ProductIds)
  if (!$ProductIds -or $ProductIds.Count -eq 0) { return }
  $mutation = @'
mutation AddProductsToCollection($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    collection { id title handle }
    userErrors { field message }
  }
}
'@
  $result = Invoke-ShopifyGraphQL $mutation @{ id = $CollectionId; productIds = $ProductIds }
  Assert-ShopifyUserErrors $result.collectionAddProducts.userErrors
}

function Invoke-ShopifyProductSet {
  param($Input)
  $mutation = @'
mutation ProductSetSync($input: ProductSetInput!, $synchronous: Boolean!) {
  productSet(input: $input, synchronous: $synchronous) {
    product {
      id
      legacyResourceId
      handle
      title
      status
      variants(first: 10) {
        nodes { id sku barcode price }
      }
    }
    userErrors { field message }
  }
}
'@
  $result = Invoke-ShopifyGraphQL $mutation @{ input = $Input; synchronous = $true }
  Assert-ShopifyUserErrors $result.productSet.userErrors
  return $result.productSet.product
}

function Update-ShopifyProductSeo {
  param([string]$ProductId, [string]$Handle, [string]$SeoTitle, [string]$SeoDescription)
  $mutation = @'
mutation UpdateProductSeo($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product {
      id
      handle
      seo { title description }
    }
    userErrors { field message }
  }
}
'@
  $input = New-ShopifySeoInput $ProductId $Handle $SeoTitle $SeoDescription
  $result = Invoke-ShopifyGraphQL $mutation @{ product = $input }
  Assert-ShopifyUserErrors $result.productUpdate.userErrors
  return $result.productUpdate.product
}

function New-ShopifySeoInput {
  param([string]$ProductId, [string]$Handle, [string]$SeoTitle, [string]$SeoDescription)
  return @{
    id = $ProductId
    handle = $Handle
    seo = @{ title = $SeoTitle; description = $SeoDescription }
  }
}
