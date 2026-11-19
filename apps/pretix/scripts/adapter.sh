#!/bin/sh
set -eu
[ "${CMDC_GUARDED_APP:-}" = pretix ] || { echo "ERROR: Use the root cmdc with --app pretix." >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PROJECT=robot-web-pretix
REPOSITORY_ROOT=$(CDPATH= cd -- "$ROOT/../.." && pwd)
. "$REPOSITORY_ROOT/scripts/terminal.sh"
terminal_init
# Kept for compatibility with named volumes from the existing setup.
BOOTSTRAP_PYTHON=python:3.12.8-alpine@sha256:ba13ef990f6e5d13014e9e8d04c02a8fdb0fe53d6dccf6e19147f316e6cc3a84

# Report a user-facing usage error to stderr and exit with status 2. Input: message words; output: one actionable error line.
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
# Print the supported commands, options, defaults and cleanup boundaries. No arguments or Docker resources are required.
help() {
cat "$ROOT/config/COMMAND_HELP.txt"
}
# Check Docker CLI, engine connectivity and Compose. Input: none; return: success, or an explanatory usage error.
doctor() {
  case "${WSL_DISTRO_NAME:-}" in
    docker-desktop*) fail 'This is Docker Desktop internal WSL, not a user Linux distribution. Run cmdc.cmd from Windows, or use Ubuntu/Debian with Docker Desktop WSL Integration enabled.' ;;
  esac
  command -v docker >/dev/null 2>&1 || fail 'Docker CLI was not found. Install Docker Engine or Docker Desktop with Compose, then retry.'
  docker info >/dev/null || fail 'Docker Engine is not reachable. Start Docker and check your connection with docker info.'
  docker compose version >/dev/null || fail 'Docker Compose is unavailable. Install or enable the Compose plugin, then retry.'
}
# Run Compose with the fixed project and optional digest override. Input: Compose arguments; return: the original command status.
compose() {
  if [ -f .runtime/compose.resources.yaml ]; then
    set -- -f .runtime/compose.resources.yaml "$@"
  fi
  if [ -f compose.lock.yaml ]; then
    set -- -f compose.lock.yaml "$@"
  fi
  set -- --parallel 1 --project-name "$PROJECT" --env-file .env -f compose.yaml "$@"
  if docker compose "$@"; then
    return 0
  else
    compose_status=$?
    if ! docker info >/dev/null 2>&1; then
      printf '%s\n' 'ERROR: Docker Engine connection was lost. No later startup step was started. Recover Docker Desktop, inspect status/logs and follow documents/helps/PRETIX_RESOURCE_PRESSURE.md. Keep database and media volumes.' >&2
      return "$compose_status"
    fi
    if [ "$compose_status" -eq 137 ]; then
      printf '%s\n' 'ERROR: The process was force-killed (exit 137), possibly by a memory limit. Check Docker OOM details and cmdc config --app pretix; inspect OOMKilled and the project/VM memory budget before retrying. Do not disable limits to bypass resource pressure.' >&2
    fi
    printf '%s\n' 'ERROR: Docker Compose could not complete this step. Review its message above; use cmdc status --app pretix and cmdc logs --app pretix <service> to investigate.' >&2
    return "$compose_status"
  fi
}

