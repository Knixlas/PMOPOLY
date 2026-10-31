<#
.SYNOPSIS
    Skapar individuella Outlook-utkast till alla mottagare i L_mottagare.csv.

.DESCRIPTION
    For varje rad i L_mottagare.csv:
      - Laser mailtexten ur Valkomstbrev.docx
      - Byter ut {Fornamn}, {Roll}, {JV_Namn} mot personens varden
      - Bifogar tre filer: individuellt brev, verksamhetsplan, roll-CV
      - Sparar som UTKAST i Outlook (skickas inte)

    Stoppar och rapporterar om nagon bilaga saknas.
#>

param(
    [switch]$TestOne,
    [string]$OnlyId,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# === Konfiguration ===
$ScriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$CsvPath        = Join-Path $ScriptDir 'L_mottagare.csv'
$BrevDocxPath   = Join-Path $ScriptDir 'Välkomstbrev.docx'
$PlanerDir      = Join-Path $ScriptDir 'planer'
$ErbjudandeDir  = Join-Path $ScriptDir 'Välkomstbrev'
$Subject        = 'Välkommen till ÅKEPOL - din roll på konferensen 8 maj'
$SenderAccount  = 'niklas.sviden@akesundvall.se'

Write-Host ""
Write-Host "=== ÅKEPOL utkasts-generator ===" -ForegroundColor Cyan
Write-Host "Skript-mapp:   $ScriptDir"
Write-Host "CSV:           $CsvPath"
Write-Host "Mailtext:      $BrevDocxPath"
Write-Host ""

# === Lasa mailtexten direkt ur .docx (zip med XML) - inget Word behovs ===
function Get-DocxText {
    param([string]$Path)
    if (-not (Test-Path $Path)) { throw "Hittar inte $Path" }
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $entry = $zip.Entries | Where-Object { $_.FullName -eq 'word/document.xml' } | Select-Object -First 1
        if (-not $entry) { throw "Hittar inte word/document.xml i $Path" }
        $reader = New-Object System.IO.StreamReader($entry.Open(), [System.Text.Encoding]::UTF8)
        try { $xmlText = $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $zip.Dispose() }

    [xml]$xml = $xmlText
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    $paragraphs = @()
    foreach ($p in $xml.SelectNodes('//w:p', $ns)) {
        $parts = @()
        foreach ($t in $p.SelectNodes('.//w:t', $ns)) { $parts += $t.InnerText }
        $paragraphs += ($parts -join '')
    }
    return ($paragraphs -join "`r`n")
}

Write-Host "Laser mailtext ur Valkomstbrev.docx ..." -ForegroundColor DarkGray
$MailMallText = Get-DocxText -Path $BrevDocxPath
Write-Host "  ($($MailMallText.Length) tecken)" -ForegroundColor DarkGray
Write-Host ""

# === Lasa CSV (cp1252) - manuell lasning fungerar i bade PS 5.1 och 7 ===
if (-not (Test-Path $CsvPath)) { throw "Hittar inte $CsvPath" }
$csvText = [System.IO.File]::ReadAllText($CsvPath, [System.Text.Encoding]::GetEncoding(1252))
$mottagare = $csvText | ConvertFrom-Csv -Delimiter ';'
Write-Host "Hittade $($mottagare.Count) mottagare i CSV." -ForegroundColor Green

if ($OnlyId) {
    $mottagare = @($mottagare | Where-Object { $_.ID -eq $OnlyId })
    if ($mottagare.Count -eq 0) { throw "Ingen mottagare med ID '$OnlyId' hittades" }
    Write-Host "Filtrerat till ID=$OnlyId" -ForegroundColor Yellow
} elseif ($TestOne) {
    $mottagare = @($mottagare | Select-Object -First 1)
    Write-Host "TestOne: bara forsta mottagaren ($($mottagare[0].Namn))" -ForegroundColor Yellow
}

# === Bygg jobblista och verifiera bilagor ===
Write-Host ""
Write-Host "Verifierar bilagor ..." -ForegroundColor DarkGray

$jobs = @()
$saknas = @()

foreach ($m in $mottagare) {
    $id      = $m.ID.Trim()
    $roll    = $m.Roll.Trim()
    $namn    = $m.Namn.Trim()
    $fornamn = $m.'Förnamn'.Trim()
    $jvNamn  = $m.JV_Namn.Trim()
    $mail    = $m.mailadress.Trim()

    $brevPath = Join-Path $ErbjudandeDir ("erbjudande {0}.pdf" -f $namn)
    $vpPath   = Join-Path $PlanerDir     ("{0} - Verksamhetsplan.pdf" -f $jvNamn)
    $cvPath   = Join-Path $ScriptDir     ("CV {0}.pdf" -f $roll)

    foreach ($pair in @(
        @{ Typ='Valkomstbrev';     Path=$brevPath },
        @{ Typ='Verksamhetsplan';  Path=$vpPath   },
        @{ Typ='CV';               Path=$cvPath   }
    )) {
        if (-not (Test-Path $pair.Path)) {
            $saknas += [PSCustomObject]@{ ID=$id; Namn=$namn; Typ=$pair.Typ; Path=$pair.Path }
        }
    }

    $jobs += [PSCustomObject]@{
        ID=$id; Namn=$namn; Fornamn=$fornamn; Roll=$roll; JV_Namn=$jvNamn; Mail=$mail
        Brev=$brevPath; VP=$vpPath; CV=$cvPath
    }
}

if ($saknas.Count -gt 0) {
    Write-Host ""
    Write-Host "STOPP - foljande $($saknas.Count) bilagor saknas:" -ForegroundColor Red
    $saknas | Format-Table -AutoSize
    exit 1
}
Write-Host "  Alla bilagor OK for $($jobs.Count) mottagare." -ForegroundColor Green

# === DryRun ===
if ($DryRun) {
    Write-Host ""
    Write-Host "=== DRY RUN - inga utkast skapas ===" -ForegroundColor Yellow
    foreach ($j in $jobs) {
        Write-Host ""
        Write-Host "--- $($j.ID): $($j.Namn) ($($j.Roll), $($j.JV_Namn)) ---" -ForegroundColor Cyan
        Write-Host "  Till:        $($j.Mail)"
        Write-Host "  Bilagor:"
        Write-Host "    $($j.Brev)"
        Write-Host "    $($j.VP)"
        Write-Host "    $($j.CV)"
        $body = $MailMallText -replace '\{Förnamn\}', $j.Fornamn -replace '\{Roll\}', $j.Roll -replace '\{JV_Namn\}', $j.JV_Namn
        Write-Host "  Mailtext:" -ForegroundColor DarkGray
        ($body -split "`r`n") | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    }
    Write-Host ""
    Write-Host "Klart (DryRun)." -ForegroundColor Yellow
    exit 0
}

# === Outlook ===
Write-Host ""
Write-Host "Ansluter till Outlook ..." -ForegroundColor DarkGray

# Forsta: forsok hamta redan korande Outlook-instans (sa vi far dess konton).
# Om ingen kor, starta en ny.
$outlook = $null
try {
    $outlook = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
    Write-Host "  Anvander redan korande Outlook-instans." -ForegroundColor DarkGray
} catch {
    Write-Host "  Ingen Outlook korde - startar ny instans." -ForegroundColor DarkGray
    $outlook = New-Object -ComObject Outlook.Application
}

# Sakerstall att vi har en MAPI-session med profil
try {
    $ns = $outlook.GetNamespace('MAPI')
    $ns.Logon($null, $null, $false, $false) | Out-Null
} catch {
    Write-Host "  (MAPI-logon hoppade over: $_)" -ForegroundColor DarkGray
}
$olMailItem  = 0
$olFormatHTML = 2
$olFolderDrafts = 16

# Lista alla tillgangliga konton
Write-Host ""
Write-Host "Tillgangliga Outlook-konton:" -ForegroundColor DarkGray
$idx = 0
foreach ($a in $outlook.Session.Accounts) {
    Write-Host ("  [{0}] SmtpAddress='{1}'  DisplayName='{2}'  UserName='{3}'" -f $idx, $a.SmtpAddress, $a.DisplayName, $a.UserName) -ForegroundColor DarkGray
    $idx++
}
Write-Host ""

$account = $null
foreach ($a in $outlook.Session.Accounts) {
    if ($a.SmtpAddress -ieq $SenderAccount -or $a.UserName -ieq $SenderAccount -or $a.DisplayName -ieq $SenderAccount) {
        $account = $a; break
    }
}
if (-not $account) {
    # Fallback: matcha pa del av strangen (t.ex. om DisplayName ar "Niklas Sviden" istallet)
    foreach ($a in $outlook.Session.Accounts) {
        if (($a.SmtpAddress -and $a.SmtpAddress.ToLower().Contains('niklas.sviden')) -or
            ($a.UserName    -and $a.UserName.ToLower().Contains('niklas.sviden'))) {
            $account = $a
            Write-Host "Hittade ungefarlig matchning pa SmtpAddress=$($a.SmtpAddress)" -ForegroundColor Yellow
            break
        }
    }
}
if (-not $account) {
    Write-Host ""
    Write-Host "STOPP - hittar inget Outlook-konto som matchar '$SenderAccount'." -ForegroundColor Red
    Write-Host "Lagg till kontot i Classic Outlook (Arkiv -> Kontoinstallningar) och kor om," -ForegroundColor Red
    Write-Host "eller andra `$SenderAccount overst i skriptet till en av adresserna ovan." -ForegroundColor Red
    exit 1
}
Write-Host "Avsandarkonto: $($account.SmtpAddress)" -ForegroundColor Green

# Hamta Drafts-mappen for det specifika kontot
$draftsFolder = $null
try {
    $draftsFolder = $account.DeliveryStore.GetDefaultFolder($olFolderDrafts)
    Write-Host "Drafts-mapp: $($draftsFolder.FolderPath)" -ForegroundColor Green
} catch {
    Write-Host "Kunde inte hitta kontots egen Drafts-mapp - utkast hamnar i default-kontots Utkast." -ForegroundColor Yellow
}

$skapade = 0
foreach ($j in $jobs) {
    $body = $MailMallText -replace '\{Förnamn\}', $j.Fornamn -replace '\{Roll\}', $j.Roll -replace '\{JV_Namn\}', $j.JV_Namn

    $htmlBody = '<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;">'
    foreach ($line in ($body -split "`r`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            $htmlBody += '<p>&nbsp;</p>'
        } else {
            $esc = $line -replace '&','&amp;' -replace '<','&lt;' -replace '>','&gt;'
            $htmlBody += "<p style=`"margin:0 0 10px 0;`">$esc</p>"
        }
    }
    $htmlBody += '</div>'

    $mail = $outlook.CreateItem($olMailItem)
    $mail.To       = $j.Mail
    $mail.Subject  = $Subject
    $mail.BodyFormat = $olFormatHTML
    $mail.HTMLBody = $htmlBody
    $mail.SendUsingAccount = $account

    $mail.Attachments.Add($j.Brev) | Out-Null
    $mail.Attachments.Add($j.VP)   | Out-Null
    $mail.Attachments.Add($j.CV)   | Out-Null

    $mail.Save()

    # Flytta till ratt kontos Drafts-mapp
    if ($draftsFolder) {
        try { [void]$mail.Move($draftsFolder) } catch { }
    }

    Write-Host "  [OK] $($j.ID)  $($j.Namn)  ->  $($j.Mail)" -ForegroundColor Green
    $skapade++
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($mail) | Out-Null
}

[System.Runtime.InteropServices.Marshal]::ReleaseComObject($outlook) | Out-Null
[GC]::Collect()
[GC]::WaitForPendingFinalizers()

Write-Host ""
Write-Host "Klart - $skapade utkast skapade i Outlook (mappen Utkast)." -ForegroundColor Cyan

