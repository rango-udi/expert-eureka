"""Verify required policy files and immutable historical source snapshots."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def required_files(root=ROOT):
    """Read the explicit preservation contract without importing application code."""
    source = json.loads((root / "config/package-preservation.json").read_text())
    local_only = source.get("local_only_directories", [])
    def available(name):
        """Allow omitted local-only directories in a Git checkout, but validate any present directory."""
        return not any(name.startswith(prefix + "/") and not (root / prefix).exists() for prefix in local_only)
    required = {name: None for name in source["required_files"] if available(name)}
    manifest = root / "documents/updates/archive/preservation.json"
    archive = json.loads(manifest.read_text()) if manifest.exists() else {"files": {}}
    required.update({"documents/updates/archive/" + name: digest for name, digest in archive["files"].items()})
    return required


def check(root=ROOT, archive=None):
    """Check real source files or the final ZIP against the same preservation manifest."""
    errors = []
    required = required_files(root)
    package = zipfile.ZipFile(archive) if archive else None
    try:
        for name, digest in required.items():
            path = root / name
            if path.is_symlink() or root.resolve() not in path.resolve().parents:
                errors.append("Unsafe preserved path: " + name)
                continue
            try:
                data = package.read("robot-web-tests/" + name) if package else path.read_bytes()
            except (KeyError, OSError):
                errors.append("Missing preserved file: " + name)
                continue
            if digest and hashlib.sha256(data).hexdigest() != digest:
                errors.append("Historical content differs from its original snapshot: " + name)
    finally:
        if package:
            package.close()
    return errors


if __name__ == "__main__":
    failures = check()
    if failures:
        raise SystemExit("\n".join(failures))
    print("Preservation checks passed: project policies and immutable historical files.")
