param(
    [datetime]$From = [datetime]::MinValue,
    [datetime]$To = [datetime]::MinValue,
    [ValidateSet('AccountingMonth', 'SellDate', 'IssueDate', 'RegistrationDate')]
    [string]$DateField = 'AccountingMonth',
    [string]$CustomerCode = $env:MAJ_CUSTOMER_CODE,
    [string]$UserName = $env:MAJ_USER_NAME,
    [switch]$IncludeRows,
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'
$BaseUri = [Uri]'https://klient.mf.lublin.pl/'
$LoginUrl = 'https://klient.mf.lublin.pl/login'
$InvoicesUrl = 'https://klient.mf.lublin.pl/invoices/buy'

function Get-DefaultFrom {
    $first = Get-Date -Day 1 -Hour 0 -Minute 0 -Second 0
    return $first.AddMonths(-1).Date
}

function Get-DefaultTo {
    $first = Get-Date -Day 1 -Hour 0 -Minute 0 -Second 0
    return $first.AddDays(-1).Date
}

function Ensure-Value {
    param([string]$Value, [string]$Prompt)
    if (-not [string]::IsNullOrWhiteSpace($Value)) { return $Value }
    return Read-Host $Prompt
}

function Read-PlainPassword {
    param([string]$Prompt)
    $secure = Read-Host $Prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Get-ProjectRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Read-PasswordFile {
    foreach ($name in @('kk', 'key', 'key.md')) {
        $path = Join-Path (Get-ProjectRoot) $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        $password = Convert-KeyTextToPassword (Get-Content -LiteralPath $path -Raw) $name
        if ($password) { return $password }
    }
    return ''
}

function Convert-KeyTextToPassword {
    param([string]$Text, [string]$Name)
    $lines = @($Text -split '\r?\n' | ForEach-Object { $_.Trim() })
    if ($Name -ne 'key.md' -and $lines.Count -eq 1) { return $lines[0] }
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^(MAJ[\s_-]*)?(PASSWORD|PASS|HASLO|HASŁO)\s*[:=]\s*(.+)$') {
            return $Matches[3].Trim()
        }
        if ($lines[$i] -match '^MAJ.*(PASSWORD|PASS|HASLO|HASŁO)\s*$') {
            return Next-NonEmptyLine $lines ($i + 1)
        }
    }
    return ''
}

function Next-NonEmptyLine {
    param($Lines, [int]$Start)
    for ($i = $Start; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i]) { return $Lines[$i] }
    }
    return ''
}

function Get-LoginPassword {
    if ($env:MAJ_PASSWORD) { return $env:MAJ_PASSWORD }
    $filePassword = Read-PasswordFile
    if ($filePassword) { return $filePassword }
    return Read-PlainPassword 'Haslo'
}

function Convert-HtmlText {
    param([string]$Html)
    $text = $Html -replace '<[^>]+>', ' '
    $text = $text -replace '\s+', ' '
    return [Net.WebUtility]::HtmlDecode($text).Trim()
}

function Get-CsrfToken {
    param([string]$Html)
    $match = [regex]::Match($Html, 'name="_token"\s+value="([^"]+)"')
    if (-not $match.Success) { throw 'CSRF token was not found.' }
    return $match.Groups[1].Value
}