# Reuse the pinned configuration helper; pull only when the exact digest is absent.
ensure_bootstrap_image() {
  if docker image inspect "$BOOTSTRAP_PYTHON" >/dev/null 2>&1; then
    terminal_message INFO 'Using cached configuration helper image.'
  else
    docker pull "$BOOTSTRAP_PYTHON"
  fi
}
# Initialize private configuration and writable output directories. Input: project root globals; output: files and directories only.
prepare() {
  environment ensure
  mkdir -p reports backups evidence upstream
  # Browser image runs as pwuser; dedicated disposable output directory only.
  chmod 1777 reports
}
# Resolve one allowed service selection to fixed service names on stdout. Input: selection or all; invalid names exit with status 2.
target() {
  case "${1:-all}" in
    all|pretix) printf '%s\n' 'postgres redis mailpit gateway pretix worker periodic' ;;
    postgres|redis|mailpit|gateway|worker|periodic) printf '%s\n' "$1" ;;
    *) fail "Unknown service: $1" ;;
  esac
}
# Resolve startup dependencies explicitly while keeping cleanup selections narrow.
start_target() {
  case "${1:-all}" in
    all|pretix|worker|periodic)
      printf '%s\n' 'postgres redis mailpit gateway pretix worker'
      mode=$(cat .runtime/periodic-mode) || fail 'Resource plan is missing. Run cmdc env init --app pretix --accept-pretix-risk.'
      if [ "$1" = periodic ] || [ "$mode" = scheduled ]; then printf '%s\n' periodic; fi ;;
    *) target "$1" ;;
  esac
}
# Run one environment-maintenance action in a pinned Python container. Input: action and options; return: its status; no host Python is used.
environment() {
  # The first bootstrap has no plan yet; later helpers use the Python allocation.
  set -- python3 scripts/configuration.py "$@"
  set -- --label org.robot-web.app=pretix --label com.docker.compose.project=robot-web-pretix --label com.docker.compose.service=python --label com.docker.compose.oneoff=True --label "com.docker.compose.project.working_dir=$ROOT" --network none --user "$(id -u):$(id -g)" --volume "$ROOT:/workspace" --workdir /workspace "$BOOTSTRAP_PYTHON" "$@"
  limit=128m; swap_limit=128m
  if [ -f .runtime/bootstrap-memory.args ]; then
    # An existing empty plan deliberately disables project ceilings.
    limit=$(cat .runtime/bootstrap-memory.args)
    swap_limit=$limit
    [ ! -f .runtime/bootstrap-memory-swap.args ] || swap_limit=$(cat .runtime/bootstrap-memory-swap.args)
  fi
  if [ -n "$limit" ]; then
    set -- --memory "$limit" --memory-swap "$swap_limit" "$@"
  fi
  terminal_wait "Prepare pretix configuration" docker run --pull never --rm "$@"
}
# Print the loopback host port for a service and target port. Missing mappings produce empty output without changing resources.
public_port() {
  compose port "$1" "$2" 2>/dev/null | sed -n 's/^127\.0\.0\.1://p' | head -n 1
}
# Read current gateway and Mailpit mappings and persist access URLs. Input: Compose state; output: private endpoint configuration files.
sync_urls() {
  web=$(public_port gateway 18445)
  mail=$(public_port mailpit 8025)
  environment sync --pretix-port "$web" --mailpit-port "$mail"
}
# Print generated access links or a next-step message. Input: endpoint document if present; no resources are changed.
show_urls() {
  environment urls
}
# Remove public containers created by the current start attempt, then refresh endpoint state. Existing public containers are preserved.
cleanup_new_exposure() {
  for service in $NEW_EXPOSURE; do compose rm -s -f "$service" || true; done
  sync_urls || true
}
# Check reachability and the Linux host reserve before starting each service.
check_start_reserve() {
  docker info >/dev/null 2>&1 || fail 'Docker Engine is unavailable. Startup stopped; recover the engine and inspect status before retrying.'
  if [ -r /proc/meminfo ]; then
    available=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
    minimum=$(sed -n 's/^HOST_FREE_MEMORY_MIN_MIB=//p' "$REPOSITORY_ROOT/config/pretix-safety.env")
    case "$minimum" in ''|*[!0-9]*) fail 'Invalid Pretix host reserve policy. Restore config/pretix-safety.env.';; esac
    [ "${#minimum}" -le 7 ] && [ "$minimum" -ge 1 ] && [ "$minimum" -le 1048576 ] || fail 'HOST_FREE_MEMORY_MIN_MIB must be within 1..1048576.' 
    [ -n "$available" ] && [ "$available" -ge "$minimum" ] || fail 'Host RAM reserve fell below the Pretix stop threshold. No later service was started. Inspect status and stop this app when Docker is reachable.'
  fi
}
# Start only one explicit service at a time; Compose dependency fan-out is disabled.
start_one() {
  check_start_reserve
  terminal_message INFO "Start pretix service: $1"
  compose up --no-deps --pull never -d --wait --wait-timeout 600 "$1"
}
# Start a validated service selection after assigning and recording public ports. Return the failing status and clean newly exposed containers on failure.
up() {
  selected=${1:-all}
  services=$(start_target "$selected")
  NEW_EXPOSURE=
  case "$selected" in
    all|pretix) [ "$(cat .runtime/periodic-mode)" != manual ] || compose stop periodic ;;
  esac
  case "$selected" in
    all|pretix|worker|periodic|gateway) exposed='gateway mailpit' ;;
    mailpit) exposed=mailpit ;;
    *) exposed= ;;
  esac
  for service in $exposed; do
    running=$(compose ps --status running -q "$service")
    [ -n "$running" ] || NEW_EXPOSURE="$NEW_EXPOSURE $service"
  done
  if [ -n "$exposed" ]; then
    # Docker binds an available port atomically within PUBLIC_PORT_RANGE.
    for service in $exposed; do
      if start_one "$service"; then :
      else start_status=$?; cleanup_new_exposure; return "$start_status"; fi
    done
    if sync_urls; then :
    else start_status=$?; cleanup_new_exposure; return "$start_status"; fi
  fi
  for service in $services; do
    case " $exposed " in *" $service "*) continue;; esac
    if start_one "$service"; then :
    else start_status=$?; cleanup_new_exposure; return "$start_status"; fi
  done
  [ -z "$exposed" ] || show_urls
}
# Show statistics only for this project's running containers. Never fall back to
# global docker stats when the project has no running containers.
show_resources() {
  ids=$(compose --profile tools ps --status running -q)
  if [ -z "$ids" ]; then
    printf '%s\n' 'No running project containers were found. Run cmdc start --app pretix to measure resource usage.'
    return 0
  fi
  printf '%s\n' 'Project container usage. Memory limits are ceilings, not reserved allocations. Docker Desktop VM memory can also include cache and other projects.'
  if [ "${1:-}" = --watch ]; then
    docker stats $ids
  else
    docker stats --no-stream $ids
  fi
}

