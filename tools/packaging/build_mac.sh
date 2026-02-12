#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv-pack"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install -U pip
python -m pip install pyinstaller

# Убираем AppleDouble (._*) и xattr из исходников, чтобы не тащить мусор в bundle
find . -name "._*" -delete || true
if command -v xattr >/dev/null 2>&1; then
  xattr -cr apps src scripts assets tools/packaging requirements.app.txt requirements.whisper.txt 2>/dev/null || true
fi

export COPYFILE_DISABLE=1

python -m PyInstaller --onedir --windowed --noconfirm --clean \
  --name 9second_capture \
  --icon assets/icon/icon.icns \
  --add-data "apps:bundle/apps" \
  --add-data "src:bundle/src" \
  --add-data "scripts/run_local_agent.py:bundle/scripts" \
  --add-data "requirements.app.txt:bundle" \
  --add-data "requirements.whisper.txt:bundle" \
  --add-data "apps/launcher/ui:bundle/launcher_ui" \
  --exclude-module pytest \
  --exclude-module py \
  --exclude-module IPython \
  --exclude-module pygments \
  scripts/launcher.py

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
  xattr -dr com.apple.FinderInfo "$APP_PATH" 2>/dev/null || true
  xattr -dr com.apple.ResourceFork "$APP_PATH" 2>/dev/null || true
  if ! /usr/bin/codesign --force --deep --sign - "$APP_PATH"; then
    # На некоторых системах FinderInfo может возвращаться после первого pass.
    xattr -dr com.apple.FinderInfo "$APP_PATH" 2>/dev/null || true
    xattr -dr com.apple.ResourceFork "$APP_PATH" 2>/dev/null || true
    /usr/bin/codesign --force --deep --sign - "$APP_PATH" || true
  fi
fi
