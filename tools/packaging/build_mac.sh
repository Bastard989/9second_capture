#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv-pack"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

# Убираем AppleDouble (._*) из исходников, чтобы не тащить их в bundle
find . -name "._*" -delete || true
find . -name "__pycache__" -type d -exec rm -rf {} + || true
find . -name "*.pyc" -delete || true
find . -name "*.pyo" -delete || true

export COPYFILE_DISABLE=1

python -m pyinstaller --onedir --windowed --noconfirm --clean \
  --name 9second_capture \
  --icon assets/icon/icon.icns \
  --paths "." \
  --paths "src" \
  --add-data "apps/api_gateway/ui:apps/api_gateway/ui" \
  --exclude-module pytest \
  --exclude-module py \
  --exclude-module IPython \
  --exclude-module pygments \
  scripts/run_local_agent.py

deactivate

APP_PATH="dist/9second_capture.app"
if [ -d "$APP_PATH" ]; then
  # Убираем AppleDouble и extended attributes (resource fork/Finder info),
  # иначе codesign падает.
  find "$APP_PATH" -name "._*" -delete || true
  if command -v dot_clean >/dev/null 2>&1; then
    dot_clean -m "$APP_PATH" || true
  fi
  xattr -cr "$APP_PATH" || true
  /usr/bin/codesign --force --deep --sign - "$APP_PATH" || true
fi
