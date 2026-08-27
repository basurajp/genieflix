# Windows setup for the Views on Autopilot pipeline (Node, ffmpeg, Python,
# a voice venv with Coqui XTTS or edge-tts, config, and a HyperFrames check).
# Usage:  powershell -ExecutionPolicy Bypass -File setup\setup-windows.ps1
# Idempotent — re-run any time; it detects what is installed and only fills gaps.
#
# Note: MLX Chatterbox (the Mac voice path) does NOT run on Windows — Apple's MLX
# is Mac-only. Windows uses Path A (Coqui XTTS v2, a local clone of your voice)
# or Path B (edge-tts, free Microsoft neural voices; not your voice, needs
# network). Everything else — composition, captions, render, factory — is
# identical to the Mac path.

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Venv = Join-Path $RepoRoot ".voice-clone-venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$script:Incomplete = $false

function Step($m) { Write-Host "`n==> $m" }
function Ok($m)   { Write-Host "    ok: $m" }
function Warn($m) { Write-Host "    !!  $m" -ForegroundColor Yellow; $script:Incomplete = $true }
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function WingetInstall($id) {
    if (-not (Have winget)) {
        Warn "winget is not available — install '$id' manually, then re-run this script."
        return
    }
    winget install --id $id -e --accept-source-agreements --accept-package-agreements
    Warn "'$id' was just installed. Open a NEW terminal so it lands on PATH, then re-run this script."
}

Step "Node.js (>= 22, for HyperFrames via npx)"
$nodeOk = $false
if (Have node) {
    $major = [int]((node --version).TrimStart("v").Split(".")[0])
    if ($major -ge 22) { $nodeOk = $true; Ok ("node " + (node --version)) }
    else { Warn "node $(node --version) is older than 22" }
}
if (-not $nodeOk) { WingetInstall "OpenJS.NodeJS.LTS" }

Step "ffmpeg"
if (Have ffmpeg) {
    Ok ((ffmpeg -version 2>$null | Select-Object -First 1))
} else {
    WingetInstall "Gyan.FFmpeg"
}

Step "Python (3.11+)"
$pyOk = $false
if (Have python) {
    try {
        $v = (python --version 2>&1 | Out-String).Trim().Split(" ")[-1]
        $parts = $v.Split(".")
        if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 11) {
            $pyOk = $true; Ok "python $v"
        } elseif ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10) {
            $pyOk = $true; Ok "python $v (works; 3.11+ recommended for the voice backends)"
        }
    } catch { $pyOk = $false }
}
if (-not $pyOk) { WingetInstall "Python.Python.3.12" }

Step "Voice venv (.voice-clone-venv, inside this repo)"
if (Have python) {
    if (-not (Test-Path $VenvPy)) { python -m venv $Venv }
    if (Test-Path $VenvPy) {
        & $VenvPy -m pip install --upgrade pip | Out-Null

        & $VenvPy -c "import TTS" 2>$null
        $haveXtts = ($LASTEXITCODE -eq 0)
        & $VenvPy -c "import edge_tts" 2>$null
        $haveEdge = ($LASTEXITCODE -eq 0)

        if ($haveXtts) {
            Ok "Coqui XTTS already installed (Path A: local voice clone)"
        } elseif ($haveEdge) {
            Ok "edge-tts already installed (Path B: non-clone fallback)"
        } else {
            Write-Host "    Installing Path A: Coqui XTTS v2 (local clone of your voice)."
            Write-Host "    This is a heavy install; with an NVIDIA GPU, installing the CUDA"
            Write-Host "    build of PyTorch from pytorch.org first makes generation much faster."
            try {
                & $VenvPy -m pip install TTS torch torchaudio
                if ($LASTEXITCODE -ne 0) { throw "pip exited with $LASTEXITCODE" }
                Ok "Coqui XTTS installed — your voice, cloned locally from voice-samples\voice-sample.wav"
            } catch {
                Warn "Path A failed (low RAM, no GPU, or a toolchain fight — common on smaller machines)."
                Write-Host "    Falling back to Path B: edge-tts (free Microsoft neural voices;"
                Write-Host "    not your clone, and it needs network)."
                try {
                    & $VenvPy -m pip install edge-tts
                    if ($LASTEXITCODE -ne 0) { throw "pip exited with $LASTEXITCODE" }
                    Ok "edge-tts installed"
                } catch {
                    Warn "edge-tts failed too; the pipeline will fall back to the built-in Kokoro voice (npx hyperframes tts)."
                }
            }
        }
    } else {
        Warn "could not create the venv at $Venv"
    }
} else {
    Warn "skipped (Python not on PATH yet — open a new terminal and re-run)"
}

Step "Config"
$cfg = Join-Path $RepoRoot "pipeline\config.json"
if (Test-Path $cfg) {
    Ok "pipeline/config.json already exists (left untouched)"
} else {
    $example = Join-Path $RepoRoot "pipeline\config.example.json"
    # On Windows the venv lives inside the repo, so point voice_venv at it
    # (relative paths resolve from the repo root).
    (Get-Content $example -Raw).Replace('~/.voice-clone-venv', '.voice-clone-venv') |
        Set-Content -NoNewline -Encoding utf8 $cfg
    Ok "created pipeline/config.json (voice_venv -> .voice-clone-venv in this repo)"
}

Step "HyperFrames doctor"
if (Have node) {
    Push-Location $RepoRoot
    npx hyperframes doctor
    if ($LASTEXITCODE -ne 0) { Warn "doctor reported issues — fix them before rendering" }
    Pop-Location
} else {
    Warn "skipped (Node not available yet)"
}

Step "Next steps"
Write-Host @"
    1. Record your voice reference: 1-2 minutes of clean speech — no music,
       no hum, no echo — and save it as voice-samples\voice-sample.wav.
       (Details in voice-samples\README.md. Skip this if you're on edge-tts.)
    2. Create your first project:   node factory\new.mjs my-first-reel "My first reel"
    3. Edit its lines.txt (five lines: hook, action, proof, contrast, CTA — see
       PLAYBOOK.md) and drop slide images into assets\slides\.
    4. Queue it:                    node factory\enqueue.mjs my-first-reel
    5. Start the factory:           factory\start.bat   (or: node factory\runner.mjs)
       There is no start.command double-click on Windows — that file is the Mac launcher.
    6. Watch it work:               http://localhost:4300/dashboard.html
    Finished reels land in factory\ready-to-post\.
"@

if ($script:Incomplete) {
    Write-Host "`n    !!  Setup finished with warnings above — fix them and re-run this script." -ForegroundColor Yellow
    exit 1
}
Ok "Setup complete."
