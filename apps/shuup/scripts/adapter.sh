#!/bin/sh
# Orchestrate Docker directly; never use a host Python or WSL launcher.
set -eu
[ "${CMDC_GUARDED_APP:-}" = shuup ] || { echo "ERROR: Use root cmdc with --app shuup." >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPOSITORY_ROOT=$(CDPATH= cd -- "$ROOT/../.." && pwd)
cd "$ROOT"
export COMPOSE_PARALLEL_LIMIT=1
[ -f "$REPOSITORY_ROOT/scripts/terminal.sh" ] || { printf '%s\n' 'ERROR: Terminal helper is missing. Extract the complete project ZIP.' >&2; exit 2; }
# shellcheck source=terminal.sh
. "$REPOSITORY_ROOT/scripts/terminal.sh"
terminal_init
. "$REPOSITORY_ROOT/scripts/memory_policy.sh"
compose() {
    mkdir -p "$ROOT/.runtime" || fail 'The project folder is not writable. Move it to a writable folder and retry.'
    terminal_stage "$@"
    started=$(date +%s)
    [ -z "$stage_label" ] || terminal_message RUN "$stage_label"
    code=0
    case "$stage_label" in
        'Validate application'|'Generate test cases'|'Run browser tests'|'Export customer report')
            terminal_live "$stage_label" docker compose --project-name robot-web-shuup --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@" || code=$?;;
        'Initialize database and store data'|'Start Shuup and wait for readiness'|'Stop application'|'Remove project containers and network')
            terminal_wait "$stage_label" docker compose --project-name robot-web-shuup --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@" || code=$?;;
        *) docker compose --project-name robot-web-shuup --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@" || code=$?;;
    esac
    finished=$(date +%s)
    if [ "$code" -ne 0 ]; then
        [ -z "$stage_label" ] || terminal_message ERROR "$stage_label (exit $code)"
        case "$*" in
            build\ *) recovery='Build failed. Review Docker build output or docker buildx history logs.';;
            run\ *tools*) recovery='Maintenance failed. Read the diagnostic file printed above and apps/shuup/.runtime/django-<step>.log for initialization failures. Correct source/configuration, then rerun setup --app shuup; keep .env and data.';;
            run\ *robot*) recovery='Browser tests failed. Review the diagnostic output and apps/shuup/reports.';;
            up\ *) recovery='Startup failed. Run cmdc status --app shuup and cmdc logs --app shuup.';;
            *) recovery='Check Docker availability with cmdc doctor, then inspect cmdc status --app shuup.';;
        esac
        fail_with_code "$code" "$recovery"
    fi
    [ -z "$stage_label" ] || terminal_message OK "$stage_label ($((finished - started))s)"
}
fail_with_code() {
    code=$1
    shift
    terminal_message ERROR "$*"
    exit "$code"
}
fail() { fail_with_code 2 "$*"; }

preflight() { check_engine_memory; }

build_app() { preflight; compose build tools; }
build_robot() { preflight; compose build robot; }
require_app() {
    docker image inspect robot-web-shuup-app:3.12.4 >/dev/null 2>&1 || fail 'Application image is missing. Run cmdc setup --app shuup. No image was pulled automatically.'
}
tool() { require_app; compose run --rm --no-deps --pull never tools "$@"; }
start() {
    require_app
    [ -f "$ROOT/.env" ] && [ -f "$ROOT/.runtime/data/db.sqlite3" ] || fail 'Shuup is not initialized. Run cmdc setup --app shuup.'
    [ ! -L "$ROOT/.env" ] && [ ! -L "$ROOT/.runtime/data" ] || fail 'Shuup environment/data paths must not be filesystem links.'
    compose up -d --no-build --pull never --wait shuup; compose port shuup 8000; }
command=${1:-help}
[ "$#" -eq 0 ] || shift
case "$command" in
    help|--help|-h) cat <<'HELP'