# Stop one validated selection and release its public-port containers. Input: selection or all; named data volumes remain intact.
stop_services() {
  services=$(target "${1:-all}")
  compose stop $services
  case "${1:-all}" in
    all|pretix)
      compose rm -f gateway mailpit
      rm -f .runtime/endpoints.json .runtime/ENDPOINTS.md
      ;;
    gateway|mailpit)
      compose rm -f "$1"
      rm -f .runtime/endpoints.json .runtime/ENDPOINTS.md
      ;;
  esac
}

# Stop application writers, migrate the database and seed missing fixtures. Input: project configuration; return: the first failing command status.
init() {
  compose stop pretix worker periodic
  start_one postgres
  start_one redis
  terminal_wait "Migrate pretix database" compose run --pull never --rm --no-deps worker migrate --noinput --verbosity 0
  terminal_wait "Initialize event data" compose run --pull never --rm --no-deps worker shell -c 'exec(open("/workspace/scripts/seed_demo.py").read())'
}
# Fetch or verify the pinned source commit. Input: existing checkout and pinned constants; output: a verified checkout, never an overwritten different tree.
source_code() {
  compose pull --policy missing git
  if [ -d upstream/pretix/.git ]; then
    actual=$(compose run --pull never --rm --no-deps git -C pretix rev-parse HEAD)
    [ "$actual" = 46bd2caea20dc1b97ebd02bcb802996f872e0c66 ] || fail 'The source checkout uses a different commit. Keep your changes separately before replacing it with the pinned version.'
  elif [ -e upstream/pretix ]; then
    fail 'upstream/pretix exists but is not a Git checkout. Move it aside before running cmdc source; it will not be overwritten.'
  else
    compose run --pull never --rm --no-deps git clone --depth 1 --branch v2026.9.2 https://github.com/pretix/pretix.git pretix
    actual=$(compose run --pull never --rm --no-deps git -C pretix rev-parse HEAD)
    [ "$actual" = 46bd2caea20dc1b97ebd02bcb802996f872e0c66 ] || fail 'The downloaded source commit does not match the pinned version. Check upstream/pretix before using it.'
  fi
}
# Delete one named project volume only after ownership-label verification. Input: allowlisted suffix; missing volumes are ignored.
volume_delete() {
  volume="${PROJECT}_$1"
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    owner=$(docker volume inspect --format '{{index .Labels "com.docker.compose.project"}}' "$volume")
    [ "$owner" = "$PROJECT" ] || fail "Refusing to delete a volume owned by another project: $volume"
    docker volume rm "$volume"
  fi
}
# Remove only the fixed generated paths after explicit destroy --include-files authorization. Code, documents and templates are preserved.
remove_generated_files() {
  printf '%s\n' 'Removing generated reports, backups, evidence, the source checkout, runtime state and private environment configuration.'
  rm -rf -- "$ROOT/reports" "$ROOT/backups" "$ROOT/evidence" "$ROOT/upstream" \
    "$ROOT/.runtime" "$ROOT/.env" "$ROOT/scripts/__pycache__" "$ROOT/tests/cli/__pycache__"
}

