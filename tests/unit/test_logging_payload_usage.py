import ast
from pathlib import Path


LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}


def _source_roots() -> list[Path]:
    root = Path(__file__).resolve().parents[2]
    return [root / "apps", root / "src", root / "scripts"]


def _iter_python_files():
    for base in _source_roots():
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


def _looks_like_logging_call(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in LOG_METHODS:
        return False
    base = func.value
    if isinstance(base, ast.Name):
        return "log" in base.id.lower()
    if isinstance(base, ast.Call):
        return True
    return False


def test_logging_calls_do_not_pass_payload_as_direct_keyword() -> None:
    violations: list[str] = []

    for path in _iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not _looks_like_logging_call(node):
                continue
            if any(kw.arg == "payload" for kw in node.keywords):
                violations.append(f"{path}:{node.lineno}")

    assert not violations, "Direct payload= is not allowed in logging calls: " + ", ".join(violations)
