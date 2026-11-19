#!/bin/sh
# Shared orchestration for native PHP and .NET storefronts; Docker owns every runtime.
set -eu
app=${CMDC_GUARDED_APP:-}
case "$app" in nopcommerce|prestashop|woocommerce) :;; *) echo 'ERROR: Use root cmdc with a commerce --app selection.' >&2; exit 2;; esac
REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
ROOT="$REPOSITORY_ROOT/apps/$app"
cd "$ROOT"
. "$REPOSITORY_ROOT/scripts/terminal.sh"
terminal_init
. "$REPOSITORY_ROOT/scripts/memory_policy.sh"
export COMPOSE_PARALLEL_LIMIT=1
command=${1:-help}
[ "$#" -eq 0 ] || shift
fail() { terminal_message ERROR "$*"; exit 2; }
case "$command" in setup|bootstrap|init|start|up|restart|robot-init|robot|env|validate)
    compose_version=$(docker compose version --short) || fail 'Docker Compose version could not be read.'
    printf '%s\n' "$compose_version" | awk -F. '{gsub(/^v/, "", $1); if ($1 !~ /^[0-9]+$/ || $2 !~ /^[0-9]+$/ || ($1 < 2 || ($1 == 2 && $2 < 24))) exit 1}' || fail 'Native commerce requires Docker Compose 2.24.0 or newer. No image was prepared.';;
esac
if [ "$app" = nopcommerce ]; then
    case "$command" in setup|bootstrap|init|start|up|restart|robot-init|robot|env|validate)
        architecture=$(docker info --format '{{.Architecture}}') || fail 'Cannot inspect Docker architecture.'
        case "$architecture" in amd64|x86_64) :;; *) fail 'The locked nopCommerce release requires Linux amd64. No image was prepared; use a supported engine or choose another app.';; esac;;
    esac
