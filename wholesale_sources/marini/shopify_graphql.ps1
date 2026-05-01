$ProjectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$SharedShopify = Join-Path $ProjectRoot "shopify_store\powershell\shopify_graphql.ps1"
. $SharedShopify
