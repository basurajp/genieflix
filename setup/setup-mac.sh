#!/usr/bin/env bash
# Mac setup for the Views on Autopilot pipeline (Homebrew, ffmpeg, Node,
# the Chatterbox voice venv, config, and a HyperFrames health check).
# Usage: ./setup/setup-mac.sh   — idempotent; re-run any time, it only fills gaps.
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$HOME/.voice-clone-venv"
INCOMPLETE=0

step() { printf '\n==> %s\n' "$1"; }
ok()   { printf '    ok: %s\n' "$1"; }
warn() { printf '    !!  %s\n' "$1"; }

step "Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew is not installed. Install it first:"
  warn '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  warn "then re-run this script."
  exit 1
fi
ok "$(brew --version | head -n 1)"

step "ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  ok "$(ffmpeg -version 2>/dev/null | head -n 1)"
else
  brew install ffmpeg || { warn "ffmpeg install failed"; INCOMPLETE=1; }
fi

step "Node.js (>= 22, for HyperFrames via npx)"
node_major=0
if command -v node >/dev/null 2>&1; then
  node_major="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
fi
if [ "$node_major" -ge 22 ]; then
  ok "node $(node --version)"
else
  brew install node 2>/dev/null || brew upgrade node || true
  if command -v node >/dev/null 2>&1 && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]; then
    ok "node $(node --version)"
  else
    warn "Node >= 22 still not available; install/upgrade it via Homebrew and re-run."
    INCOMPLETE=1
  fi
fi

step "Voice venv (Chatterbox via mlx-audio)"
if [ "$(uname -m)" = "arm64" ]; then
  [ -d "$VENV" ] || python3 -m venv "$VENV"
  if "$VENV/bin/pip" install --upgrade pip mlx-audio; then
    ok "mlx-audio ready in $VENV"
  else
    warn "mlx-audio install failed. The pipeline will fall back to the built-in"
    warn "Kokoro voice (npx hyperframes tts) until this is fixed."
    INCOMPLETE=1
  fi
else
  # MLX runs on Apple Silicon only — same limit as Windows/Linux (see setup-linux.sh).
  warn "This Mac is Intel; MLX (Chatterbox) needs Apple Silicon."
  warn "Skipping the clone venv — the pipeline will use the built-in Kokoro voice,"
  warn "or install Coqui XTTS the way setup-linux.sh does if you want a clone."
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
       (Details in voice-samples/README.md. Clean beats long.)
    2. Create your first project:   node factory/new.mjs my-first-reel "My first reel"
    3. Edit its lines.txt (five lines: hook, action, proof, contrast, CTA — see
       PLAYBOOK.md) and drop slide images into assets/slides/.
    4. Queue it:                    node factory/enqueue.mjs my-first-reel
    5. Start the factory:           ./factory/start.command
    6. Watch it work:               http://localhost:4300/dashboard.html
    Finished reels land in factory/ready-to-post/.
EOF

if [ "$INCOMPLETE" -ne 0 ]; then
  warn "Setup finished with warnings above — fix them and re-run this script."
  exit 1
fi
ok "Setup complete."