# Validate a backup identifier for safe path construction. Input: one name; invalid or empty names exit before Docker mutation.
backup_name() {
  case "${1:-}" in ''|*[!A-Za-z0-9_-]*) fail 'Backup names must contain only English letters, numbers, hyphens or underscores; for example before-tests.' ;; esac
}
# Require an explicit --yes token for destructive operations. Input: confirmation token; output: explanatory error when missing.
require_yes() { [ "${1:-}" = --yes ] || fail 'This operation replaces or deletes data. Add --yes only after checking the scope in cmdc help.'; }
cmd=${1:-help}
[ "$#" -eq 0 ] || shift
case "$cmd" in
  help|-h|--help) help; exit 0 ;;
  setup) cmd=bootstrap ;;
  destroy)
    include_files=false
    [ "$#" -ge 1 ] && [ "$1" = --yes ] || fail 'Usage: cmdc destroy --yes [--include-files]. This deletes project runtime data.'
    shift
    if [ "$#" -eq 1 ] && [ "$1" = --include-files ]; then include_files=true; shift; fi
    [ "$#" -eq 0 ] || fail 'Usage: cmdc destroy --yes [--include-files]'
    cmd=reset
    set -- all --yes
    ;;
  doctor) [ "$#" -eq 0 ] || fail 'doctor does not accept options. Run: cmdc doctor'; doctor; exit 0 ;;
  version) [ "$#" -eq 0 ] || fail 'version does not accept options. Run: cmdc version'; cat VERSION; exit 0 ;;
  host-memory) fail 'Run cmdc.cmd host-memory from Windows CMD or PowerShell. This command manages the Windows WSL VM, not Linux containers.' ;;
