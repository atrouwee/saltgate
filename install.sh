#!/bin/sh
# SALTGATE one-line installer (macOS / Linux).
#   curl -fsSL https://raw.githubusercontent.com/atrouwee/saltgate/main/install.sh | sh
# Installs uv (a small Python tool manager) if needed, then the `saltgate` command with its own Python.
set -e
echo "SALTGATE installer — the name is a wink, the work is sincere."
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv (Python tool manager)…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
echo "Installing saltgate…"
if [ "${SALTGATE_ROTATE:-}" = "1" ]; then
  uv tool install --force --python 3.12 --with torch --with torchvision "saltgate @ git+https://github.com/atrouwee/saltgate.git"
else
  uv tool install --force --python 3.12 "saltgate @ git+https://github.com/atrouwee/saltgate.git"
fi
uv tool update-shell >/dev/null 2>&1 || true
echo
echo "Done. Open a NEW terminal window and type:   saltgate"
echo "It will ask where your scans are and walk you through the rest."