function Invoke-Login {
    param($Session, [string]$Token, [string]$Code, [string]$Name, [string]$Password)
    $body = @{ _token = $Token; customer_code = $Code; name = $Name; password = $Password }
    $headers = @{ Referer = $LoginUrl }
    return Invoke-WebRequest -Uri $LoginUrl -Method Post -Body $body `
        -Headers $headers -WebSession $Session -MaximumRedirection 5 -UseBasicParsing
}

function Test-LoginFailed {
    param($Response)
    $url = $Response.BaseResponse.ResponseUri.AbsoluteUri
    if ($url -match '/login$') { return $true }
    return $Response.Content -match 'B.?dny login lub has'
}

function Resolve-Url {
    param([string]$Href)
    if ([string]::IsNullOrWhiteSpace($Href)) { return $null }
    return ([Uri]::new($BaseUri, $Href)).AbsoluteUri
}

function Convert-PolishDate {
    param([string]$Value)
    $date = ($Value -split '\s+-\s+')[0].Trim()
    return [datetime]::ParseExact($date, 'dd.MM.yyyy', $null)
}

function Convert-Amount {
    param([string]$Value)
    $clean = ($Value -replace '\s', '') -replace ',', '.'
    return [decimal]::Parse($clean, [Globalization.CultureInfo]::InvariantCulture)
}

function Get-CellTexts {
    param([string]$RowHtml)
    foreach ($cell in [regex]::Matches($RowHtml, '<td[\s\S]*?</td>', 'IgnoreCase')) {
        Convert-HtmlText $cell.Value
    }
}

function Get-InvoiceRows {
    param([string]$Html)
    $pattern = '<tr[^>]+data-href=["'']([^"'']*/invoices/(\d+)[^"'']*)["''][^>]*>([\s\S]*?)</tr>'
    foreach ($match in [regex]::Matches($Html, $pattern, 'IgnoreCase')) {
        $cells = @(Get-CellTexts $match.Groups[3].Value)
        if ($cells.Count -lt 11) { continue }
        New-InvoiceRow $match $cells
    }
}

function New-InvoiceRow {
    param($Match, $Cells)
    [pscustomobject]@{
        id = $Cells[2]
        detail_url = Resolve-Url $Match.Groups[1].Value
        number = $Cells[3]
        registration_date = Convert-PolishDate $Cells[4]
        issue_date = Convert-PolishDate $Cells[5]
        contractor = $Cells[6]
        city = $Cells[7]
        net = Convert-Amount $Cells[8]
        vat = Convert-Amount $Cells[9]
        gross = Convert-Amount $Cells[10]
    }
}

function Get-SellDate {
    param($Row, $Session)
    $detail = Invoke-WebRequest -Uri $Row.detail_url -WebSession $Session -UseBasicParsing
    $pattern = 'name="sell_date"[^>]*value="([^"]+)"'
    $match = [regex]::Match($detail.Content, $pattern, 'IgnoreCase')
    if ($match.Success) { return [datetime]::Parse($match.Groups[1].Value) }
    return $Row.issue_date
}

function Get-ScanRange {
    param([datetime]$From, [datetime]$To, [string]$DateField)
    if ($DateField -ne 'SellDate') { return @($From, $To) }
    $scanTo = [datetime]::Today
    if ($To -gt $scanTo) { $scanTo = $To }
    return @($From.AddDays(-7), $scanTo)
}

function New-ListUrl {
    param([datetime]$From, [datetime]$To, [int]$Page, [string]$DateField, [string]$Status)
    $fromText = $From.ToString('yyyy-MM-dd')
    $toText = $To.ToString('yyyy-MM-dd')
    $dateQuery = Get-DateQuery $DateField $fromText $toText
    $statusQuery = if ($Status) { "&filtr_status=$Status" } else { '' }
    return "${InvoicesUrl}?$dateQuery$statusQuery&page=$Page"
}

function Get-DateQuery {
    param([string]$DateField, [string]$From, [string]$To)
    if ($DateField -eq 'RegistrationDate' -or $DateField -eq 'AccountingMonth') {
        return "created_at_min=$From&created_at_max=$To"
    }
    return "filtr_odDnia=$From&filtr_doDnia=$To"
}

function Get-AllRows {
    param($Session, [datetime]$ScanFrom, [datetime]$ScanTo, [string]$DateField, [string]$Status)
    $rows = @()
    for ($page = 1; $page -lt 100; $page++) {
        $batch = @(Get-PageRows $Session $ScanFrom $ScanTo $page $DateField $Status)
        if ($batch.Count -eq 0) { break }
        $rows += $batch
    }
    return $rows
}

function Get-PageRows {
    param($Session, [datetime]$ScanFrom, [datetime]$ScanTo, [int]$Page, [string]$DateField, [string]$Status)
    $url = New-ListUrl $ScanFrom $ScanTo $Page $DateField $Status
    $pageHtml = (Invoke-WebRequest -Uri $url -WebSession $Session -UseBasicParsing).Content
    return @(Get-InvoiceRows $pageHtml)
}

function Get-AllRowCount {
    param($Session, [datetime]$ScanFrom, [datetime]$ScanTo, [string]$DateField, [string]$Status)
    $count = 0
    for ($page = 1; $page -lt 100; $page++) {
        $url = New-ListUrl $ScanFrom $ScanTo $page $DateField $Status
        $html = (Invoke-WebRequest -Uri $url -WebSession $Session -UseBasicParsing).Content
        $batch = ([regex]::Matches($html, '<tr[^>]+data-href=["''][^"'']*/invoices/\d+', 'IgnoreCase')).Count
        if ($batch -eq 0) { break }
        $count += $batch
    }
    return $count
}

function Get-RowDate {
    param($Row, $Session, [string]$DateField)
    if ($DateField -eq 'IssueDate') { return $Row.issue_date }
    if ($DateField -eq 'RegistrationDate') { return $Row.registration_date }
    if ($DateField -eq 'AccountingMonth') { return $Row.registration_date }
    return Get-SellDate $Row $Session
}

function Select-PeriodRows {
    param($Rows, $Session, [datetime]$From, [datetime]$To, [string]$DateField)
    foreach ($row in $Rows) {
        $date = Get-RowDate $row $Session $DateField
        if ($date -lt $From -or $date -gt $To) { continue }
        $row | Add-Member -NotePropertyName period_date -NotePropertyValue $date -Force
        $row
    }
}

function New-Summary {
    param($Rows, [datetime]$From, [datetime]$To, [string]$DateField, [int]$Scanned, [int]$Added, [int]$Deleted)
    $net = [decimal]::Round(($Rows | Measure-Object -Property net -Sum).Sum, 2)
    $vat = [decimal]::Round(($Rows | Measure-Object -Property vat -Sum).Sum, 2)
    $gross = [decimal]::Round(($Rows | Measure-Object -Property gross -Sum).Sum, 2)
    [pscustomobject]@{
        period_from = $From.ToString('yyyy-MM-dd')
        period_to = $To.ToString('yyyy-MM-dd')
        date_field = $DateField
        status = 'Wszystkie bez usunietych i anulowanych'
        added_documents = $Added
        deleted_documents = $Deleted
        invoices = $Rows.Count
        total_net = $net
        total_vat = $vat
        total_gross = $gross
        scanned_rows = $Scanned
    }
}

if ($From -eq [datetime]::MinValue) { $From = Get-DefaultFrom }
if ($To -eq [datetime]::MinValue) { $To = Get-DefaultTo }

$CustomerCode = Ensure-Value $CustomerCode 'Identyfikator firmy'
$UserName = Ensure-Value $UserName 'Uzytkownik'
$password = Get-LoginPassword

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$loginPage = Invoke-WebRequest -Uri $LoginUrl -WebSession $session -UseBasicParsing
$login = Invoke-Login $session (Get-CsrfToken $loginPage.Content) $CustomerCode $UserName $password
if (Test-LoginFailed $login) { throw 'Login failed. Check customer code, user name, or password.' }

$scan = Get-ScanRange $From.Date $To.Date $DateField
$filterDateField = if ($DateField -eq 'AccountingMonth') { 'RegistrationDate' } else { $DateField }
$addedCount = Get-AllRowCount $session $scan[0] $scan[1] $filterDateField ''
$deletedCount = (Get-AllRowCount $session $scan[0] $scan[1] $filterDateField '3') + (Get-AllRowCount $session $scan[0] $scan[1] $filterDateField '4')
$allRows = @()
foreach ($status in @('1', '2', '5', '6', '7')) { $allRows += @(Get-AllRows $session $scan[0] $scan[1] $filterDateField $status) }
$periodRows = @(Select-PeriodRows $allRows $session $From.Date $To.Date $DateField)
$summary = New-Summary $periodRows $From.Date $To.Date $DateField $allRows.Count $addedCount $deletedCount

if ($AsJson) {
    if ($IncludeRows) { @{ summary = $summary; rows = $periodRows } | ConvertTo-Json -Depth 5 }
    else { $summary | ConvertTo-Json -Depth 5 }
    exit 0
}

$summary | Format-List
if ($IncludeRows) {
    $periodRows | Sort-Object period_date | Format-Table `
        id, number, period_date, contractor, net, vat, gross -AutoSize
}
