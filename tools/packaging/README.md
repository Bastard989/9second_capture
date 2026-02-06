# Packaging (launcher binaries)

Цель: собрать простой лаунчер, который запускает локальный агент и открывает UI.

## Базовый вариант (PyInstaller)

### macOS
```bash
tools/packaging/build_mac.sh
```

### Windows
```powershell
tools/packaging/build_windows.ps1
```

### Linux
```bash
tools/packaging/build_linux.sh
```

## Иконка

Иконка задана в `assets/icon/`:
- macOS: `icon.icns`
- Windows: `icon.ico`
- Linux: `icon_1024.png`

## Примечание

В прод-сборке нужно убедиться, что:
- backend зависимости доступны (uvicorn, fastapi, etc.)
- порт выбирается автоматически (логика уже в run_local_agent.py)
- UI открывается автоматически (LOCAL_AGENT_AUTO_OPEN=true)
