$ErrorActionPreference = "Stop"

py -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture scripts/run_local_agent.py