Shuup Web Tests - Docker only
setup [--with-robot] [--run-tests [--customer]] | init | start | up | restart | stop | down
robot-init | robot [Robot options...] | validate | generate [--customer | --design-model <YAML-or-JSON> | --legacy] | report [--media] [--results <app-relative file>] | manage <command...>
env [init|show] | config | status | urls | resources | logs
backup <name> | restore <name> --yes | reset <scope> --yes
destroy --yes [--include-files] | source | versions
CMDC_UI=auto|rich|plain controls terminal display. NO_COLOR disables colors.
Engine target and upward tolerance: ../../config/host-memory.env; terminal variables override project values.
HELP
    exit 0;;

esac
command -v docker >/dev/null 2>&1 || fail 'Docker CLI is missing. Install and start Docker with Compose.'
compose version >/dev/null
terminal_wait 'Check Docker Engine' docker info >/dev/null || fail 'Docker Engine is unreachable. Start Docker and check docker info.'
[ "$(docker info --format '{{.OSType}}' 2>/dev/null)" = linux ] || fail 'Switch Docker to Linux containers.'
case "$command" in
    config) compose config; exit 0;;
    status) compose ps; exit 0;;
    urls)
        address=$(compose port shuup 8000)
        printf 'Storefront: http://%s/\nAdministration: http://%s/sa/\n' "$address" "$address"
        exit 0;;
    resources) compose stats --no-stream; exit 0;;
    logs) compose logs --tail 100 shuup; exit 0;;
    stop) compose stop; exit 0;;
    down) compose --profile '*' down --remove-orphans; exit 0;;
esac
mkdir -p .runtime 2>/dev/null || fail 'The project folder is not writable. Move it to a writable folder and retry.'
mkdir .runtime/launcher.lock 2>/dev/null || fail 'Another launcher is running. If a previous terminal crashed, verify no cmdc operation is active before removing .runtime/launcher.lock.'
trap 'rmdir "$ROOT/.runtime/launcher.lock" 2>/dev/null || :' EXIT
trap 'exit 130' INT TERM
case "$command" in
    setup|bootstrap)
        terminal_message INFO "Robot Web Tests | shuup | $command"
        with_robot=0; run_tests=0; customer=0
        for option in "$@"; do
            case "$option" in
                --with-robot) with_robot=1;;
                --run-tests) with_robot=1; run_tests=1;;
                --customer) customer=1;;
                *) fail "Unknown setup option: $option";;
            esac
        done
        [ "$customer" -eq 0 ] || [ "$run_tests" -eq 1 ] || fail 'Use setup --run-tests --customer to select the customer suite.'
        build_app
        compose stop shuup
        tool init
        [ "$with_robot" -eq 0 ] || build_robot
        start
        if [ "$run_tests" -eq 1 ]; then
            if [ "$customer" -eq 1 ]; then compose run --rm --no-deps --pull never robot --customer
            else compose run --rm --no-deps --pull never robot; fi
        fi;;
    start|up) start;;
    restart) compose stop shuup; start;;
    robot-init) build_robot;;
    robot)
        dryrun=0
        for option in "$@"; do [ "$option" != --dryrun ] || dryrun=1; done
        build_robot
        [ "$dryrun" -eq 1 ] || start
        compose run --rm --no-deps --pull never robot "$@";;
    init|backup|restore|reset|manage)
        compose stop shuup
        tool "$command" "$@";;
    destroy)
        confirmed=0
        for option in "$@"; do
            case "$option" in --yes) confirmed=1;; --include-files) :;; *) fail "Unknown destroy option: $option";; esac
        done
        [ "$confirmed" -eq 1 ] || fail 'Use destroy --yes to remove project data.'
        compose --profile '*' down --remove-orphans
        tool destroy "$@"
        compose --profile '*' down --remove-orphans --rmi all;;
    env) build_app; tool env "$@";;
    report) preflight; compose build report; compose run --rm --no-deps --pull never report "$@";;
    validate|generate|source|versions) tool "$command" "$@";;
    *) fail "Unknown command: $command. Run cmdc help.";;
esac
