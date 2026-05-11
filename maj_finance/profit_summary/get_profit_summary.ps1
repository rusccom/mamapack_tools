param(
    [datetime]$From = [datetime]::MinValue,
    [datetime]$To = [datetime]::MinValue,
    [string]$CustomerCode = $env:MAJ_CUSTOMER_CODE,
    [string]$UserName = $env:MAJ_USER_NAME,
    [switch]$IncludeRows,
    [switch]$AsJson
)

$ErrorActionPreference = 'Stop'
$BaseUri = [Uri]'https://klient.mf.lublin.pl/'
$LoginUrl = 'https://klient.mf.lublin.pl/login'
$KpirUrl = 'https://klient.mf.lublin.pl/analyzes/kpir'

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
    $text = $Html -replace '<script[\s\S]*?</script>', ' '
    $text = $text -replace '<style[\s\S]*?</style>', ' '
    $text = $text -replace '<[^>]+>', ' '
    return [Net.WebUtility]::HtmlDecode(($text -replace '\s+', ' ').Trim())
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
    return Invoke-WebRequest -Uri $LoginUrl -Method Post -Body $body `
        -Headers @{ Referer = $LoginUrl } -WebSession $Session `
        -MaximumRedirection 5 -UseBasicParsing
}

function Test-LoginFailed {
    param($Response)
    $url = $Response.BaseResponse.ResponseUri.AbsoluteUri
    if ($url -match '/login$') { return $true }
    return $Response.Content -match 'B.?dny login lub has'
}

function Convert-Amount {
    param([string]$Value)
    $clean = ($Value -replace '[^0-9,\.-]', '') -replace ',', '.'
    if ([string]::IsNullOrWhiteSpace($clean)) { return [decimal]0 }
    return [decimal]::Parse($clean, [Globalization.CultureInfo]::InvariantCulture)
}

function Get-CellTexts {
    param([string]$RowHtml)
    foreach ($cell in [regex]::Matches($RowHtml, '<t[dh][\s\S]*?</t[dh]>', 'IgnoreCase')) {
        Convert-HtmlText $cell.Value
    }
}

function New-KpirUrl {
    param([datetime]$From, [datetime]$To)
    $fromText = $From.ToString('yyyy-MM-dd')
    $toText = $To.ToString('yyyy-MM-dd')
    return "${KpirUrl}?time_from=$fromText&time_to=$toText"
}

function Get-KpirRows {
    param([string]$Html)
    foreach ($row in [regex]::Matches($Html, '<tr[\s\S]*?</tr>', 'IgnoreCase')) {
        $cells = @(Get-CellTexts $row.Value)
        if ($cells.Count -lt 10 -or $cells[2] -notmatch '^\d{4}-\d{2}-\d{2}$') { continue }
        New-KpirRow $cells
    }
}

function New-KpirRow {
    param($Cells)
    [pscustomobject]@{
        lp = $Cells[1]
        date = [datetime]::ParseExact($Cells[2], 'yyyy-MM-dd', $null)
        document = $Cells[3]
        contractor = $Cells[4]
        revenue = Convert-Amount $Cells[5]
        expense = Convert-Amount $Cells[6]
        column = $Cells[7]
        description = $Cells[8]
        category = $Cells[9]
    }
}

function Select-PeriodRows {
    param($Rows, [datetime]$From, [datetime]$To)
    foreach ($row in $Rows) {
        if ($row.date -lt $From -or $row.date -gt $To) { continue }
        $row
    }
}

function New-ColumnSummary {
    param($Rows)
    $Rows | Group-Object column | ForEach-Object {
        [pscustomobject]@{
            column = $_.Name
            count = $_.Count
            revenue = [decimal]::Round(($_.Group | Measure-Object revenue -Sum).Sum, 2)
            expense = [decimal]::Round(($_.Group | Measure-Object expense -Sum).Sum, 2)
        }
    } | Sort-Object column
}

function New-ProfitSummary {
    param($Rows, [datetime]$From, [datetime]$To)
    $revenue = [decimal]::Round(($Rows | Measure-Object revenue -Sum).Sum, 2)
    $expense = [decimal]::Round(($Rows | Measure-Object expense -Sum).Sum, 2)
    [pscustomobject]@{
        period_from = $From.ToString('yyyy-MM-dd')
        period_to = $To.ToString('yyyy-MM-dd')
        source = 'KPiR - Ksiega podatkowa'
        records = $Rows.Count
        revenue = $revenue
        expenses = $expense
        profit = [decimal]::Round($revenue - $expense, 2)
        columns = @(New-ColumnSummary $Rows)
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

$kpirPage = Invoke-WebRequest -Uri (New-KpirUrl $From.Date $To.Date) `
    -WebSession $session -UseBasicParsing
$rows = @(Select-PeriodRows (Get-KpirRows $kpirPage.Content) $From.Date $To.Date)
$summary = New-ProfitSummary $rows $From.Date $To.Date

if ($AsJson) {
    if ($IncludeRows) { @{ summary = $summary; rows = $rows } | ConvertTo-Json -Depth 5 }
    else { $summary | ConvertTo-Json -Depth 5 }
    exit 0
}

$summary | Select-Object -ExcludeProperty columns | Format-List
$summary.columns | Format-Table -AutoSize
if ($IncludeRows) {
    $rows | Sort-Object date | Format-Table `
        lp, date, document, contractor, revenue, expense, column, description -AutoSize
}
