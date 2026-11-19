"""Check project Python documentation and English source text without importing the app."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIRECTORIES = frozenset({
    ".runtime", ".venv", "venv", "__pycache__", "node_modules", ".git",
    "reports", "backups", "upstream", "vendor", "dist", "build", "site-packages",
})


def authored_paths(root=ROOT):
    """Select maintained source only, without entering generated or dependency trees."""
    import os

    paths = [root / "cmdc", root / "cmdc.cmd", root / "config/host-memory.env"]
    suffixes = {".py", ".robot", ".html", ".json", ".ps1", ".sh", ".yaml",
                ".env", ".jinja", ".js", ".css", ".php"}
    for folder in ("scripts", "tests", "apps", "config", "fuzcake-data", "test-design"):
        for current, directories, files in os.walk(root / folder, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in GENERATED_DIRECTORIES
                                    and not (Path(current) / name).is_symlink())
            for name in sorted(files):
                if name.startswith(".env") and name != ".env.template":
                    continue
                path = Path(current) / name
                if not path.is_symlink() and (path.suffix in suffixes or name == ".env.template"):
                    paths.append(path)
    return sorted(set(paths))


def main():
    """Inspect authored code only and return a readable failure for missing docstrings or source language."""
    errors = []
    obsolete_name = re.compile(r"(?i)(?<![a-z0-9])l[a]b(?![a-z0-9])")
    paths = authored_paths()
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if obsolete_name.search(path.relative_to(ROOT).as_posix()) or obsolete_name.search(text):
            errors.append(f"{path.relative_to(ROOT)}: use the current project naming convention.")
        if not text.isascii():
            errors.append(f"{path.relative_to(ROOT)}: keep source text in English.")
        if path.suffix == ".py":
            for node in ast.walk(ast.parse(text, filename=str(path))):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not ast.get_docstring(node):
                    errors.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: document {node.name}."
                    )
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Source checks passed: {len(paths)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
