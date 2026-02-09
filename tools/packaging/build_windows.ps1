$ErrorActionPreference = "Stop"

$venv = ".venv-pack"
if (-not (Test-Path $venv)) {
  py -3 -m venv $venv
}

$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install -U pip
& $python -m pip install pyinstaller

& $python -m PyInstaller --onedir --windowed --noconfirm --clean `
  --name 9second_capture `
  --icon assets/icon/icon.ico `
  --add-data "apps;bundle/apps" `
  --add-data "src;bundle/src" `
  --add-data "scripts/run_local_agent.py;bundle/scripts" `
  --add-data "requirements.app.txt;bundle" `
  --add-data "requirements.whisper.txt;bundle" `
  --add-data "apps/launcher/ui;bundle/launcher_ui" `
  --exclude-module pytest `
  --exclude-module py `
  --exclude-module IPython `
  --exclude-module pygments `
  scripts/launcher.py
