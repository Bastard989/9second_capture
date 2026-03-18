#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

_launcher_main_module = importlib.import_module("apps.launcher.main")

for _name, _value in vars(_launcher_main_module).items():
    if _name.startswith("__"):
        continue
    globals()[_name] = _value


if __name__ == "__main__":
    main()
