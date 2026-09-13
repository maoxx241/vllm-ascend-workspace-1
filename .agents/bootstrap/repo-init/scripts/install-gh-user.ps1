[CmdletBinding()]
param(
  [switch]$AddToPath = $true
)

$ErrorActionPreference = "Stop"

# This emergency installer can run before Python exists. Emit the same bounded
# schema using static fields only; the installed diagnostics worker owns export
# and retention. Logging failure never changes installation or its exit status.
$diagnosticId = [Guid]::NewGuid().ToString('N')
$diagnosticStart = [Diagnostics.Stopwatch]::StartNew()
$diagnosticPhase = 'discovery'
$diagnosticPhaseStart = 0.0
function Write-InstallEvent([string]$Event, [string]$Severity, [string]$Status, [string]$ErrorType = '') {
  try {
    $diagnosticRoot = $env:VAWS_DIAGNOSTICS_ROOT
    if (-not $diagnosticRoot) { $diagnosticRoot = Join-Path $env:LOCALAPPDATA 'vaws/diagnostics' }
    $folder = Join-Path $diagnosticRoot 'events/vaws-workspace'
    [IO.Directory]::CreateDirectory($folder) | Out-Null
    $record = @{
      schema = 1; timestamp = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
      monotonic_ns = [long]($diagnosticStart.Elapsed.TotalMilliseconds * 1000000)
      clock_domain_unknown = $true; pid = $PID; process_instance_id = $diagnosticId
      component = 'vaws-workspace'; package_version = 'bootstrap'; severity = $Severity
      event = $Event; operation = 'install_gh_user'; operation_id = $diagnosticId; trace_id = $diagnosticId
      status = $Status; duration_ms = $diagnosticStart.Elapsed.TotalMilliseconds
      attributes = @{ stage = $diagnosticPhase; elapsed_ms = $diagnosticStart.Elapsed.TotalMilliseconds - $diagnosticPhaseStart }
    }
    if ($ErrorType) { $record.attributes.error_type = $ErrorType; $record.attributes.category = 'bootstrap' }
    $line = ConvertTo-Json -InputObject $record -Depth 4 -Compress
    if ($line.Length -le 16000) {
      [IO.File]::AppendAllText((Join-Path $folder "$PID-$diagnosticId.jsonl"), "$line`n", [Text.UTF8Encoding]::new($false))
    }
  } catch { }
}
trap {
  Write-InstallEvent 'operation.end' 'ERROR' 'error' $_.Exception.GetType().Name
  throw
}
Write-InstallEvent 'operation.start' 'INFO' 'running'

function Get-ArchToken {
  $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
  switch ($arch) {
    "x64"   { return "amd64" }
    "arm64" { return "arm64" }
    default { throw "Unsupported Windows architecture: $arch" }
  }
}

$archToken = Get-ArchToken
$apiUrl = "https://api.github.com/repos/cli/cli/releases/latest"
$headers = @{
  "Accept" = "application/vnd.github+json"
  "User-Agent" = "repo-init-fallback"
}

$diagnosticPhase = 'release_lookup'
$diagnosticPhaseStart = $diagnosticStart.Elapsed.TotalMilliseconds

Write-Host "Querying latest GitHub CLI release ..."
$release = Invoke-RestMethod -Uri $apiUrl -Headers $headers
$asset = $release.assets | Where-Object { $_.name -match ("^gh_.*_windows_{0}\.zip$" -f $archToken) } | Select-Object -First 1

if (-not $asset) {
  throw "Could not find a matching Windows asset for architecture $archToken"
}
Write-InstallEvent 'phase.end' 'INFO' 'success'

$installRoot = Join-Path $env:LOCALAPPDATA "Programs\GitHubCLI\$($release.tag_name)"
$binDir = Join-Path $installRoot "bin"
$currentDir = Join-Path $env:LOCALAPPDATA "Programs\GitHubCLI\current"
$tmpZip = Join-Path $env:TEMP $asset.name
$tmpExtract = Join-Path $env:TEMP ("repo-init-gh-" + [System.Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $binDir | Out-Null
New-Item -ItemType Directory -Force -Path $currentDir | Out-Null
New-Item -ItemType Directory -Force -Path $tmpExtract | Out-Null

Write-Host "Downloading $($asset.name) ..."
$diagnosticPhase = 'download_install'
$diagnosticPhaseStart = $diagnosticStart.Elapsed.TotalMilliseconds
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $tmpZip
Expand-Archive -Path $tmpZip -DestinationPath $tmpExtract -Force

$ghExe = Get-ChildItem -Path $tmpExtract -Recurse -Filter gh.exe | Where-Object {
  $_.FullName -match "\\bin\\gh\.exe$"
} | Select-Object -First 1

if (-not $ghExe) {
  throw "Downloaded archive does not contain bin\gh.exe"
}

Copy-Item -Force $ghExe.FullName (Join-Path $binDir "gh.exe")
Copy-Item -Force (Join-Path $binDir "gh.exe") (Join-Path $currentDir "gh.exe")
Write-InstallEvent 'phase.end' 'INFO' 'success'
$diagnosticPhase = 'path_and_cleanup'
$diagnosticPhaseStart = $diagnosticStart.Elapsed.TotalMilliseconds

if ($AddToPath) {
  $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $pathEntries = @()
  if ($userPath) {
    $pathEntries = $userPath -split ";"
  }
  if ($pathEntries -notcontains $currentDir) {
    $newPath = if ($userPath) { "$userPath;$currentDir" } else { $currentDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Updated the user PATH with: $currentDir"
    Write-Host "Restart your terminal so the new PATH is visible."
  }
}

Remove-Item -Force $tmpZip
Remove-Item -Recurse -Force $tmpExtract

Write-Host ""
Write-Host "Installed gh to $binDir"
Write-Host "Convenience path: $currentDir\gh.exe"
Write-Host ""
Write-Host "Verify with:"
Write-Host "  gh --version"
Write-Host "  gh auth status --hostname github.com"
Write-InstallEvent 'phase.end' 'INFO' 'success'
Write-InstallEvent 'operation.end' 'INFO' 'success'
