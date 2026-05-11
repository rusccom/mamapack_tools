$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path (Split-Path $Here -Parent) -Parent
$KeyPath = Join-Path $ProjectRoot "key.md"
$OutputPath = Join-Path $Here "forbaby_wozki_live_extract.json"

function Read-KeyValues {
  param([string]$Path)
  $values = @{}
  if (!(Test-Path $Path)) { return $values }
  foreach ($line in Get-Content $Path) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) { continue }
    $pair = $line -split "=", 2
    if ($pair.Count -eq 2) { $values[$pair[0].Trim()] = $pair[1].Trim().Trim('"').Trim("'") }
  }
  return $values
}

function Get-Value {
  param($Values, [string]$Name, [string]$Default = "")
  $envValue = [Environment]::GetEnvironmentVariable($Name)
  if ($envValue) { return $envValue }
  if ($Values.ContainsKey($Name)) { return $Values[$Name] }
  if ($Default) { return $Default }
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
  throw "Browser executable was not found."
}

function New-Browser {
  param([string]$Url)
  $port = Get-Random -Minimum 9300 -Maximum 9900
  $userData = Join-Path $env:TEMP ("marini-edge-" + [guid]::NewGuid())
  $args = @(
    "--headless=new", "--disable-gpu", "--disable-extensions", "--disable-sync",
    "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*",
    "--remote-debugging-port=$port", "--user-data-dir=$userData", $Url
  )
  $process = Start-Process (Get-EdgePath) $args -WindowStyle Hidden -PassThru
  [pscustomobject]@{ Process = $process; Port = $port; UserData = $userData }
}

function Wait-CdpTabs {
  param([int]$Port)
  for ($i = 0; $i -lt 40; $i++) {
    try { return Invoke-RestMethod "http://127.0.0.1:$Port/json" }
    catch { Start-Sleep -Milliseconds 500 }
  }
  throw "CDP endpoint is not available."
}

function Connect-Cdp {
  param($Browser)
  $tabs = Wait-CdpTabs $Browser.Port
  $page = $tabs | Where-Object { $_.type -eq "page" } | Select-Object -First 1
  $socket = [System.Net.WebSockets.ClientWebSocket]::new()
  $socket.ConnectAsync([uri]$page.webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
  [pscustomobject]@{ Socket = $socket; MessageId = 0 }
}

function Has-Property {
  param($Object, [string]$Name)
  $Object.PSObject.Properties.Name -contains $Name
}

function Send-CdpPayload {
  param($Session, $Payload)
  $bytes = [Text.Encoding]::UTF8.GetBytes(($Payload | ConvertTo-Json -Depth 40 -Compress))
  $segment = [ArraySegment[byte]]::new($bytes)
  $type = [System.Net.WebSockets.WebSocketMessageType]::Text
  $Session.Socket.SendAsync($segment, $type, $true, [Threading.CancellationToken]::None).Wait()
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

function Navigate-Browser {
  param($Session, [string]$Url)
  Invoke-Cdp $Session "Page.navigate" @{ url = $Url } | Out-Null
  Start-Sleep -Seconds 8
}

function Login-Expression {
  param([string]$CredentialsJson)
  $loginScript = Get-Content (Join-Path $Here "login_form.js") -Raw
  "$loginScript`nloginMarini($CredentialsJson)"
}

function Credentials-Json {
  param($Secrets)
  @{
    company = Get-Value $Secrets "MARINI_COMPANY"
    employee = Get-Value $Secrets "MARINI_EMPLOYEE"
    password = Get-Value $Secrets "MARINI_PASSWORD"
  } | ConvertTo-Json -Compress
}

function Extract-Expression {
@'
(async function collect4BabyWozki() {
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const text = value => (value || "").replace(/\s+/g, " ").trim();
  await sleep(2000);
  const links = [...document.querySelectorAll("a[href*='/items/']")].map(anchor => {
    const url = new URL(anchor.href);
    const groupId = Number((url.pathname.match(/\/items\/(\d+)/) || [])[1] || 0);
    return { text: text(anchor.innerText), href: anchor.href, route: url.pathname + url.search, groupId };
  }).filter(item => item.text && item.groupId);
  const selected = links.filter(item => /(COSMO|RAPID|STINGER|SINGER|TWEETY)/i.test(item.text));
  const wozki = links.find(item => item.groupId === 12) || links.find(item => /^W/i.test(item.text));
  const sourceLinks = selected.length ? selected : (wozki ? [wozki] : []);
  const unique = [...new Map(sourceLinks.map(item => [item.groupId, item])).values()];
  const groups = [];
  for (const category of unique) {
    const articleList = [];
    const pages = [];
    for (let page = 1, total = 1; page <= total; page++) {
      const url = `/api/items/articleListXl/?groupId=${category.groupId}&filterInGroup=false&pageNumber=${page}&sortMode=NameAsc&onlyAvailable=false&warehouseId=1&stockLevelFilter=0`;
      const response = await fetch(url, { credentials: "include" });
      const json = response.ok ? await response.json() : null;
      pages.push({ url, ok: response.ok, status: response.status, json });
      if (!json) continue;
      articleList.push(...(json.articleList || []));
      total = json.paging?.totalPages || 1;
    }
    const details = [];
    for (const item of articleList) {
      const id = item.article?.id;
      if (!id) continue;
      const url = `/api/items/articleFromListXl/?articleId=${id}&warehouseId=1`;
      const response = await fetch(url, { credentials: "include" });
      details.push({ id, url, ok: response.ok, status: response.status, json: response.ok ? await response.json() : null });
    }
    groups.push({ category, pages, articleList, details });
  }
  return { url: location.href, links, selectedCategories: unique, groups };
})()
'@
}

function Close-Browser {
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
  $secrets = Read-KeyValues $KeyPath
  $baseUrl = Get-Value $secrets "MARINI_BASE_URL" "https://b2b.marini.pl"
  $browser = New-Browser "$baseUrl/login"
  $session = Connect-Cdp $browser
  Invoke-Cdp $session "Runtime.enable" @{} | Out-Null
  Invoke-Cdp $session "Page.enable" @{} | Out-Null
  Navigate-Browser $session "$baseUrl/login"
  Invoke-BrowserScript $session (Login-Expression (Credentials-Json $secrets)) | Out-Null
  Start-Sleep -Seconds 8
  Navigate-Browser $session "$baseUrl/items/10?parent=0"
  $extract = Invoke-BrowserScript $session (Extract-Expression)
  [ordered]@{
    checkedAt = (Get-Date).ToString("o")
    sourceUrl = "$baseUrl/items/10?parent=0"
    extract = $extract
  } | ConvertTo-Json -Depth 80 | Set-Content $OutputPath -Encoding UTF8
  "Saved $OutputPath"
}
finally {
  Close-Browser $browser $session
}
