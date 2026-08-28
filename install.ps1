# SALTGATE one-line installer (Windows).
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/atrouwee/saltgate/main/install.ps1 | iex"
# The Windows half of install.sh: same uv, same tool install, same 47 MB
# auto-rotation model into the same place saltgate looks for it.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'     # the download bar costs more than the download
# Windows PowerShell 5.1 still defaults to TLS 1.0 and github.com refuses that.
# PowerShell 7 negotiates for itself, and pinning it there would rule out 1.3.
if ($PSVersionTable.PSVersion.Major -lt 6) {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}

Write-Host 'SALTGATE installer - the name is a wink, the work is sincere.'

# uv brings its own Python, so nothing here depends on what is already installed.
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host 'Installing uv (Python tool manager)...'
  Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
}
# uv has just written itself somewhere this session's PATH has never heard of.
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = "$env:USERPROFILE\.local\bin\uv.exe" }
if (-not (Test-Path $uv)) {
  Write-Host 'uv did not install. Install it by hand from https://docs.astral.sh/uv/ and run this again.'
  exit 1
}

# Most Windows machines have no git, and a `git+https://` install needs one.
# GitHub serves the same tree as a zip and uv installs from that just as well.
$spec = 'saltgate @ git+https://github.com/atrouwee/saltgate.git'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host 'No git here - installing from the source archive instead.'
  $spec = 'saltgate @ https://github.com/atrouwee/saltgate/archive/refs/heads/main.zip'
}
if ($env:SALTGATE_SPEC) { $spec = $env:SALTGATE_SPEC }   # CI installs this checkout instead
Write-Host 'Installing saltgate...'
& $uv tool install --force --python 3.12 $spec
if ($LASTEXITCODE -ne 0) { Write-Host 'The install failed - the lines above say why.'; exit 1 }
# puts the command on PATH for windows opened after this one. Redirecting a
# native command's stderr would turn uv's ordinary progress lines into
# terminating errors under $ErrorActionPreference = 'Stop', so it isn't.
try { & $uv tool update-shell | Out-Null } catch { }

# The auto-rotation backbone: 47 MB, fetched here so the walkthrough never has to
# stop and ask. Everything below is best-effort -- if it fails, saltgate offers
# the same download itself the first time you use auto-rotation.
if ($env:SALTGATE_NO_MODEL -ne '1') {
  $modelUrl = 'https://github.com/atrouwee/saltgate/releases/download/orient-model-v1/orient-resnet50-body-fp16.onnx'
  $modelSha = '818e29fe77ea228d64fcf04f7798c98f4838a7a66385209c70785472321b2a49'
  # the same folder orient.model_cache_dir() reads on a non-Mac: ~/.saltgate/models
  $modelDir = Join-Path $env:USERPROFILE '.saltgate\models'
  $modelPath = Join-Path $modelDir 'orient-resnet50-body-fp16.onnx'
  if (Test-Path $modelPath) {
    Write-Host 'Auto-rotation model already present.'
  } else {
    Write-Host 'Fetching the auto-rotation model (47 MB, once)...'
    New-Item -ItemType Directory -Force -Path $modelDir | Out-Null
    $part = "$modelPath.part"
    try {
      Invoke-WebRequest -Uri $modelUrl -OutFile $part -UseBasicParsing
      # written to a .part and renamed only once the digest matches, so an
      # interrupted or tampered download can never be loaded
      if ((Get-FileHash $part -Algorithm SHA256).Hash -eq $modelSha) {
        Move-Item -Force $part $modelPath
      } else {
        Remove-Item -Force $part
        Write-Host '  checksum did not match - skipping; saltgate will offer it again later.'
      }
    } catch {
      if (Test-Path $part) { Remove-Item -Force $part }
      Write-Host "  couldn't download it - skipping; saltgate will offer it again later."
    }
  }
}

Write-Host ''
Write-Host 'Done. Close this window, open a NEW PowerShell window and type:   saltgate'
Write-Host 'It will ask where your scans are and walk you through the rest.'
Write-Host "If it says the command isn't recognised, use this line instead:   $env:USERPROFILE\.local\bin\saltgate.exe"
