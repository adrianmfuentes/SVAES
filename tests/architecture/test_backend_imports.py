import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[2] / "api" / "src"
FORBIDDEN = {
    "bootstrap", "core", "infrastructure", "fastapi", "sqlalchemy", "httpx", "cryptography",
    "pyotp", "segno", "reportlab", "croniter",
}


def test_inner_layers_use_ports_for_infrastructure():
    violations = []
    for path in SOURCE.rglob("*.py"):
        relative = path.relative_to(SOURCE)
        if not {"application", "domain"}.intersection(relative.parts[:-1]):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if FORBIDDEN.intersection(module.split(".")):
                    violations.append(f"{relative}:{node.lineno}: {module}")

    assert not violations, "\n".join(sorted(violations))


def test_feature_adapters_do_not_import_other_features_adapters():
    violations = []
    for path in (SOURCE / "features").glob("*/infrastructure/**/*.py"):
        relative = path.relative_to(SOURCE)
        feature = relative.parts[1]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                parts = module.split(".")
                if len(parts) >= 3 and parts[0] == "features" and parts[2] == "infrastructure" and parts[1] != feature:
                    violations.append(f"{relative}:{node.lineno}: {module}")

    assert not violations, "\n".join(sorted(violations))
