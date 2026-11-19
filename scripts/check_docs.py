"""Check navigation boundaries and relative Markdown links without network access."""

from __future__ import annotations

from pathlib import Path
import os
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def documents(root: Path = ROOT) -> list[Path]:
    """Collect repository Markdown documents and the project license.

    Args:
        root: Repository directory to inspect, excluding downloaded upstream files.
    Returns:
        A sorted list of project-authored documents; generated results are excluded.
    """
    paths = list(root.glob("*.md"))
    if (root / "LICENSE").exists():
        paths.append(root / "LICENSE")
    paths.extend(path for path in (root / "documents").rglob("*.md")
                 if "archive/snapshot/" not in path.relative_to(root).as_posix())
    paths.extend((root / ".local").glob("*.md"))
    return sorted(paths)


def check(root: Path = ROOT) -> tuple[list[Path], list[str]]:
    """Validate navigation boundaries, link destinations, and public-document scope.

    Args:
        root: Repository directory with NAVIGATION.md and project documentation.
    Returns:
        The inspected paths and readable errors. The function never edits files
        or accesses the network, so callers can use it in tests and CI checks.
    """
    errors = []
    for name in ("PRINCIPLES.md", "INTERFACE_DESIGN.md", "MOCK_DATA.md"):
        if (root / ".local").exists() and not (root / ".local" / name).is_file():
            errors.append("Missing project policy: .local/" + name)
        if (root / "documents/guides" / name).exists():
            errors.append("Project policy belongs only in .local/: " + name)
    paths = documents(root)
    for path in paths:
        text = path.read_text(encoding="utf-8").strip()
        if root / ".local" not in path.parents and re.search(r"(?<![\w-])\.local(?:/|(?![\w-]))", text):
            errors.append(f"{path.relative_to(root)}: keep internal project metadata out of public documentation.")
        nav = Path(os.path.relpath(root / "documents/NAVIGATION.md", path.parent)).as_posix()
        expected = f"[NAVIGATION]({nav})"
        if not text.startswith(expected) or not text.endswith(expected):
            errors.append(
                f"{path.relative_to(root)}: add a link to the main NAVIGATION.md on the first and last lines"
            )
        evergreen = path.suffix == ".md" and path.stem == path.stem.upper()
        if evergreen:
            style_patterns = (
                r"(?<!\w)(?:ch\u1eeba|n\u00e9)(?!\w)",
                r"trong b\u1ea3n ph\u00e1t h\u00e0nh n\u00e0y",
                r"(?:ch\u01b0a c\u00f3 s\u1ed1 \u0111o|ch\u01b0a x\u00e1c minh|ch\u01b0a \u0111\u01b0\u1ee3c ch\u1ee9ng minh).*?(?:Docker|Windows|m\u00f4i tr\u01b0\u1eddng)",
            )
            for pattern in style_patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    errors.append(
                        f"{path.relative_to(root)}: use neutral reference wording; keep release-specific evidence in dated update records."
                    )
        # Code fences contain copyable commands, not documentation links.
        prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^)]+)\)", prose):
            target = match[1].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            dest = path.parent / unquote(parsed.path)
            if not dest.exists():
                try:
                    relative = dest.resolve().relative_to(root.resolve()).as_posix()
                except ValueError:
                    relative = ""
                if any(relative.startswith(prefix + "/") and not (root / prefix).exists()
                       for prefix in ("documents/updates", "evidence")):
                    continue
                errors.append(
                    f"{path.relative_to(root)}: linked file {target} does not exist. Update the link or restore the file."
                )
    return paths, errors


if __name__ == "__main__":
    checked, errors = check()
    if errors:
        raise SystemExit("Documentation check failed:\n" + "\n".join(errors))
    print(f"Documentation checks PASS: {len(checked)} documents")
