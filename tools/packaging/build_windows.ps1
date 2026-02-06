$ErrorActionPreference = "Stop"

py -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture --icon assets/icon/icon.ico scripts/run_local_agent.py
