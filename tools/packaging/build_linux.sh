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

python -m PyInstaller --onedir --windowed --noconfirm --clean \
  --name 9second_capture \
  --icon assets/icon/icon_1024.png \
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
