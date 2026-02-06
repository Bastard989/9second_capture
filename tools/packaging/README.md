# Packaging (launcher binaries)

Цель: собрать простой лаунчер, который запускает локальный агент и открывает UI.

## Базовый вариант (PyInstaller)

### macOS
```bash
python3 -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture scripts/run_local_agent.py
```

### Windows
```powershell
py -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture scripts/run_local_agent.py
```

### Linux
```bash
python3 -m pip install pyinstaller
pyinstaller --onefile --name 9second_capture scripts/run_local_agent.py
```

## Иконка

Иконка пока не задана. Позже можно добавить флаг:
`--icon path/to/icon` (png/ico/icns).

## Примечание

В прод-сборке нужно убедиться, что:
- backend зависимости доступны (uvicorn, fastapi, etc.)
- порт выбирается автоматически (логика уже в run_local_agent.py)
- UI открывается автоматически (LOCAL_AGENT_AUTO_OPEN=true)
