#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install pyinstaller
pyinstaller --onefile --windowed --name 9second_capture --icon assets/icon/icon.icns scripts/run_local_agent.py
