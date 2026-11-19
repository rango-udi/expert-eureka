"""Run maintenance and tests inside the Docker application image."""

from pathlib import Path, PurePosixPath
from contextlib import contextmanager
import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.configuration import ensure, load, SECRET_KEYS, atomic_write

PYTHON = Path(sys.executable)


def run(arguments, **kwargs):
    """Run an argument array in the project and preserve a failing child status."""
    environment = kwargs.pop("env", None)
    environment = os.environ.copy() if environment is None else environment.copy()
    environment["PIP_CACHE_DIR"] = str(ROOT / ".runtime/pip-cache")
    return subprocess.run(
        [str(value) for value in arguments],
        cwd=ROOT,
        check=True,
        env=environment,
        **kwargs,
    )


@contextmanager
def command_lock():
    """Hold a cross-platform OS file lock so two commands cannot mutate the same runtime."""
    path = ROOT / ".runtime/command.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    stream.seek(0)
    stream.write(b"0")
    stream.flush()
    stream.seek(0)
    try:
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError(
                "Another cmdc operation is running. Wait for it to finish; do not delete the lock file."
            ) from error
        yield
    finally:
        stream.close()


def stop():
    """Leave lifecycle ownership to the host Docker launcher, which stops writers first."""
    return None


class DjangoStepError(subprocess.CalledProcessError):
    """Preserve the failed Django status together with an actionable initialization diagnostic."""

    def __init__(self, error, step, diagnostic):
        """Keep the child status and safe step label without exposing command arguments."""
        super().__init__(error.returncode, error.cmd)
        self.step = step
        self.diagnostic = diagnostic

    def __str__(self):
        """Explain where initialization stopped and where its full technical output was saved."""
        detail = "Details: " + self.diagnostic if self.diagnostic else "The private diagnostic could not be written. Check folder permissions and the host task log."
        return (f"Wowy initialization step '{self.step}' failed (exit {self.returncode}). "
                "No later initialization step was started. " + detail +
                " After correcting source/configuration, rerun cmdc setup --app wowy; keep .env and existing data.")


def django(*arguments, capture=False):
    """Run Django, saving noninteractive initialization output before reporting a failed stage."""
    load()
    environment = os.environ.copy()
    if arguments and arguments[0] == "test":
        environment["CMDC_TESTING"] = "1"
    if not capture:
        return run([PYTHON, "-m", "django", *arguments], env=environment)
    try:
        result = run([PYTHON, "-m", "django", *arguments], env=environment,
                     capture_output=True, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as error:
        import re

        step = re.sub(r"[^A-Za-z0-9_-]", "_", arguments[0])
        path = ROOT / ".runtime" / ("django-" + step + ".log")
        output = (error.stdout or "") + (error.stderr or "")
        diagnostic = "apps/wowy/.runtime/" + path.name
        try:
            atomic_write(path, output)
        except OSError:
            diagnostic = None
            # The outer quiet-stage task log retains technical output if local logging fails.
            sys.stderr.write(output)
        raise DjangoStepError(error, step, diagnostic) from error
    sys.stdout.write(result.stdout or "")
    sys.stderr.write(result.stderr or "")
    return result


def initialize():
    """Apply real Wowy migrations, seed missing references and collect static assets."""
    stop()
    django("migrate", "--noinput", "--verbosity", "0", capture=True)
    django("seed_demo", capture=True)
    django("collectstatic", "--noinput", "--verbosity", "0", capture=True)


def robot(arguments):
    """Run sequential Robot tests using Chromium already installed in the browser image."""
    values = load()
    environment = os.environ.copy()
    environment["BASE_URL"] = "http://wowy:8000"
    for role in ("ADMIN", "CUSTOMER", "STAFF"):
        for field in ("EMAIL", "PASSWORD"):
            environment[f"ROBOT_{role}_{field}"] = values[f"{role}_{field}"]
    run([PYTHON, "-m", "robot", "--outputdir", ROOT / "reports", *arguments,
         ROOT / "tests/robot"], env=environment)


def remove_directory(path):
    """Remove a project-owned generated directory; unlink a directory link instead of traversing it."""
    path = Path(path)
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        path.unlink() if path.is_symlink() else os.rmdir(path)
    elif path.exists():
        shutil.rmtree(path)


def valid_backup_name(name):
    """Accept only a simple English backup name and reject path traversal before changing files."""
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError(
            "Backup names must use English letters, digits, hyphens or underscores."
        )
    return ROOT / "backups" / (name + ".zip")


def backup(name):
    """Stop writers and archive SQLite plus media; never overwrite an existing backup."""
    target = valid_backup_name(name)
    if target.exists():
        raise ValueError("That backup already exists. Choose a new name.")
    stop()
    target.parent.mkdir(exist_ok=True)
    data = ROOT / ".runtime/data"
    if not (data / "db.sqlite3").exists():
        raise ValueError("No initialized database exists to back up.")
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        archive.write(data / "db.sqlite3", "db.sqlite3")
        for path in (data / "media").rglob("*"):
            if path.is_file() and not path.is_symlink():
                archive.write(path, path.relative_to(data).as_posix())
    print("Backup created: " + str(target) + ". Run cmdc start --app wowy to resume.")


def restore(name):
    """Validate a trusted backup before stopping writers and replacing the database/media."""
    source = valid_backup_name(name)
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() or "db.sqlite3" not in archive.namelist():
            raise ValueError("The backup is damaged or has no database.")
        for item in archive.namelist():
            path = PurePosixPath(item)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in item
                or (item != "db.sqlite3" and not item.startswith("media/"))
            ):
                raise ValueError(
                    "The backup contains an unsafe path. Nothing was restored."
                )
        stop()
        data = ROOT / ".runtime/data"
        remove_directory(data / "media")
        archive.extractall(data)
    django("migrate", "--noinput", "--verbosity", "0", capture=True)
    print("Database and media restored. Run cmdc start --app wowy to resume.")


