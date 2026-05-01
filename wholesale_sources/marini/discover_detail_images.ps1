param([switch]$AllProducts)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseUrl = "https://b2b.marini.pl"
$LoginUrl = "$BaseUrl/login"
$PlanPath = Join-Path $Here "tega_wanny_shopify_plan.json"
$OutputPath = Join-Path $Here "tega_detail_images.json"

function Read-DotEnv {
  param([string]$Path)
  $values = @{}
  if (!(Test-Path $Path)) { return $values }
  foreach ($line in Get-Content $Path) { Add-DotEnvLine $values $line }
  return $values
}

function Add-DotEnvLine {
  param($Values, [string]$Line)
  if ([string]::IsNullOrWhiteSpace($Line)) { return }
  if ($Line.TrimStart().StartsWith("#")) { return }
  $pair = $Line -split "=", 2
  if ($pair.Count -eq 2) { $Values[$pair[0].Trim()] = $pair[1].Trim().Trim('"').Trim("'") }
}

function Get-SecretValue {
  param($Values, [string]$Name)
  $envValue = [Environment]::GetEnvironmentVariable($Name)
  if ($envValue) { return $envValue }
  if ($Values.ContainsKey($Name)) { return $Values[$Name] }
  throw "Missing required value: $Name"
}

function Get-EdgePath {
  $paths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
  )
  foreach ($path in $paths) {
    if (Test-Path $path) { return $path }
  }
  throw "Microsoft Edge was not found."
}

function New-MariniBrowser {
  param([string]$Url)
  $port = Get-Random -Minimum 9300 -Maximum 9900
  $userData = Join-Path $env:TEMP ("marini-edge-" + [guid]::NewGuid())
  $process = Start-Process (Get-EdgePath) (New-EdgeArgs $Url $port $userData) -WindowStyle Hidden -PassThru
  [pscustomobject]@{ Process = $process; Port = $port; UserData = $userData }
}

function New-EdgeArgs {
  param([string]$Url, [int]$Port, [string]$UserData)
  @("--headless=new", "--disable-gpu", "--disable-extensions", "--disable-sync",
    "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*",
    "--remote-debugging-port=$Port", "--user-data-dir=$UserData", $Url)
}

function Wait-CdpTabs {
  param([int]$Port)
  for ($i = 0; $i -lt 40; $i++) {
    try { return Invoke-RestMethod "http://127.0.0.1:$Port/json" }
    catch { Start-Sleep -Milliseconds 500 }
  }
  throw "CDP endpoint is not available."
}

function Connect-MariniCdp {
  param($Browser)
  $page = Wait-MariniPage $Browser.Port
  $socket = [System.Net.WebSockets.ClientWebSocket]::new()
  $socket.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
  [pscustomobject]@{ Socket = $socket; MessageId = 0 }
}

function Wait-MariniPage {
  param([int]$Port)
  for ($i = 0; $i -lt 40; $i++) {
    $tabs = @(Wait-CdpTabs $Port | ForEach-Object { $_ })
    $page = $tabs | Where-Object { Is-MariniTab $_ } | Select-Object -First 1
    if ($page) { return $page }
    $page = $tabs | Where-Object { Is-DebuggableTab $_ } | Select-Object -First 1
    if ($page) { return $page }
    Open-CdpPage $Port
    Start-Sleep -Milliseconds 500
  }
  throw "Browser tab is not available."
}

function Open-CdpPage {
  param([int]$Port)
  try {
    Invoke-RestMethod -Method Put "http://127.0.0.1:$Port/json/new?$LoginUrl" | Out-Null
  }
  catch {}
}

function Is-MariniTab {
  param($Tab)
  if (!(Has-Property $Tab "type") -or $Tab.type -ne "page") { return $false }
  if (!(Has-Property $Tab "url")) { return $false }
  return ([string]$Tab.url).StartsWith($BaseUrl)
}

function Is-DebuggableTab {
  param($Tab)
  if (!(Has-Property $Tab "type") -or $Tab.type -ne "page") { return $false }
  return Has-Property $Tab "webSocketDebuggerUrl"
}

function Receive-CdpMessage {
  param($Session)
  $buffer = New-Object byte[] 1048576
  $stream = [System.IO.MemoryStream]::new()
  do {
    $segment = [ArraySegment[byte]]::new($buffer)
    $result = $Session.Socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).Result
    $stream.Write($buffer, 0, $result.Count)
  } while (!$result.EndOfMessage)
  [Text.Encoding]::UTF8.GetString($stream.ToArray()) | ConvertFrom-Json
}

