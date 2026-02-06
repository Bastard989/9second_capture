#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install pyinstaller
pyinstaller --onedir --noconfirm --clean \
  --name 9second_capture \
  --icon assets/icon/icon_1024.png \
  --add-data "apps/api_gateway/ui:apps/api_gateway/ui" \
  --exclude-module pytest \
  --exclude-module py \
  --exclude-module IPython \
  --exclude-module pygments \
  scripts/run_local_agent.py
