"""Create dotenv configuration and record Docker-assigned public endpoints."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import tempfile
import tarfile
import sys

SECRET_KEYS = {"POSTGRES_PASSWORD", "ADMIN_PASSWORD", "STAFF_PASSWORD"}
PORT_KEYS = {"PRETIX_PUBLIC_PORT", "MAILPIT_PUBLIC_PORT"}


def apply_private_mode(path: Path, mode: int = 0o600) -> None:
    """Apply POSIX file permissions only when the host filesystem supports them.

    Args:
        path: Private configuration or generated state file.
        mode: POSIX permissions for a Linux or POSIX-hosted workspace.
    Returns:
        None. Native Windows bind mounts retain their host NTFS access controls;
        this function does not claim to create a Windows ACL from a Linux chmod.
    """
    if os.environ.get("CMDC_HOST_PLATFORM") != "windows":
        path.chmod(mode)


def validate_public_port(value: str, key: str) -> None:
    """Accept an empty port or a high-range integer; explain how to repair bad input.

    Args:
        value: Port text read from dotenv configuration or Docker output.
        key: Setting name used in diagnostics, never a password or secret value.
    Returns:
        None when valid. Raises ValueError with the setting and recovery command
        when a nonnumeric or out-of-range port is supplied.
    """
    if not value:
        return
    try:
        valid = 49152 <= int(value) <= 65535
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{key} must be empty or an integer port in 49152-65535. Run cmdc urls --app pretix to refresh assigned ports.")


def parse(text: str) -> dict[str, str]:
    """Read a restricted dotenv document without executing shell expressions.

    Args:
        text: UTF-8 configuration text with KEY=value lines and separate comments.
    Returns:
        A mapping of keys to unquoted values; comments are ignored.
    Raises:
        ValueError: A line is malformed, a key is repeated, or JSON quoting is invalid.
    """
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Z][A-Z0-9_]*)=(.*)", line)
        if not match:
            raise ValueError("Configuration contains a malformed line. Use KEY=value and place comments on separate lines.")
        key, value = match.groups()
        if key in values:
            raise ValueError(f"Configuration defines {key} more than once. Keep one value for that key.")
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        values[key] = value
    return values


def write_atomic(path: Path, text: str, mode: int = 0o600) -> None:
    """Replace one UTF-8 file using a flushed temporary file in the same directory.

    Args:
        path: Destination file; its parent directory is created when missing.
        text: Complete replacement content.
        mode: POSIX permissions applied on supported hosts before replacement.
    Returns:
        None. The destination is replaced and temporary files are removed.
    Raises:
        OSError: The directory cannot be created, written, or updated.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        apply_private_mode(Path(temporary), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update(path: Path, changes: dict[str, str], template: str = "") -> None:
    """Apply selected values while preserving existing comments and unrelated keys.

    Args:
        path: Dotenv destination to update atomically.
        changes: Values to write using literal single-quoted dotenv syntax.
        template: Initial document used only when the destination does not exist.
    Returns:
        None. The destination is written with host-appropriate private permissions.
    Raises:
        ValueError: Existing syntax or replacement values cannot be serialized safely.
    """
    text = path.read_text() if path.exists() else template
    existing = parse(text)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        key = line.split("=", 1)[0]
        if key in changes:
            value = changes[key]
            # Compose treats single-quoted dotenv values literally, including $.
            if any(char in value for char in "\n\r'"):
                raise ValueError(f"Cannot write {key}: line breaks and single quotes are not supported in generated values.")
            lines[index] = f"{key}='{value}'"
    for key, value in changes.items():
        if key not in existing:
            if any(char in value for char in "\n\r'"):
                raise ValueError(f"Cannot write {key}: line breaks and single quotes are not supported in generated values.")
            lines.append(f"{key}='{value}'")
    write_atomic(path, "\n".join(lines) + "\n")


def validate_resource_settings(values: dict[str, str]) -> None:
    """Check process counts, maintenance cadence, and PostgreSQL setting syntax.

    Args:
        values: Merged dotenv settings after missing template keys are added.
    Returns:
        None. Raises ValueError naming an invalid setting before writing .env.
        Validation catches input errors; it does not estimate total RAM usage.
    """
    bounds = {
        "WEB_WORKERS": (1, 64),
        "TASK_CONCURRENCY": (1, 64),
        "WEB_THREADS": (1, 64),
        "NATIVE_THREADS": (1, 64),
        "NGINX_WORKERS": (1, 64),
        "NGINX_CONNECTIONS": (64, 65536),
        "ROBOT_SHM_MIB": (64, 4096),
        "PERIODIC_INTERVAL_SECONDS": (60, 3600),
        "PG_MAX_CONNECTIONS": (20, 2000),
    }
    if values["EXECUTION_MODE"] not in {"single", "custom"}:
        raise ValueError("EXECUTION_MODE must be single or custom.")
    if values["TASK_POOL"] not in {"solo", "prefork"}:
        raise ValueError("TASK_POOL must be solo or prefork.")
    if values["PERIODIC_TASKS"] not in {"manual", "scheduled"}:
        raise ValueError("PERIODIC_TASKS must be manual or scheduled.")
    if values["RESTART_POLICY"] not in {"no", "unless-stopped"}:
        raise ValueError("RESTART_POLICY must be no or unless-stopped.")
    swap = values["CONTAINER_SWAP_ALLOWANCE_MIB"]
    if not swap.isdecimal() or not 0 <= int(swap) <= 1048576:
        raise ValueError("CONTAINER_SWAP_ALLOWANCE_MIB must be a whole MiB value from 0 to 1048576.")
    budget = values["MEMORY_BUDGET_MIB"]
    if budget and (not budget.isdecimal() or not 1024 <= int(budget) <= 1048576):
        raise ValueError("MEMORY_BUDGET_MIB must be empty for automatic/unlimited operation, or an integer from 1024 to 1048576 MiB.")
    for key, (minimum, maximum) in bounds.items():
        text = values[key]
        if not text.isdecimal() or not minimum <= int(text) <= maximum:
            raise ValueError(f"{key} must be an integer from {minimum} to {maximum}. Review .env.template before retrying.")
    if values["EXECUTION_MODE"] == "custom" and values["TASK_POOL"] == "solo" and values["TASK_CONCURRENCY"] != "1":
        raise ValueError("The solo task pool is sequential. Use TASK_CONCURRENCY=1 or select prefork in custom mode.")
    for key in ("PG_SHARED_BUFFERS", "PG_WORK_MEM", "PG_MAINTENANCE_WORK_MEM"):
        if not re.fullmatch(r"[1-9][0-9]*(?:kB|MB|GB)", values[key]):
            raise ValueError(f"{key} needs a positive PostgreSQL memory value such as 64MB or 2MB; use kB, MB, or GB units.")


# Reference allocation sums to 1920 MiB for one instance of each service.
MEMORY_SHARES = {
    "gateway": 32, "postgres": 128, "redis": 48, "mailpit": 48,
    "pretix": 384, "worker": 320, "periodic": 256, "robot": 512,
    "python": 128, "git": 64,
}
SINGLE_SETTINGS = {
    "WEB_WORKERS": "1", "WEB_THREADS": "1", "TASK_POOL": "solo",
    "TASK_CONCURRENCY": "1", "NATIVE_THREADS": "1", "NGINX_WORKERS": "1",
    "NGINX_CONNECTIONS": "128", "PG_SHARED_BUFFERS": "32MB",
    "PG_WORK_MEM": "1MB", "PG_MAINTENANCE_WORK_MEM": "16MB", "PG_MAX_CONNECTIONS": "20",
}


def build_resource_plan(values: dict[str, str]) -> dict:
    """Resolve single/custom execution settings and scale per-service memory ceilings.

    Args:
        values: Complete, validated dotenv settings. An empty memory budget means
            no project-imposed RAM ceiling; it never means a zero-byte container.
    Returns:
        Secret-free effective settings and per-instance memory allocations. The
        sum of finite service allocations equals the configured MiB budget exactly.
        This is not a shared cgroup or a cap on Docker Desktop/host memory.
    """
    effective = {key: values[key] for key in SINGLE_SETTINGS}
    if values["EXECUTION_MODE"] == "single":
        effective.update(SINGLE_SETTINGS)
    budget = int(values["MEMORY_BUDGET_MIB"]) if values["MEMORY_BUDGET_MIB"] else None
    limits = {}
    if budget is not None:
        reference = sum(MEMORY_SHARES.values())
        limits = {service: share * budget // reference for service, share in MEMORY_SHARES.items()}
        limits["pretix"] += budget - sum(limits.values())
    return {
        "mode": values["EXECUTION_MODE"], "memory_budget_mib": budget,
        "periodic_tasks": values["PERIODIC_TASKS"], "restart_policy": values["RESTART_POLICY"],
        "container_swap_allowance_mib": int(values["CONTAINER_SWAP_ALLOWANCE_MIB"]),
        "memory_limits_mib": limits, "effective": effective,
        "scope": "Per-instance Compose ceilings; excludes host/VM overhead and extra concurrent one-off containers.",
        "robot_policy": "One named Robot run at a time; the standard suite runs tests sequentially.",
    }


def write_resource_files(root: Path, values: dict[str, str]) -> None:
    """Write a Compose override, effective Nginx files, and a readable resource plan.

    Args:
        root: Project directory with config/nginx.conf and config/gateway.conf.
        values: Complete validated configuration. Source templates are never edited.
    Returns:
        None. Each generated file is replaced atomically under .runtime. JSON is
        used as a YAML-compatible Compose document to avoid a host/package dependency.
        No container is started, restarted, or stopped by this function.
    """
    plan = build_resource_plan(values)
    effective = plan["effective"]
    native = effective["NATIVE_THREADS"]
    native_env = {key: native for key in ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "NUMEXPR_MAX_THREADS")}
    thread_env = dict(native_env)
    thread_env.update({"NUM_WORKERS": effective["WEB_WORKERS"]})
    worker_class = "sync" if effective["WEB_THREADS"] == "1" else "gthread"
    thread_env["GUNICORN_CMD_ARGS"] = f"--worker-class {worker_class} --threads {effective['WEB_THREADS']}"
    task_command = ["taskworker", "--pool", effective["TASK_POOL"], "--concurrency", effective["TASK_CONCURRENCY"], "--prefetch-multiplier", "1"]
    if values["EXECUTION_MODE"] == "single":
        task_command.extend(["--without-gossip", "--without-mingle"])
    services = {
        "pretix": {"environment": thread_env},
        "worker": {"environment": thread_env, "command": task_command},
        "periodic": {"environment": thread_env},
        "robot": {"environment": native_env,
                  "shm_size": f"{values['ROBOT_SHM_MIB']}m"},
        "postgres": {"command": ["postgres", "-c", f"shared_buffers={effective['PG_SHARED_BUFFERS']}",
            "-c", f"work_mem={effective['PG_WORK_MEM']}", "-c", f"maintenance_work_mem={effective['PG_MAINTENANCE_WORK_MEM']}",
            "-c", f"max_connections={effective['PG_MAX_CONNECTIONS']}"]},
    }
    for service in MEMORY_SHARES:
        services.setdefault(service, {})
        services[service].update(restart=plan["restart_policy"], pids_limit=128, cpus=1.0)
        if service in plan["memory_limits_mib"]:
            services[service]["mem_limit"] = f"{plan['memory_limits_mib'][service]}m"
            services[service]["memswap_limit"] = f"{plan['memory_limits_mib'][service] + plan['container_swap_allowance_mib']}m"
    runtime = root / ".runtime"
    for source_name in ("nginx.conf", "gateway.conf"):
        text = (root / "config" / source_name).read_text(encoding="utf-8")
        text = re.sub(r"worker_processes\s+[^;]+;", f"worker_processes {effective['NGINX_WORKERS']};", text)
        text = re.sub(r"worker_connections\s+[0-9]+;", f"worker_connections {effective['NGINX_CONNECTIONS']};", text)
        write_atomic(runtime / source_name, text, mode=0o644)
    write_atomic(runtime / "compose.resources.yaml", json.dumps({"services": services}, indent=2) + "\n")
    write_atomic(runtime / "resource-plan.json", json.dumps(plan, indent=2) + "\n")
    write_atomic(runtime / "periodic-mode", plan["periodic_tasks"] + "\n")
    helper = plan["memory_limits_mib"].get("python")
    write_atomic(runtime / "bootstrap-memory.args", f"{helper}m\n" if helper else "")
    write_atomic(runtime / "bootstrap-memory-swap.args", f"{helper + plan['container_swap_allowance_mib']}m\n" if helper else "")


def print_resource_plan(root: Path) -> None:
    """Print effective execution settings and memory ceilings without exposing secrets.

    Args:
        root: Initialized project directory containing .runtime/resource-plan.json.
    Returns:
        None. English console output distinguishes configured limits from measured RAM.
    """
    plan = json.loads((root / ".runtime/resource-plan.json").read_text(encoding="utf-8"))
    print(f"Execution mode: {plan['mode']}")
    budget = plan["memory_budget_mib"]
    print(f"Memory budget: {budget} MiB, per-instance allocations" if budget else "Memory budget: automatic/unlimited; project memory ceilings are disabled")
    for key, value in plan["effective"].items():
        print(f"  {key}={value}")
    for service, limit in plan["memory_limits_mib"].items():
        print(f"  {service}: {limit} MiB ceiling")
    print(f"Periodic tasks: {plan['periodic_tasks']}; restart policy: {plan['restart_policy']}")
    print(f"Container swap allowance: {plan['container_swap_allowance_mib']} MiB per finite allocation")
    print(plan["scope"])
    print("These are limits, not measured requirements. If a service fails, inspect OOMKilled and logs before changing the project/VM budget; disabling limits can exhaust host RAM.")


def migrate_credential_names(current: dict[str, str]) -> dict[str, str]:
    """Resolve unique older credential suffixes while preserving saved password values."""
    migrated = dict(current)
    obsolete = set()
    for key in ("ADMIN_EMAIL", "ADMIN_PASSWORD", "STAFF_EMAIL", "STAFF_PASSWORD"):
        aliases = [name for name in current if name != key and name.endswith("_" + key)]
        values = {current[name] for name in aliases if current[name]}
        if len(values) > 1 or (values and current.get(key) and current[key] not in values):
            raise ValueError(f"Conflicting saved credentials for {key}. Keep one explicit value before initialization.")
        if not migrated.get(key) and values:
            migrated[key] = values.pop()
        obsolete.update(aliases)
    return {key: value for key, value in migrated.items() if key not in obsolete}


def ensure(root: Path) -> None:
    """Create or complete project configuration without rotating existing passwords.

    Args:
        root: Project directory containing .env.template and the optional .env file.
    Returns:
        None. Missing keys and empty passwords are filled after validation.
    Raises:
        ValueError: A setting conflicts with the supported host, port range, or accounts.
        OSError: The template or destination cannot be accessed.
    """
    for relative in (".runtime", ".env", "backups", "reports", "upstream"):
        if (root / relative).is_symlink():
            raise ValueError(f"{relative} is a filesystem link. Use a real application-owned path.")
    template = (root / ".env.template").read_text()
    defaults = parse(template)
    path = root / ".env"
    saved_text = path.read_text() if path.exists() else ""
    saved_values = parse(saved_text) if saved_text else {}
    current = migrate_credential_names(saved_values)
    renamed_credentials = current != saved_values
    changes = {key: value for key, value in defaults.items() if key not in current}
    for key in SECRET_KEYS:
        if not current.get(key):
            changes[key] = secrets.token_hex(24)
    merged = defaults | current | changes
    validate_resource_settings(merged)
    match = re.fullmatch(r"(\d+)-(\d+)", merged["PUBLIC_PORT_RANGE"])
    if not match or not 49152 <= int(match[1]) <= int(match[2]) <= 65535:
        raise ValueError("PUBLIC_PORT_RANGE must be a range such as 49152-65535. Both endpoints must stay within that high-port range.")
    # Keep the hostname fixed so the browser rule and generated URLs stay aligned.
    if merged["PRETIX_PUBLIC_HOST"] != "pretix.localhost":
        raise ValueError("PRETIX_PUBLIC_HOST must remain pretix.localhost so host and browser-container access use the same address.")
    for key in PORT_KEYS:
        validate_public_port(merged[key], key)
    if merged["ADMIN_EMAIL"] == merged["STAFF_EMAIL"]:
        raise ValueError("Administrator and staff emails must be different. Update ADMIN_EMAIL or STAFF_EMAIL.")
    if renamed_credentials:
        backup = root / ".env.credentials-backup"
        if backup.exists():
            raise ValueError("A credential migration backup already exists. Verify it before retrying initialization.")
        write_atomic(backup, saved_text)
        lines = []
        for line in template.splitlines():
            key = line.split("=", 1)[0] if "=" in line and not line.startswith("#") else None
            lines.append(key + "=" + json.dumps(merged[key]) if key in defaults else line)
        lines.extend(key + "=" + json.dumps(value) for key, value in merged.items() if key not in defaults)
        write_atomic(path, "\n".join(lines) + "\n")
    elif changes or not path.exists():
        update(path, changes, template)
    else:
        apply_private_mode(path)
    write_resource_files(root, merged)


def endpoints(root: Path) -> None:
    """Render access links from recorded public ports, or remove empty endpoint files.

    Args:
        root: Project directory with an initialized .env file.
    Returns:
        None. JSON and Markdown endpoint files are synchronized under .runtime.
    Raises:
        OSError: Configuration or generated files cannot be read or written.
    """
    values = parse((root / ".env").read_text())
    links = {}
    if values.get("PRETIX_PUBLIC_PORT"):
        base = f"http://{values['PRETIX_PUBLIC_HOST']}:{values['PRETIX_PUBLIC_PORT']}"
        links |= {"shop": base + "/demo-organizer/", "control": base + "/control/"}
    if values.get("MAILPIT_PUBLIC_PORT"):
        links["mailpit"] = f"http://localhost:{values['MAILPIT_PUBLIC_PORT']}"
    runtime = root / ".runtime"
    if not links:
        for name in ("endpoints.json", "ENDPOINTS.md"):
            (runtime / name).unlink(missing_ok=True)
        return
    write_atomic(runtime / "endpoints.json", json.dumps(links, indent=2) + "\n")
    template = "[NAVIGATION](../../../documents/NAVIGATION.md)\n\n# Pretix access links\n\n{{ENDPOINT_LINKS}}\n\n[NAVIGATION](../../../documents/NAVIGATION.md)\n"
    link_list = "\n".join(f"- [{key}]({url})" for key, url in links.items())
    text = template.replace("{{ENDPOINT_LINKS}}", link_list)
    write_atomic(runtime / "ENDPOINTS.md", text)


def validate_backup_archive(root: Path, name: str) -> None:
    """Reject unsafe archive paths, links and special files before restore mutates database/media."""
    if not name or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Choose a simple backup name.")
    folder = root / "backups" / name
    source = folder / "data.tar.gz"
    database = folder / "database.dump"
    if any(path.is_symlink() for path in (root / "backups", folder, source, database)):
        raise ValueError("Backup paths must not be filesystem links.")
    if not database.is_file():
        raise ValueError("The backup is missing its database dump.")
    with tarfile.open(source, "r:gz") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or "\\" in member.name or not (member.isfile() or member.isdir()):
                raise ValueError("The backup contains an unsafe member. No database or media was restored.")


def main() -> int:
    """Parse command-line arguments and perform one environment maintenance action.

    Input comes from argv and project configuration files. Actions update only
    configuration and endpoint files; they never change Docker resources.
    Returns:
        Zero on success, or two after an actionable configuration error.
    """
    parser = argparse.ArgumentParser(description="Create project configuration, preserve passwords, and refresh recorded access ports.")
    parser.add_argument("action", choices=["ensure", "sync", "clear", "show", "urls", "config", "check-backup"], help="Configuration action; no Docker resources are changed.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Project directory containing .env.template.")
    parser.add_argument("--pretix-port", help="Assigned pretix host port, or an empty value to clear it.")
    parser.add_argument("--mailpit-port", help="Assigned Mailpit host port, or an empty value to clear it.")
    parser.add_argument("--backup", help="Validated backup name for archive inspection.")
    parser.add_argument("--scope", choices=["all", "gateway", "mailpit"], default="all", help="Endpoint state to clear; default: all.")
    args = parser.parse_args()
    try:
        ensure(args.root)
        if args.action == "check-backup":
            validate_backup_archive(args.root, args.backup)
        elif args.action == "sync":
            changes = {}
            for key, value in (("PRETIX_PUBLIC_PORT", args.pretix_port), ("MAILPIT_PUBLIC_PORT", args.mailpit_port)):
                if value is not None:
                    validate_public_port(value, key)
                    changes[key] = value
            update(args.root / ".env", changes)
            endpoints(args.root)
        elif args.action == "clear":
            keys = PORT_KEYS if args.scope == "all" else {
                "PRETIX_PUBLIC_PORT" if args.scope == "gateway" else "MAILPIT_PUBLIC_PORT"}
            update(args.root / ".env", dict.fromkeys(keys, ""))
            endpoints(args.root)
        elif args.action == "config":
            print_resource_plan(args.root)
        elif args.action == "show":
            values = parse((args.root / ".env").read_text())
            print("\n".join(f"{key}={'<redacted>' if key in SECRET_KEYS else value}"
                            for key, value in values.items()))
        elif args.action == "urls":
            path = args.root / ".runtime/endpoints.json"
            links = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if links:
                print("Service access links (published ports; use cmdc status --app pretix to check health):")
                labels = {"shop": "Ticket shop", "control": "Administration", "mailpit": "Test email inbox"}
                for key, url in links.items():
                    print(f"  {labels[key]}: {url}")
            else:
                print("No service access ports are published. Run cmdc start --app pretix, then cmdc urls --app pretix.")
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        print(f"ERROR: Project configuration could not be updated. {error}", file=sys.stderr)
        print("Review .env.template and your private .env file, correct the setting, and retry cmdc env init --app pretix.", file=sys.stderr)
        return 2
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
