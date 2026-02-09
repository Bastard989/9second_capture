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
- собран лаунчер `scripts/launcher.py` (единый для macOS/Windows/Linux)
- при первом запуске лаунчер ставит зависимости в `~/.9second_capture/venv`
- порт выбирается автоматически и открывается локальный UI на `127.0.0.1`

Сборка использует `--onedir` (для `.app/.exe` и Linux-бандла).