esac
# Validate before Docker, so invalid/destructive commands have no side effects.
case "$cmd" in
  bootstrap)
    skip_source=true
    run_tests=false
    for option in "$@"; do
      case "$option" in
        --skip-source) skip_source=true ;;
        --run-tests) run_tests=true ;;
        *) fail 'Usage: cmdc setup --app pretix [--skip-source] [--run-tests]' ;;
      esac
    done
    ;;
  source|down|init|generate|validate|status|versions|lock|urls|config) [ "$#" -eq 0 ] || fail "$cmd does not accept options" ;;
  pull) [ "$#" -le 1 ] || fail 'Usage: cmdc pull [server|robot|all]'; case "${1:-server}" in server|robot|all) ;; *) fail 'Usage: cmdc pull [server|robot|all]' ;; esac ;;
  start|up|stop|restart) [ "$#" -le 1 ] || fail "$cmd [service|all]"; target "${1:-all}" >/dev/null ;;
  reset) [ "$#" -eq 2 ] || fail 'reset db|cache|data|all --yes'; case "$1" in db|cache|data|all) ;; *) fail 'Unknown reset scope. Choose db, cache, data or all.' ;; esac; require_yes "$2" ;;
  backup) [ "$#" -eq 1 ] || fail 'backup <name>'; backup_name "$1" ;;
  restore) [ "$#" -eq 2 ] || fail 'restore <name> --yes'; backup_name "$1"; require_yes "$2"
    [ -f "backups/$1/database.dump" ] && [ -f "backups/$1/data.tar.gz" ] || fail 'The backup is incomplete: database.dump and data.tar.gz are both required. Choose a complete backup.' ;;
  env) [ "$#" -le 1 ] || fail "env [init|show]"; case "${1:-init}" in init|show) ;; *) fail "env [init|show]" ;; esac ;;
  resources) [ "$#" -eq 0 ] || { [ "$#" -eq 1 ] && [ "$1" = --watch ]; } || fail "Usage: cmdc resources --app pretix [--watch]" ;;
  manage) [ "$#" -gt 0 ] || fail 'manage <Django command...>' ;;
  robot) ;;
  logs) for service in "$@"; do case "$service" in postgres|redis|mailpit|gateway|pretix|worker|periodic|robot) ;; *) fail "Unknown service: $service" ;; esac; done ;;
  *) fail "Unknown command: $cmd. Run cmdc help to see available commands." ;;
esac
doctor
case "$cmd" in
  bootstrap) ensure_bootstrap_image ;;
  env) [ "${1:-init}" != init ] || ensure_bootstrap_image ;;
esac
case "$cmd" in
  down|stop|status|resources|logs)
    if [ ! -f .env ]; then
      case "$cmd:${CMDC_SELECTED_RUNNING:-0}" in stop:1|down:1) fail 'Pretix is running but its .env file is missing. Restore the saved configuration before cleanup; no successful stop is being claimed.';; esac
      echo 'No pretix configuration exists. No initialization was attempted.'
      exit 0
    fi ;;
  *) prepare ;;
