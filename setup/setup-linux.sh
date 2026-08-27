#!/usr/bin/env bash
# Linux setup for the Views on Autopilot pipeline (ffmpeg, Node 22, a voice
# venv with Coqui XTTS or edge-tts, config, and a HyperFrames health check).
# Usage: ./setup/setup-linux.sh   — idempotent; re-run any time, it only fills gaps.
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$HOME/.voice-clone-venv"
INCOMPLETE=0

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    ok: %s\n' "$1"; }
warn() { printf '    !!  %s\n' "$1"; }

SUDO=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
fi

PKG=""
if command -v apt-get >/dev/null 2>&1; then
  PKG="apt"
elif command -v dnf >/dev/null 2>&1; then
  PKG="dnf"
fi

step "ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  ok "$(ffmpeg -version 2>/dev/null | head -n 1)"
else
  case "$PKG" in
    apt) $SUDO apt-get update -qq && $SUDO apt-get install -y ffmpeg ;;
    dnf) $SUDO dnf install -y ffmpeg || warn "on Fedora/RHEL, ffmpeg may need the RPM Fusion repos enabled" ;;
    *)   warn "no apt/dnf found — install ffmpeg with your distro's package manager" ;;
  esac
  command -v ffmpeg >/dev/null 2>&1 || { warn "ffmpeg still missing"; INCOMPLETE=1; }
fi

step "Node.js (>= 22, for HyperFrames via npx)"
node_major=0
if command -v node >/dev/null 2>&1; then
  node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
fi
if [ "$node_major" -ge 22 ]; then
  ok "node $(node --version)"
else
  warn "Node >= 22 not found. Distro packages are usually too old; the easy path is nvm:"
  warn '  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash'
  warn '  nvm install 22'
  warn "then re-run this script."
  INCOMPLETE=1
fi

step "Voice venv (Coqui XTTS clone, or edge-tts fallback)"
# MLX Chatterbox is Mac-only (Apple Silicon). On Linux the clone path is Coqui
# XTTS v2; edge-tts is the lighter non-clone fallback; the built-in Kokoro voice
# (npx hyperframes tts) always works and needs nothing installed here.
if [ ! -x "$VENV/bin/python" ]; then
  if ! python3 -m venv "$VENV" 2>/dev/null; then
    if [ "$PKG" = "apt" ]; then
      $SUDO apt-get install -y python3-venv python3-pip && python3 -m venv "$VENV"
    fi
  fi
fi
if [ -x "$VENV/bin/python" ]; then
  "$VENV/bin/pip" install --upgrade pip >/dev/null
  if "$VENV/bin/python" -c "import TTS" >/dev/null 2>&1; then
    ok "Coqui TTS already installed (voice clone path)"
  elif "$VENV/bin/python" -c "import edge_tts" >/dev/null 2>&1; then
    ok "edge-tts already installed (non-clone fallback)"
  elif "$VENV/bin/pip" install TTS torch torchaudio; then
    ok "Coqui XTTS installed — your voice, cloned locally from voice-samples/voice-sample.wav"
  else
    warn "Coqui XTTS install failed (it is a heavy install). Falling back to edge-tts —"
    warn "free Microsoft neural voices: not your clone, and it needs network."
    if "$VENV/bin/pip" install edge-tts; then
      ok "edge-tts installed"
    else
      warn "edge-tts failed too; the pipeline will fall back to the built-in Kokoro voice."
    fi
  fi
else
  warn "could not create $VENV — the pipeline will fall back to the Kokoro voice"
  INCOMPLETE=1
fi

step "Config"
if [ -f "$REPO_ROOT/pipeline/config.json" ]; then
  ok "pipeline/config.json already exists (left untouched)"
else
  cp "$REPO_ROOT/pipeline/config.example.json" "$REPO_ROOT/pipeline/config.json"
  ok "created pipeline/config.json from the example"
fi

step "HyperFrames doctor"
if command -v node >/dev/null 2>&1; then
  (cd "$REPO_ROOT" && npx hyperframes doctor) || { warn "doctor reported issues — fix them before rendering"; INCOMPLETE=1; }
else
  warn "skipped (Node not available yet)"
  INCOMPLETE=1
fi

printf '\n==> Next steps\n'
cat <<'EOF'
    1. Record your voice reference: 1-2 minutes of clean speech — no music,
       no hum, no echo — and save it as voice-samples/voice-sample.wav.
       (Details in voice-samples/README.md. Skip this if you're on edge-tts/Kokoro.)
    2. Create your first project:   node factory/new.mjs my-first-reel "My first reel"
    3. Edit its lines.txt (five lines: hook, action, proof, contrast, CTA — see
       PLAYBOOK.md) and drop slide images into assets/slides/.
    4. Queue it:                    node factory/enqueue.mjs my-first-reel
    5. Start the factory:           node factory/runner.mjs
    6. Watch it work:               http://localhost:4300/dashboard.html
    Finished reels land in factory/ready-to-post/.
EOF

if [ "$INCOMPLETE" -ne 0 ]; then
  warn "Setup finished with warnings above — fix them and re-run this script."
  exit 1
fi
ok "Setup complete."
