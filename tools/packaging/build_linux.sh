#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture --icon assets/icon/icon_1024.png scripts/run_local_agent.py
