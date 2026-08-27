#!/bin/bash
# Double-clickable launcher (macOS): starts the factory runner + dashboard.
set -e
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "error: node not found — run setup/setup-mac.sh first" >&2
  exit 1
fi
exec node runner.mjs
