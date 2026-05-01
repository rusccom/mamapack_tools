$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseUrl = "https://b2b.marini.pl"
$LoginUrl = "$BaseUrl/login"
$OutputPath = Join-Path $Here "catalog_access.json"

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
  if ($pair.Count -ne 2) { return }
  $Values[$pair[0].Trim()] = $pair[1].Trim().Trim('"').Trim("'")
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
  $args = New-EdgeArgs $Url $port $userData
  $process = Start-Process (Get-EdgePath) $args -WindowStyle Hidden -PassThru
  [pscustomobject]@{ Process = $process; Port = $port; UserData = $userData }
}

function New-EdgeArgs {
  param([string]$Url, [int]$Port, [string]$UserData)
  @(
    "--headless=new",
    "--disable-gpu",
    "--disable-extensions",
    "--no-first-run",
    "--remote-allow-origins=*",
    "--remote-debugging-port=$Port",
    "--user-data-dir=$UserData",
    $Url
  )
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
  $tabs = Wait-CdpTabs $Browser.Port
  $page = $tabs | Where-Object type -eq "page" | Select-Object -First 1
  $socket = [System.Net.WebSockets.ClientWebSocket]::new()
  $socket.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
  [pscustomobject]@{ Socket = $socket; MessageId = 0 }
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
    if (!(Has-Property $message "id")) { continue }
    if ($message.id -eq $Session.MessageId) { return $message }
  }
}

function Has-Property {
  param($Object, [string]$Name)
  return $Object.PSObject.Properties.Name -contains $Name
}

function Send-CdpPayload {
  param($Session, $Payload)
  $json = $Payload | ConvertTo-Json -Depth 40 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
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
  if (Has-Property $result "exceptionDetails") {
    throw ($result.exceptionDetails | ConvertTo-Json -Depth 8)
  }
  return $result.result.result.value
}

function Enable-BrowserRuntime {
  param($Session)
  Invoke-Cdp $Session "Runtime.enable" @{} | Out-Null
  Invoke-Cdp $Session "Page.enable" @{} | Out-Null
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

function Get-DiscoverExpression {
  $script = Get-Content (Join-Path $Here "discover_catalog.js") -Raw
  "$script`ndiscoverMariniCatalog()"
}

function New-AccessReport {
  param($LoginState, $CatalogState)
  [ordered]@{
    checkedAt = (Get-Date).ToString("o")
    baseUrl = $BaseUrl
    loginRoute = "/login"
    loginSelectors = New-LoginSelectors
    loginState = $LoginState
    catalog = $CatalogState
  }
}

function New-LoginSelectors {
  [ordered]@{
    company = "input[name='customerName']"
    employee = "input[name='userName']"
    password = "input[name='password']"
    terms = "input[name='LoginConfirmation']"
    submit = "form button.action.primary-action"
  }
}

function Save-AccessReport {
  param($Report)
  $Report | ConvertTo-Json -Depth 12 | Set-Content $OutputPath -Encoding UTF8
}

function Close-MariniBrowser {
  param($Browser, $Session)
  if ($Session -and (Has-Property $Session "Socket")) { $Session.Socket.Dispose() }
  if (!$Browser) { return }
  if ($Browser.Process -and !$Browser.Process.HasExited) {
    Stop-Process -Id $Browser.Process.Id -Force
  }
  Remove-Item -LiteralPath $Browser.UserData -Recurse -Force -ErrorAction SilentlyContinue
}

$browser = $null
$session = $null

try {
  $secrets = Read-DotEnv (Join-Path $Here ".env")
  $credentials = New-CredentialsJson $secrets
  $browser = New-MariniBrowser $LoginUrl
  $session = Connect-MariniCdp $browser
  Enable-BrowserRuntime $session
  Start-Sleep -Seconds 5
  $loginState = Invoke-BrowserScript $session (Get-LoginExpression $credentials)
  Start-Sleep -Seconds 10
  $catalogState = Invoke-BrowserScript $session (Get-DiscoverExpression)
  Save-AccessReport (New-AccessReport $loginState $catalogState)
  "Saved $OutputPath"
}
finally {
  Close-MariniBrowser $browser $session
}