def parser():
    """Validate maintenance arguments before changing project files."""
    result = argparse.ArgumentParser(description="Container-only Wowy maintenance.")
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("init", "generate", "validate", "versions", "source"):
        commands.add_parser(name)
    command = commands.add_parser("env")
    command.add_argument("action", nargs="?", choices=["init", "show"], default="init")
    commands.add_parser("backup").add_argument("name")
    command = commands.add_parser("restore")
    command.add_argument("name")
    command.add_argument("--yes", action="store_true", required=True)
    command = commands.add_parser("reset")
    command.add_argument("scope", choices=["db", "data", "all"])
    command.add_argument("--yes", action="store_true", required=True)
    command = commands.add_parser("destroy")
    command.add_argument("--yes", action="store_true", required=True)
    command.add_argument("--include-files", action="store_true")
    return result


def main():
    """Require a Docker execution marker and preserve failing command exit codes."""
    try:
        if os.environ.get("CMDC_CONTAINER") != "1" or not Path("/.dockerenv").exists():
            raise ValueError("Use cmdc or cmdc.cmd. All project execution requires Docker.")
        args = sys.argv[1:]
        if args and args[0] in ("robot", "manage"):
            command, extra = args[0], args[1:]
            options = None
        else:
            options = parser().parse_args(args)
            command = options.command
        with command_lock():
            values = ensure()
            load()
            if command == "init":
                initialize()
            elif command == "robot":
                robot(extra)
            elif command == "manage":
                django(*extra)
            elif command == "env":
                if options.action == "show":
                    print("\n".join(f'{key}={"<redacted>" if key in SECRET_KEYS else value}'
                                    for key, value in values.items()))
                else:
                    print("Private configuration ready. Existing values were preserved.")
            elif command == "generate":
                run([PYTHON, ROOT / "scripts/generate_cases.py"])
            elif command == "validate":
                django("check")
                django("makemigrations", "storefront", "--check", "--dry-run", "--verbosity", "0")
                run([PYTHON, "-m", "unittest", "discover", "-s", "tests/cli", "-v"])
                django("test", "tests.integration", "--noinput")
                run([PYTHON, Path("/repository/scripts/check_docs.py")])
                run([PYTHON, Path("/repository/scripts/check_code.py")])
            elif command == "backup":
                backup(options.name)
            elif command == "restore":
                restore(options.name)
            elif command in ("reset", "destroy"):
                scope = options.scope if command == "reset" else "all"
                data = ROOT / ".runtime/data"
                if scope == "db":
                    for path in data.glob("db.sqlite3*"):
                        path.unlink()
                else:
                    remove_directory(data)
                    remove_directory(ROOT / "reports")
                if command == "destroy" and options.include_files:
                    for name in ("backups", "reports"):
                        remove_directory(ROOT / name)
                    (ROOT / ".env").unlink(missing_ok=True)
                print("Selected project data removed. Source and release evidence were kept.")
            elif command == "source":
                print("/opt/wowy")
                print((ROOT / "config/source-lock.json").read_text())
            elif command == "versions":
                import importlib.metadata
                print(json.dumps({name: importlib.metadata.version(name) for name in
                                  ("Django", "djangorestframework", "waitress")}, indent=2))
        return 0
    except DjangoStepError as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return error.returncode or 2
    except subprocess.CalledProcessError as error:
        print(f"ERROR: Step failed (exit {error.returncode}). Review the output above.", file=sys.stderr)
        return error.returncode or 2
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 2
    except Exception:
        import traceback

        diagnostic = ROOT / ".runtime/maintenance-errors.log"
        try:
            diagnostic.parent.mkdir(parents=True, exist_ok=True)
            with diagnostic.open("a", encoding="utf-8") as stream:
                traceback.print_exc(file=stream)
            detail = "Technical details: .runtime/maintenance-errors.log."
        except OSError:
            detail = "A diagnostic file could not be written; check project folder permissions."
        print("ERROR: Container maintenance could not finish. No later step was started. "
              "Run cmdc doctor, review the configuration and retry. " + detail, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