esac
case "$cmd" in
  bootstrap)
    compose --profile tools pull --policy missing postgres redis mailpit gateway pretix worker periodic python
    printf '%s\n' 'Preparing project images and the pinned source checkout.'
    [ "$skip_source" = true ] || source_code
    init
    up all
    echo "Pinned image digests: compose.lock.yaml"
    printf '%s\n' 'Setup completed. Services are ready; use cmdc urls --app pretix to view access links.'
    if [ "$run_tests" = true ]; then compose pull --policy missing robot; sh "$ROOT/scripts/adapter.sh" robot; fi
    ;;
  pull)
    case "${1:-server}" in
      server) compose --profile tools pull --policy missing postgres redis mailpit gateway pretix worker periodic python ;;
      robot) compose --profile tools pull --policy missing robot ;;
      all) compose --profile tools pull --policy missing postgres redis mailpit gateway pretix worker periodic python git robot ;;
    esac
    ;;
  source) source_code ;;
  start|up) up "${1:-all}" ;;
  stop) stop_services "${1:-all}" ;;
  restart) stop_services "${1:-all}"; up "${1:-all}" ;;
  down) compose --profile tools down --remove-orphans; rm -f .runtime/endpoints.json .runtime/ENDPOINTS.md ;;
  env) [ "${1:-init}" != show ] || environment show ;;
  config) environment config ;;
  urls) sync_urls; show_urls ;;
  init) init ;;
  robot)
    dryrun=false
    for arg in "$@"; do [ "$arg" != --dryrun ] || dryrun=true; done
    [ "$dryrun" = true ] || up all
    compose pull --policy missing robot
    compose run --pull never --rm --no-deps --name "${PROJECT}-robot-run" robot --outputdir /workspace/reports "$@" /workspace/tests/robot
    ;;
  generate) compose run --pull never --rm --no-deps python scripts/generate_cases.py ;;
  validate)
    compose --profile tools config --quiet
    compose run --pull never --rm --no-deps python -m unittest discover -s tests/cli -v
    compose run --pull never --rm --no-deps python -m compileall -q scripts tests/cli
    compose run --pull never --rm --no-deps python /repository/scripts/check_docs.py
    compose run --pull never --rm --no-deps python /repository/scripts/check_code.py
    ;;
  status) compose --profile tools ps -a ;;
  resources) show_resources "${1:-}" ;;
  logs) compose logs --tail 150 "$@" ;;
  versions)
    compose --profile tools config --images > evidence/images.txt
    if ! docker image inspect $(cat evidence/images.txt) > evidence/image-inspect.json; then
      printf '%s\n' 'Some images are not cached. Version reporting does not download them.' >&2
    fi
    for report in robot-version browser-version robot-python-version; do
      printf '%s\n' 'Not probed: version reporting does not pull or launch the browser image. See the image lock and Robot run reports.' > "evidence/$report.txt"
    done
    compose run --pull never --rm --no-deps --entrypoint python3 worker --version > evidence/pretix-python-version.txt
    compose run --pull never --rm --no-deps worker --version > evidence/pretix-version.txt
    ;;
  lock)
    # Compose resolves registry digests, including tool profiles. Atomic replacement.
    docker compose --parallel 1 --project-name "$PROJECT" --env-file .env -f compose.yaml --profile tools config --lock-image-digests -o compose.lock.yaml.tmp
    mv compose.lock.yaml.tmp compose.lock.yaml
    ;;
  reset)
    # Clear state before removing images; cleanup must not re-pull an image.
    rm -f .runtime/endpoints.json .runtime/ENDPOINTS.md
    if [ "$1" = all ]; then
      compose --profile tools down --remove-orphans --volumes --rmi all
    elif [ "$1" = data ]; then
      compose --profile tools down --remove-orphans --volumes
    else
      compose --profile tools down --remove-orphans
      case "$1" in db) volume_delete postgres_data ;; cache) volume_delete redis_data ;; esac
    fi
    if [ "${include_files:-false}" = true ]; then remove_generated_files; fi
    printf '%s\n' 'Cleanup completed for the selected project resources. Project code and documents were kept.'
    ;;
  backup)
    [ ! -e "backups/$1" ] || fail 'That backup name already exists. Choose a new name to avoid overwriting it.'
    mkdir "backups/$1"
    chmod 1777 "backups/$1"
    compose stop pretix worker periodic
    compose up --pull never -d --wait postgres
    compose exec -T postgres pg_dump -U pretix -d pretix -Fc -f "/backups/$1/database.dump"
    compose run --pull never --rm --no-deps --entrypoint tar worker -czf "/workspace/backups/$1/data.tar.gz" -C /data .
    printf '%s\n' 'Backup completed: database and uploaded files were saved. Application writers remain stopped. Run cmdc start --app pretix to resume.'
    ;;
  restore)
    environment check-backup --backup "$1"
    compose stop pretix worker periodic
    start_one postgres
  start_one redis
    compose exec -T postgres pg_restore -U pretix -d pretix --clean --if-exists --exit-on-error "/backups/$1/database.dump"
    compose run --pull never --rm --no-deps --entrypoint /bin/sh worker -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -xzf "$1" -C /data' sh "/workspace/backups/$1/data.tar.gz"
    compose exec -T redis redis-cli FLUSHALL
    printf '%s\n' 'Restore completed: database and uploaded files were replaced, and Redis was cleared. Run cmdc start --app pretix to resume.'
    ;;
  manage) compose up --pull never -d --wait postgres redis; compose run --pull never --rm --no-deps worker "$@" ;;
esac