fi
compose() {
    docker compose --project-name "robot-web-$app" --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@"
}
step() {
    label=$1; shift
    terminal_message RUN "$label"
    result=0
    terminal_wait "$label" docker compose --project-name "robot-web-$app" --project-directory "$ROOT" -f "$ROOT/compose.yaml" "$@" || result=$?
    [ "$result" -eq 0 ] || { terminal_message ERROR "$label failed (exit $result). Run cmdc logs --app $app. Preserve .env and volumes before retrying."; exit "$result"; }
    terminal_message OK "$label"
}
settings() {
    [ ! -L "$ROOT/.runtime" ] || fail 'Runtime must not be a filesystem link.'
    mkdir -p "$ROOT/.runtime"
    chmod 700 "$ROOT/.runtime"
    check_engine_memory
    # Bootstrap has no Docker socket or network; the template is the only settings source.
    docker image inspect python:3.12-slim-bookworm >/dev/null 2>&1 || docker pull python:3.12-slim-bookworm
    terminal_wait 'Create private configuration' docker run --rm --user "$(id -u):$(id -g)" --network none --memory 128m --pids-limit 64 --label "org.robot-web.app=$app" --label "com.docker.compose.project=robot-web-$app" --label "com.docker.compose.project.working_dir=$ROOT" --label com.docker.compose.oneoff=True --mount "type=bind,source=$ROOT,target=/workspace" --mount "type=bind,source=$REPOSITORY_ROOT/scripts/commerce,target=/opt/commerce,readonly" python:3.12-slim-bookworm python /opt/commerce/commands.py env "$app"
}
tool() { step 'Validate shared data' run --rm --no-deps --pull never tools "$@" "$app"; }
require_initialized() { [ -f .env ] && [ -f .runtime/initialized.json ] || fail "Application is not initialized. Run cmdc setup --app $app."; }
initialize() {
    tool validate
    step 'Start private database' up -d --no-build --pull never --wait db
    # The app remains loopback-only; installers must complete before the marker is written.
    step 'Start native application' up -d --no-build --pull never app
    case "$app" in
        nopcommerce) step 'Install and seed nopCommerce' run --rm --no-deps --pull never tools init "$app";;
        prestashop|woocommerce)
            step 'Wait for native application files' up -d --no-build --pull never --wait app
            step 'Stop writers before initialization' stop app
            step 'Install and seed storefront' run --rm --no-deps --pull never --entrypoint php app /opt/adapter/initialize.php;;
    esac
    step 'Verify storefront readiness' up -d --no-build --pull never --wait app
    step 'Record successful initialization' run --rm --no-deps --pull never tools complete "$app"
}
case "$command" in
    setup|bootstrap)
        with_robot=0; run_tests=0
        for option in "$@"; do case "$option" in --with-robot) with_robot=1;; --run-tests) with_robot=1; run_tests=1;; *) fail "Unknown setup option: $option";; esac; done
        check_engine_memory
        settings
        compose pull db
        compose build app tools
        initialize
        if [ "$with_robot" -eq 1 ]; then compose build robot; fi
        if [ "$run_tests" -eq 1 ]; then step 'Read-only browser smoke checks' run --rm --no-deps --pull never robot; fi
        terminal_message OK "Setup completed. Run cmdc urls --app $app.";;
    init) [ "$#" -eq 0 ] || fail 'init takes no options.'; settings; check_engine_memory; initialize;;
    start|up|restart)
        [ "$#" -eq 0 ] || fail 'Startup takes no options.'
        require_initialized; check_engine_memory
        [ "$command" != restart ] || step 'Stop native application' stop app
        step 'Start private database' up -d --no-build --pull never --wait db
        step 'Start native application' up -d --no-build --pull never --wait app;;
    robot-init) settings; check_engine_memory; compose build robot;;
    robot)
        [ "$#" -eq 0 ] || fail 'Native commerce smoke suites take no additional options.'
        require_initialized; check_engine_memory; compose build robot
        step 'Read-only browser smoke checks' run --rm --no-deps --pull never robot;;
    env) [ "$#" -eq 0 ] || { [ "$#" -eq 1 ] && [ "$1" = init ]; } || fail 'Use env init. Read private .env locally to view credentials.'; settings;;
    validate) settings; compose build tools; tool validate;;
    status) compose ps;; resources) compose stats --no-stream;; logs) compose logs --tail 100 app db;;
    stop) step 'Stop application services' stop;;
    down) step 'Remove application containers' --profile '*' down --remove-orphans;;
    destroy)
        confirmed=0; include_files=0
        for option in "$@"; do
            case "$option" in --yes) confirmed=1;; --include-files) include_files=1;; *) fail 'Use destroy --yes [--include-files].';; esac
        done
        [ "$confirmed" -eq 1 ] || fail 'destroy removes the selected database and media. Add --yes after reviewing the scope.'
        [ ! -L "$ROOT/.runtime" ] && [ ! -L "$ROOT/.runtime/initialized.json" ] || fail 'Runtime and marker must not be filesystem links.'
        if [ "$include_files" -eq 1 ]; then
            for path in .env reports backups; do [ ! -L "$ROOT/$path" ] || fail 'Generated file paths must not be filesystem links.'; done
        fi
        volumes=$(docker volume ls --format '{{.Name}}') || fail 'Cannot inspect volumes before destroy.'
        for suffix in database_data app_data product_media; do
            volume="robot-web-${app}_$suffix"
            for candidate in $volumes; do
                [ "$candidate" = "$volume" ] || continue
                owner=$(docker volume inspect --format '{{index .Labels "org.robot-web.workspace"}}' "$volume") || fail 'Cannot verify workspace ownership before destroy.'
                identity=$(docker volume inspect --format '{{index .Labels "org.robot-web.app"}}' "$volume") || fail 'Cannot verify app ownership before destroy.'
                [ "$owner" = "$REPOSITORY_ROOT" ] && [ "$identity" = "$app" ] || fail 'Volume ownership does not match the selected workspace and app. No resources were deleted.'
            done
        done
        step 'Remove selected application and data volumes' --profile '*' down --remove-orphans --volumes
        rm -f "$ROOT/.runtime/initialized.json"
        if [ "$include_files" -eq 1 ]; then
            rm -f "$ROOT/.env"
            rm -rf "$ROOT/reports" "$ROOT/backups"
            mkdir -p "$ROOT/reports"
        fi
        terminal_message OK "Destroyed $app data. Source, shared fuzcake-data, diagnostic logs and image cache were kept.";;
    urls)
        require_initialized
        # Stable public URL is part of native application settings.
        port=$(sed -n 's/^HTTP_PORT=//p' .env)
        case "$port" in ''|*[!0-9]*) fail 'HTTP_PORT must be a numeric port in .env.';; esac
        case "$app" in nopcommerce) admin=Admin;; prestashop) admin=control;; woocommerce) admin=wp-admin;; esac
        printf 'Storefront: http://127.0.0.1:%s/\nAdministration: http://127.0.0.1:%s/%s/\n' "$port" "$port" "$admin";;
    config) compose config --no-interpolate;;
    versions|source) cat config/source-lock.json;;
    *) fail "Command $command is not supported by the native commerce adapter. See documents/guides/NATIVE_COMMERCE.md; no data was changed.";;
esac
