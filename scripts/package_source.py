"""Build and verify the source ZIP while preserving policies and release history."""
from pathlib import Path
import argparse
import zipfile
from check_preservation import ROOT, check


def package(output):
    """Exclude runtime secrets and require all preserved content before and after packaging."""
    failures = check()
    if failures:
        raise ValueError("\n".join(failures))
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if path.is_symlink():
                raise ValueError("Source links are not package members: " + relative.as_posix())
            historical = relative.as_posix().startswith("documents/updates/archive/")
            if not historical:
                if any(part in (".git", "__pycache__", ".venv", "node_modules") for part in relative.parts):
                    continue
                if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.template"):
                    continue
                if any(part in (".runtime", "reports", "backups", "upstream") for part in relative.parts) and path.name != ".gitkeep":
                    continue
                if path.suffix in (".pyc", ".pyo"):
                    continue
            archive.write(path, "robot-web-tests/" + relative.as_posix())
    failures = check(archive=output)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            failures.append("ZIP integrity check failed.")
    if failures:
        raise ValueError("\n".join(failures))
    return output


def main():
    """Create a versioned artifact using the shared source packaging contract."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    output = options.output or ROOT.parent / ("robot-web-tests-v" + (ROOT / "VERSION").read_text().strip() + ".zip")
    print(package(output))


if __name__ == "__main__":
    main()