function Invoke-Cdp {
  param($Session, [string]$Method, $Params)
  $Session.MessageId += 1
  $payload = @{ id = $Session.MessageId; method = $Method }
  if ($Params) { $payload.params = $Params }
  Send-CdpPayload $Session $payload
  while ($true) {
    $message = Receive-CdpMessage $Session
    if ((Has-Property $message "id") -and $message.id -eq $Session.MessageId) { return $message }
  }
}

function Has-Property {
  param($Object, [string]$Name)
  return $Object.PSObject.Properties.Name -contains $Name
}

function Send-CdpPayload {
  param($Session, $Payload)
  $bytes = [Text.Encoding]::UTF8.GetBytes(($Payload | ConvertTo-Json -Depth 40 -Compress))
  $segment = [ArraySegment[byte]]::new($bytes)
  $type = [System.Net.WebSockets.WebSocketMessageType]::Text
  $Session.Socket.SendAsync($segment, $type, $true, [Threading.CancellationToken]::None).Wait()
}

function Invoke-BrowserScript {
  param($Session, [string]$Script)
  $result = Invoke-Cdp $Session "Runtime.evaluate" @{
    expression = $Script
    awaitPromise = $true
    returnByValue = $true
  }
  if (Has-Property $result "exceptionDetails") { throw ($result.exceptionDetails | ConvertTo-Json -Depth 8) }
  return $result.result.result.value
}

function Enable-BrowserRuntime {
  param($Session)
  Invoke-Cdp $Session "Runtime.enable" @{} | Out-Null
  Invoke-Cdp $Session "Page.enable" @{} | Out-Null
}

function Navigate-Browser {
  param($Session, [string]$Url)
  Invoke-Cdp $Session "Page.navigate" @{ url = $Url } | Out-Null
  Start-Sleep -Seconds 9
}

function New-CredentialsJson {
  param($Secrets)
  @{
    company = Get-SecretValue $Secrets "MARINI_COMPANY"
    employee = Get-SecretValue $Secrets "MARINI_EMPLOYEE"
    password = Get-SecretValue $Secrets "MARINI_PASSWORD"
  } | ConvertTo-Json -Compress
}

function Get-LoginExpression {
  param([string]$CredentialsJson)
  $script = Get-Content (Join-Path $Here "login_form.js") -Raw
  "$script`nloginMarini($CredentialsJson)"
}

function Get-DetailExpression {
  $script = Get-Content (Join-Path $Here "detail_images.js") -Raw
  "$script`ncollectMariniDetailPage()"
}

function Get-Targets {
  $plan = Get-Content -Raw -Encoding UTF8 $PlanPath | ConvertFrom-Json
  $products = if ($AllProducts) { $plan.products } else {
    $plan.products | Where-Object { !$_.imageUrls -or $_.imageUrls.Count -eq 0 }
  }
  return @($products | ForEach-Object { New-Target $_ })
}

function New-Target {
  param($Product)
  [ordered]@{
    sku = [string]$Product.sku
    title = [string]$Product.title
    sourceUrl = [string]$Product.sourceUrl
    imageCount = @($Product.imageUrls).Count
  }
}

function Save-Report {
  param($Items)
  [ordered]@{ checkedAt = (Get-Date).ToString("o"); items = @($Items) } |
    ConvertTo-Json -Depth 20 | Set-Content $OutputPath -Encoding UTF8
}

function Close-MariniBrowser {
  param($Browser, $Session)
  if ($Session -and (Has-Property $Session "Socket")) { $Session.Socket.Dispose() }
  if ($Browser -and $Browser.Process -and !$Browser.Process.HasExited) {
    Stop-Process -Id $Browser.Process.Id -Force
  }
  if ($Browser) { Remove-Item -LiteralPath $Browser.UserData -Recurse -Force -ErrorAction SilentlyContinue }
}

$browser = $null
$session = $null

try {
  $secrets = Read-DotEnv (Join-Path $Here ".env")
  $browser = New-MariniBrowser $LoginUrl
  $session = Connect-MariniCdp $browser
  Enable-BrowserRuntime $session
  Navigate-Browser $session $LoginUrl
  Start-Sleep -Seconds 5
  Invoke-BrowserScript $session (Get-LoginExpression (New-CredentialsJson $secrets)) | Out-Null
  Start-Sleep -Seconds 10
  $items = foreach ($target in Get-Targets) {
    Navigate-Browser $session $target.sourceUrl
    $page = Invoke-BrowserScript $session (Get-DetailExpression)
    [ordered]@{ target = $target; page = $page }
  }
  Save-Report $items
  "Saved $OutputPath"
}
finally {
  Close-MariniBrowser $browser $session
}
