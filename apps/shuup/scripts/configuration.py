"""Create private settings and validate container runtime options using only the standard library."""

from pathlib import Path
import json
import os
import secrets
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = ("SECRET_KEY", "ADMIN_PASSWORD", "CUSTOMER_PASSWORD", "STAFF_PASSWORD")


def parse(text):
    """Return unique KEY=value entries; preserve an explicitly empty value and reject duplicates."""
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("Each environment setting must use KEY=value.")
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            raise ValueError(f"Duplicate environment setting: {key}. Keep one entry.")
        values[key] = value.strip()
    return values


def atomic_write(path, text):
    """Replace a UTF-8 file atomically with owner-only permissions where POSIX supports them."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate(values):
    """Validate web concurrency and explicit Docker memory sizes before saving settings."""
    import re

    if values.get("COUPON_CODE") and not re.fullmatch(r"[A-Za-z0-9_-]{1,12}", values["COUPON_CODE"]):
        raise ValueError("COUPON_CODE must use 1..12 ASCII letters, digits, underscores or hyphens, or be empty.")
    if not values["WEB_THREADS"].isdigit() or not 1 <= int(values["WEB_THREADS"]) <= 16:
        raise ValueError("WEB_THREADS must be 1..16; use 1 for sequential testing.")
    for key in ("APP_MEMORY_LIMIT", "ROBOT_MEMORY_LIMIT"):
        if not re.fullmatch(r"(?:0|[1-9][0-9]*[kKmMgG]?)?", values[key]):
            raise ValueError(f"{key} must be a Docker size such as 384m, 0, or empty.")
    if (
        len({values[key] for key in ("ADMIN_EMAIL", "CUSTOMER_EMAIL", "STAFF_EMAIL")})
        != 3
    ):
        raise ValueError(
            "Admin, customer and staff must use different email addresses."
        )


def validate_generated_paths(root):
    """Refuse linked generated roots so database or cache operations cannot traverse outside the project."""
    for name in (
        ".venv",
        ".runtime",
        ".runtime/data",
        ".runtime/data/db.sqlite3",
        ".runtime/data/media",
        ".runtime/data/search",
        ".runtime/data/static",
        ".runtime/data/mail",
    ):
        path = Path(root) / name
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(
                f"{name} is a filesystem link. Use a real project-owned directory before running this command."
            )


def ensure(root=ROOT):
    """Complete .env from its template, generate missing secrets, and preserve existing preferences."""
    root = Path(root)
    validate_generated_paths(root)
    template_path = root / ".env.template"
    if not template_path.is_file():
        raise ValueError("The .env.template file is missing. Extract the complete project ZIP before running env init.")
    template = template_path.read_text(encoding="utf-8")
    defaults = parse(template)
    path = root / ".env"
    current = parse(path.read_text(encoding="utf-8")) if path.exists() else {}
    values = {**defaults, **current}
    for key in SECRET_KEYS:
        if not values.get(key):
            values[key] = secrets.token_hex(24)
    validate(values)
    if current != values:
        lines = []
        for line in template.splitlines():
            key = (
                line.split("=", 1)[0]
                if "=" in line and not line.startswith("#")
                else None
            )
            lines.append(f"{key}={values[key]}" if key in defaults else line)
        lines.extend(
            f"{key}={value}" for key, value in current.items() if key not in defaults
        )
        atomic_write(path, "\n".join(lines) + "\n")
    return values


def load(root=ROOT):
    """Read validated existing private settings into this process without creating files."""
    validate_generated_paths(Path(root))
    values = parse((Path(root) / ".env").read_text(encoding="utf-8"))
    validate(values)
    os.environ.update(values)
    os.environ["DJANGO_SETTINGS_MODULE"] = "storefront.settings"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"
    temporary = Path(root) / ".runtime/tmp"
    temporary.mkdir(parents=True, exist_ok=True)
    for key in ("TMPDIR", "TMP", "TEMP"):
        os.environ[key] = str(temporary)
    return values


def state(root=ROOT):
    """Read the server identity document, or return None when no valid JSON exists."""
    try:
        return json.loads(
            (Path(root) / ".runtime/server.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None
