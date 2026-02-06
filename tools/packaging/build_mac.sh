#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install pyinstaller
pyinstaller --onedir --windowed --noconfirm --clean \
  --name 9second_capture \
  --icon assets/icon/icon.icns \
  --add-data "apps/api_gateway/ui:apps/api_gateway/ui" \
  --exclude-module pytest \
  --exclude-module py \
  --exclude-module IPython \
  --exclude-module pygments \
  scripts/run_local_agent.py

APP_PATH="dist/9second_capture.app"
if [ -d "$APP_PATH" ]; then
  # Убираем extended attributes (resource fork/Finder info),
  # иначе codesign может падать.
  xattr -cr "$APP_PATH" || true
  /usr/bin/codesign --force --deep --sign - "$APP_PATH" || true
fi
