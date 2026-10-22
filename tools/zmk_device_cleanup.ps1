<#
.SYNOPSIS
  Cleanup stale (ghost) ZMK device entries on Windows.
.DESCRIPTION
  Targets PnP entries for the ZMK USB VID/PID (VID_1D50&PID_615E).
  - Default mode: report only (no admin needed).
  - -Apply: removes stale entries via pnputil (requires an elevated PowerShell).
  - -IncludeBle: additionally lists (and with -Apply removes) Bluetooth LE ghost
    keys under HKLM\SYSTEM\CurrentControlSet\Enum\BTHLE\DEV_* (requires admin;
    registry removal, safer to do while Bluetooth for target device is disconnected).
.NOTES
  Best performed with the keyboard NOT plugged in via USB (BLE pairs unaffected).
  pnputil /remove-device requires Windows 10 1809 or later.
#>
param(
    [switch]$Apply,
    [switch]$IncludeBle
)

$ErrorActionPreference = 'Continue'
$vidPattern = 'VID_1D50&PID_615E'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "== ZMK device cleanup ==" -ForegroundColor Cyan
Write-Host ("Admin elevated session: {0}" -f $isAdmin)

# --- 1) Report stale USB/HID PnP entries ---
$devices = @(Get-PnpDevice | Where-Object { $_.InstanceId -match $vidPattern })
Write-Host ""
Write-Host ("Found {0} PnP entries for {1}" -f $devices.Count, $vidPattern)
$devices | Group-Object Status | ForEach-Object {
    Write-Host ("  Status '{0}': {1} devices" -f $_.Name, $_.Count)
}
Write-Host ""
Write-Host "Device list:"
foreach ($d in ($devices | Sort-Object Status, InstanceId)) {
    Write-Host ("  [{0}] {1,-12} {2}" -f $d.Status, $d.Class, $d.InstanceId)
}

if ($Apply) {
    if (-not $isAdmin) {
        Write-Warning "Removal requires admin. Re-run from an elevated PowerShell:"
        Write-Host ("  powershell -ExecutionPolicy Bypass -File `"{0}`" -Apply" -f $PSCommandPath)
        Write-Host "Tip: start an elevated prompt (Win+X > Terminal (Admin)) or ask IT to run this script."
        exit 1
    }

    Write-Host ""
    Write-Host "== Removing stale entries (Status Unknown only) ==" -ForegroundColor Yellow
    $removed = 0; $failed = 0
    foreach ($d in $devices) {
        if ($d.Status -ne 'Unknown') {
            Write-Host ("  SKIP (currently connected): {0}" -f $d.InstanceId)
            continue
        }
        Write-Host ("  Removing: {0}" -f $d.InstanceId)
        pnputil.exe /remove-device "$($d.InstanceId)" | Out-Null
        if ($LASTEXITCODE -eq 0) { $removed++ } else { $failed++ }
    }
    Write-Host ("Done. Removed: {0}, Failed: {1}" -f $removed, $failed)
}

# --- 2) Optional: Bluetooth LE ghost keys in registry ---
if ($IncludeBle) {
    $base = 'HKLM:\SYSTEM\CurrentControlSet\Enum\BTHLE\DEV_'
    $keys = @(Get-ChildItem -Path $base -ErrorAction SilentlyContinue)
    Write-Host ""
    Write-Host ("Bluetooth LE enumeration keys (BTHLE\DEV_*): {0}" -f $keys.Count)
    # Show keys whose child (descriptor) indicates ZMK VID (IMD 1D50 encoding inside key name)
    $zmkKeys = $keys | Where-Object { $_.PSChildName -match '1D50' -or (Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '1D50' }) }
    # key names look like DEV_<MAC>; device identity lives in subkey (e.g. VID&00011D50_PID&615E)
    Write-Host "Keys mentioning ZMK VID 1D50 / PID 615E anywhere in name or subkeys:"
    $targets = @()
    foreach ($k in $keys) {
        $sub = Get-ChildItem $k.PSPath -ErrorAction SilentlyContinue
        $hit = ($sub.PSChildName -match '1D50|615E') -or ($k.PSChildName -match '1D50|615E')
        if ($hit) {
            Write-Host ("  {0}  [{1}]" -f $k.Name, ($sub.PSChildName -join ', '))
            $targets += $k
        }
    }
    if ($targets.Count -eq 0) { Write-Host "  (none found)" }

    if ($Apply -and $targets.Count -gt 0) {
        if (-not $isAdmin) {
            Write-Warning "Registry removal requires admin; none removed."
            exit 2
        }
        foreach ($k in $targets) {
            Write-Host ("  Deleting reg key: {0}" -f $k.Name)
            Remove-Item -Path $k.PSPath -Recurse -Force -ErrorAction Continue
        }
        Write-Host "Note: some Properties subkeys are SYSTEM-owned and may need Sysinternals PsExec:  PsExec.exe -i -s regedit.exe   (then delete HKLM\SYSTEM\CurrentControlSet\Enum\BTHLE\DEV_<...> manually)"
    }
}

Write-Host ""
if (-not $Apply) {
    Write-Host "Report-only mode. To remove stale entries, run in an ELEVATED PowerShell:"
    Write-Host ("  powershell -ExecutionPolicy Bypass -File `"{0}`" -Apply" -f $PSCommandPath)
    Write-Host ("Add -IncludeBle to also clean Bluetooth LE ghost registry keys (advanced).")
}
