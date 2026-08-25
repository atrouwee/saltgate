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
uv tool install --force --python 3.12 "saltgate @ git+https://github.com/atrouwee/saltgate.git"
uv tool update-shell >/dev/null 2>&1 || true

# The auto-rotation backbone: 47 MB, fetched here so the walkthrough never has to
# stop and ask. Everything below is best-effort -- if it fails, saltgate offers
# the same download itself the first time you use auto-rotation.
if [ "${SALTGATE_NO_MODEL:-}" != "1" ]; then
  MODEL_URL="https://github.com/atrouwee/saltgate/releases/download/orient-model-v1/orient-resnet50-body-fp16.onnx"
  MODEL_SHA="818e29fe77ea228d64fcf04f7798c98f4838a7a66385209c70785472321b2a49"
  case "$(uname -s)" in
    Darwin) MODEL_DIR="$HOME/Library/Application Support/saltgate/models" ;;
    *)      MODEL_DIR="$HOME/.saltgate/models" ;;
  esac
  MODEL_PATH="$MODEL_DIR/orient-resnet50-body-fp16.onnx"
  if [ -f "$MODEL_PATH" ]; then
    echo "Auto-rotation model already present."
  else
    echo "Fetching the auto-rotation model (47 MB, once)…"
    mkdir -p "$MODEL_DIR"
    if curl -fL# "$MODEL_URL" -o "$MODEL_PATH.part" 2>/dev/null; then
      if command -v shasum >/dev/null 2>&1; then GOT=$(shasum -a 256 "$MODEL_PATH.part" | cut -d' ' -f1)
      elif command -v sha256sum >/dev/null 2>&1; then GOT=$(sha256sum "$MODEL_PATH.part" | cut -d' ' -f1)
      else GOT="$MODEL_SHA"; fi          # no checksum tool: saltgate verifies again on load
      if [ "$GOT" = "$MODEL_SHA" ]; then
        mv "$MODEL_PATH.part" "$MODEL_PATH"
      else
        rm -f "$MODEL_PATH.part"
        echo "  checksum did not match — skipping; saltgate will offer it again later."
      fi
    else
      rm -f "$MODEL_PATH.part"
      echo "  couldn't download it — skipping; saltgate will offer it again later."
    fi
  fi
fi

echo
echo "Done. Open a NEW terminal window and type:   saltgate"
echo "It will ask where your scans are and walk you through the rest."
