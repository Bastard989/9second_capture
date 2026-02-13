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
find . -name ".DS_Store" -delete || true
if command -v dot_clean >/dev/null 2>&1; then
  dot_clean -m apps src scripts assets tools/packaging 2>/dev/null || true
fi
if command -v xattr >/dev/null 2>&1; then
  xattr -cr apps src scripts assets tools/packaging requirements.app.txt requirements.whisper.txt 2>/dev/null || true
  xattr -dr com.apple.FinderInfo assets/icon/icon.icns 2>/dev/null || true
  xattr -dr com.apple.ResourceFork assets/icon/icon.icns 2>/dev/null || true
fi

export COPYFILE_DISABLE=1
export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/.pyinstaller-cache}"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

# Удаляем старые артефакты перед сборкой, чтобы не наследовать xattr/подписи.
rm -rf build/9second_capture dist/9second_capture dist/9second_capture.app 2>/dev/null || true

# Используем "чистую" копию иконки без metadata/resource fork.
PACK_ICON=".pyinstaller-icon.icns"
cat assets/icon/icon.icns > "$PACK_ICON"
if command -v xattr >/dev/null 2>&1; then
  xattr -cr "$PACK_ICON" 2>/dev/null || true
fi

python -m PyInstaller --onedir --windowed --noconfirm --clean --log-level ERROR \
  --name 9second_capture \
  --icon "$PACK_ICON" \
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

rm -f "$PACK_ICON" 2>/dev/null || true

deactivate

APP_PATH="dist/9second_capture.app"
if [ -d "$APP_PATH" ]; then
  scrub_bundle_metadata() {
    local target="$1"
    find "$target" -name "._*" -delete || true
    find "$target" -name ".DS_Store" -delete || true
    if command -v dot_clean >/dev/null 2>&1; then
      dot_clean -m "$target" || true
    fi
    if command -v xattr >/dev/null 2>&1; then
      xattr -cr "$target" || true
      xattr -crs "$target" 2>/dev/null || true
      xattr -dr com.apple.FinderInfo "$target" 2>/dev/null || true
      xattr -drs com.apple.FinderInfo "$target" 2>/dev/null || true
      xattr -dr com.apple.ResourceFork "$target" 2>/dev/null || true
      xattr -drs com.apple.ResourceFork "$target" 2>/dev/null || true
      xattr -dr com.apple.fileprovider.fpfs#P "$target" 2>/dev/null || true
      xattr -drs com.apple.fileprovider.fpfs#P "$target" 2>/dev/null || true
    fi
  }

  CLEAN_APP_PATH="dist/9second_capture.clean.app"
  rm -rf "$CLEAN_APP_PATH" 2>/dev/null || true
  if command -v ditto >/dev/null 2>&1; then
    # Пересобираем bundle без extended attrs/resource fork.
    ditto --noextattr --norsrc "$APP_PATH" "$CLEAN_APP_PATH"
    rm -rf "$APP_PATH" 2>/dev/null || true
    mv "$CLEAN_APP_PATH" "$APP_PATH"
  fi
  # Убираем AppleDouble и extended attributes (resource fork/Finder info),
  # иначе codesign падает.
  scrub_bundle_metadata "$APP_PATH"
  if [ "${MANUAL_CODESIGN:-1}" = "1" ]; then
    signed_ok=0
    SIGN_TMP_DIR="$(mktemp -d /tmp/9second_capture_sign.XXXXXX 2>/dev/null || mktemp -d)"
    SIGN_APP_PATH="$SIGN_TMP_DIR/9second_capture.app"
    if command -v ditto >/dev/null 2>&1; then
      ditto --noextattr --norsrc "$APP_PATH" "$SIGN_APP_PATH"
    else
      cp -R "$APP_PATH" "$SIGN_APP_PATH"
    fi
    for attempt in 1 2 3; do
      scrub_bundle_metadata "$SIGN_APP_PATH"
      if /usr/bin/codesign --force --deep --sign - "$SIGN_APP_PATH"; then
        signed_ok=1
        break
      fi
      echo "[pack] codesign attempt $attempt failed, retrying..."
      sleep 0.3
    done
    if [ "$signed_ok" -eq 1 ]; then
      rm -rf "$APP_PATH" 2>/dev/null || true
      if command -v ditto >/dev/null 2>&1; then
        ditto --noextattr --norsrc "$SIGN_APP_PATH" "$APP_PATH"
      else
        mv "$SIGN_APP_PATH" "$APP_PATH"
      fi
      scrub_bundle_metadata "$APP_PATH"
    else
      echo "[pack] warning: post-build ad-hoc codesign still failed."
    fi
    rm -rf "$SIGN_TMP_DIR" 2>/dev/null || true
    echo "[pack] post-build ad-hoc codesign finished."
  else
    echo "[pack] manual codesign skipped (set MANUAL_CODESIGN=1 to force ad-hoc signing)."
  fi
fi
