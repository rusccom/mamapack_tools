$ShopifyStoreRoot = Split-Path $PSScriptRoot -Parent
$ProjectRoot = Split-Path $ShopifyStoreRoot -Parent

function ConvertTo-ShopifyDescriptionHtml {
  param($Spec)
  $json = $Spec | ConvertTo-Json -Depth 20 -Compress
  return Invoke-ShopifyDescriptionRenderer $json
}

function Invoke-ShopifyDescriptionRenderer {
  param([string]$Json)
  $oldEncoding = $env:PYTHONIOENCODING
  $oldOutput = [Console]::OutputEncoding
  $env:PYTHONIOENCODING = "utf-8"
  [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
  Push-Location $ProjectRoot
  try { return [string](($Json | & py -m shopify_store.products.description_cli) -join "") }
  finally {
    Pop-Location
    Restore-PythonIoEncoding $oldEncoding
    [Console]::OutputEncoding = $oldOutput
  }
}

function Restore-PythonIoEncoding {
  param($Value)
  if ($null -eq $Value) {
    Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
    return
  }
  $env:PYTHONIOENCODING = $Value
}
