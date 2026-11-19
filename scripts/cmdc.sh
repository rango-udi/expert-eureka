#!/bin/sh
# Guard one explicit application selection before calling its Docker adapter.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
. "$ROOT/scripts/terminal.sh"
terminal_init
fail() { terminal_message ERROR "$*"; exit 2; }
command=${1:-help}
[ "$#" -eq 0 ] || shift
app=
app_seen=0
accept_pretix_risk=0
accept_resource_risk=0
engine_token=
selected_running=0
remaining=$#
while [ "$remaining" -gt 0 ]; do
    value=$1; shift; remaining=$((remaining - 1))
    case "$value" in
        --accept-resource-risk) [ "$accept_resource_risk" -eq 0 ] || fail 'Use --accept-resource-risk once.'; accept_resource_risk=1;;
        --accept-pretix-risk) [ "$accept_pretix_risk" -eq 0 ] || fail 'Use --accept-pretix-risk once.'; accept_pretix_risk=1;;
        --app)
            [ "$app_seen" -eq 0 ] && [ "$remaining" -gt 0 ] || fail 'Use exactly one --app oscar, --app pretix, --app shuup, --app wowy, --app nopcommerce, --app prestashop or --app woocommerce.'
            app_seen=1; app=$1; shift; remaining=$((remaining - 1));;
        --app=*) [ "$app_seen" -eq 0 ] || fail 'Choose exactly one app.'; app_seen=1; app=${value#--app=};;
        *) set -- "$@" "$value";;
    esac
done
case "$command" in
    help|--help|-h)
        cat "$ROOT/config/COMMAND_HELP.txt"
        exit 0;;
    apps)
        [ -z "$app" ] || fail 'apps is a global command; omit --app.'
        [ "$#" -le 1 ] || fail 'Use apps [--names|--ids|--raw].'
        mode=${1:-table}
        case "$mode" in table|--names|--ids|--raw) :;; *) fail 'Use apps [--names|--ids|--raw].';; esac
        if [ "$mode" = --raw ]; then cat config/apps.list
        else
            awk -F'|' -v mode="$mode" 'BEGIN {if(mode=="table") printf "%-16s %s\n", "APP ID", "NAME"} !/^#/ && NF {if(mode=="--names") print $4; else if(mode=="--ids") print $1; else printf "%-16s %s\n", $1, $4}' config/apps.list
        fi
        exit 0;;
    version) cat VERSION; exit 0;;
    doctor|wsl-vm-limit-help)
        [ -z "$app" ] || fail 'This is a global command; omit --app.'
        exec sh "$ROOT/scripts/system.sh" "$command" "$@";;
    setup|bootstrap|start|up|restart|stop|down|status|urls|resources|logs|diagnostics|init|env|config|robot-init|robot|generate|validate|manage|backup|restore|reset|destroy|source|versions|pull|report) :;;
    *) fail "Unknown command: $command. Run cmdc help.";;
esac
case "$app" in oscar|pretix|shuup|wowy|nopcommerce|prestashop|woocommerce) :;; *) fail 'Choose an application: add --app oscar, --app pretix, --app shuup, --app wowy, --app nopcommerce, --app prestashop or --app woocommerce. See documents/APPS.md.';; esac
[ "$command" != report ] || [ "$app" = shuup ] || fail 'report is supported only for --app shuup.'
case "$app" in nopcommerce|prestashop|woocommerce)
    case "$command" in setup|bootstrap|init|start|up|restart|robot-init|robot|env|validate|status|resources|logs|stop|down|urls|config|versions|source|destroy|diagnostics) :;; *) fail 'Unsupported command for native commerce. See documents/guides/NATIVE_COMMERCE.md. No Docker operation was started.';; esac;;
esac
if [ "$command" = diagnostics ]; then
    [ "$#" -eq 0 ] || fail 'diagnostics takes no options.'
    exec sh "$ROOT/scripts/diagnostics.sh" "$app"
fi
if [ "$command" = destroy ]; then
    case "$app" in nopcommerce|prestashop|woocommerce)
        for option in "$@"; do case "$option" in --yes|--include-files) :;; *) fail 'Use destroy --app <id> --yes [--include-files].';; esac; done;;
    esac
fi
[ "$accept_pretix_risk" -eq 0 ] || [ "$app" = pretix ] || fail '--accept-pretix-risk applies only to Pretix.'
[ "$accept_resource_risk" -eq 0 ] || { case "$app" in nopcommerce|prestashop|woocommerce) :;; *) fail '--accept-resource-risk applies only to native commerce adapters.';; esac; }
case "$app" in nopcommerce|prestashop|woocommerce)
    . "$ROOT/scripts/commerce/resource_safety.sh"
    confirm_commerce_risk;;
esac
# Confirmation and option validation happen before Docker or resource changes.
case "$command" in
    destroy|reset|restore)
        confirmed=0
        for value in "$@"; do [ "$value" != --yes ] || confirmed=1; done
        [ "$confirmed" -eq 1 ] || fail 'Destructive operations require --yes after reviewing their scope.';;
esac
if [ "$app" = pretix ]; then
    . "$ROOT/scripts/pretix_safety.sh"
    confirm_pretix_risk
fi
[ -f "$ROOT/apps/$app/scripts/adapter.sh" ] || fail "The selected adapter is missing. Extract the complete source package."
case "$command" in stop|down|status|resources|logs) :;; *)
    [ -f "$ROOT/fuzcake-data/records/app-profiles.json" ] && [ -f "$ROOT/fuzcake-data/fuzcake_data/__init__.py" ] || fail 'Shared fuzcake-data is missing. Extract the complete source package at the repository root before continuing.'
    [ ! -L "$ROOT/fuzcake-data" ] || fail 'Shared fuzcake-data must be a real source directory, not a filesystem link.';;
esac
if [ "$app" = oscar ] && { [ -e "$ROOT/.env" ] || [ -e "$ROOT/.runtime/data/db.sqlite3" ]; }; then
    fail 'Oscar configuration or data remains at the repository root. Follow documents/guides/MIGRATION.md to move it into apps/oscar before continuing.'
fi
command -v docker >/dev/null 2>&1 || fail 'Docker CLI is missing. Install and start Docker.'
case "$command" in status|resources|logs) mutation=0;; *) mutation=1;; esac
if [ "$mutation" -eq 1 ]; then
    [ ! -L .runtime ] || fail "The workspace runtime path must not be a filesystem link."
    mkdir -p .runtime
    mkdir .runtime/app-operation.lock 2>/dev/null || fail 'Another application operation is running. Wait for it to finish. After a crash, verify that no launcher or task container is active before removing .runtime/app-operation.lock.'
    release_operation() {
        if [ -n "$engine_token" ]; then
            current=$(docker volume inspect --format '{{index .Labels "org.robot-web.owner"}}' robot-web-operation-lock 2>/dev/null || :)
            [ "$current" != "$engine_token" ] || docker volume rm robot-web-operation-lock >/dev/null 2>&1 || :
        fi
        rmdir "$ROOT/.runtime/app-operation.lock" 2>/dev/null || :
    }
    trap 'release_operation' EXIT
    trap 'exit 130' INT TERM
    earlier_locks=$(docker volume ls --format '{{.Name}}') || fail 'Cannot inspect coordinator metadata.'
    for name in $earlier_locks; do
        case "$name" in robot-web-*-operation-lock) fail 'An earlier coordinator lock is present. Finish or recover that operation with its original version.';; esac
    done
    claim=$(mktemp -d "$ROOT/.runtime/claim-XXXXXXXX")
    engine_token="$(basename "$claim")-$$"
    rmdir "$claim"
    docker volume create --label org.robot-web.operation-lock=true --label "org.robot-web.owner=$engine_token" --label "org.robot-web.workspace=$ROOT" robot-web-operation-lock >/dev/null || fail 'Cannot acquire the Docker operation lock. No application was started.'
    current=$(docker volume inspect --format '{{index .Labels "org.robot-web.owner"}}' robot-web-operation-lock) || fail 'Cannot verify operation lock ownership.'
    [ "$current" = "$engine_token" ] || fail 'Another workspace operation owns the engine lock. Wait for it to finish. After an interrupted operation, follow documents/guides/APP_LIFECYCLE.md to inspect and release a stale lock.'
fi
case "$command" in status|resources|logs) :;; *)
    projects=$(docker ps -a --format '{{.Label "org.robot-web.app"}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.project.working_dir"}}|{{.Label "com.docker.compose.oneoff"}}|{{.State}}') || fail 'Cannot inspect running Docker projects. No application was started.'
    while IFS='|' read -r managed project working_dir task state; do
        case "$managed" in oscar|pretix|shuup|wowy|nopcommerce|prestashop|woocommerce) active=$managed;; *)
            case "$project" in robot-web-oscar|robot-web-*-oscar|oscar-*) active=oscar;; robot-web-pretix|robot-web-*-pretix|pretix-*) active=pretix;; robot-web-shuup|robot-web-*-shuup|shuup-*) active=shuup;; robot-web-wowy|robot-web-*-wowy|wowy-*) active=wowy;; robot-web-nopcommerce) active=nopcommerce;; robot-web-prestashop) active=prestashop;; robot-web-woocommerce) active=woocommerce;; *) continue;; esac;;
        esac
        running=0
        case "$state" in running|paused|restarting) running=1;; created|exited|dead|removing) :;; *) fail 'Docker returned incomplete container state metadata.';; esac
        if [ "$active" != "$app" ]; then
            [ "$running" -eq 1 ] || continue
            case "$command" in stop|down) continue;; *) fail "Application $active is still running. Run cmdc down --app $active before selecting $app. No application resources were changed.";; esac
        fi
        [ "$project" = "robot-web-$app" ] || fail 'An earlier project identifier is present. Stop it with its original launcher before using this version.'
        [ "$running" -eq 1 ] || task=
        case "$task:$command" in
            True:stop|true:stop|True:down|true:down) :;;
            True:*|true:*) fail 'An application task is still running. Inspect status and logs; stop it before starting another operation.';;
        esac
        expected="$ROOT/apps/$app"
        [ "$working_dir" = "$expected" ] || fail 'The selected application belongs to another workspace or its ownership could not be verified. Use its original workspace to stop it.'
        [ "$running" -ne 1 ] || selected_running=1
    done <<PROJECTS
$projects
PROJECTS
    ;;
esac

case "$command" in
    setup|bootstrap|start|up|restart|robot|robot-init|init|manage|restore|backup|env|pull|source|generate|validate|report)
        sh "$ROOT/scripts/system.sh" doctor;;
esac

export CMDC_GUARDED_APP=$app
export CMDC_WORKSPACE=$ROOT
export CMDC_SELECTED_RUNNING=$selected_running
private_env="$ROOT/apps/$app/.env"
[ ! -L "$private_env" ] || fail "Application configuration must not be a filesystem link."
has_data=0
case "$app" in oscar|shuup|wowy) [ ! -f "$ROOT/apps/$app/.runtime/data/db.sqlite3" ] || has_data=1;; esac
if [ "$app" = pretix ] && [ "$mutation" -eq 1 ]; then
    volumes=$(docker volume ls --format '{{.Name}}') || fail 'Cannot inspect existing data volume ownership.'
    for suffix in postgres_data redis_data pretix_data pretix_config mail_data; do
        volume="robot-web-pretix_$suffix"
        for existing in $volumes; do
            [ "$existing" = "$volume" ] || continue
            owner=$(docker volume inspect --format '{{index .Labels "org.robot-web.workspace"}}' "$volume") || fail 'Cannot verify data volume ownership.'
            [ "$owner" = "$ROOT" ] || fail 'Pretix data volumes belong to another workspace or have no ownership record. Use the original workspace; no data was changed.'
            has_data=1
        done
    done
fi
case "$app" in nopcommerce|prestashop|woocommerce)
    if [ "$mutation" -eq 1 ]; then
        volumes=$(docker volume ls --format '{{.Name}}') || fail 'Cannot inspect commerce data ownership.'
        for suffix in database_data app_data product_media; do
            volume="robot-web-${app}_$suffix"
            for existing in $volumes; do
                [ "$existing" = "$volume" ] || continue
                owner=$(docker volume inspect --format '{{index .Labels "org.robot-web.workspace"}}' "$volume") || fail 'Cannot verify commerce data ownership.'
                [ "$owner" = "$ROOT" ] || fail 'Commerce data belongs to another workspace or has no ownership record. Use the original workspace; no data was changed.'
                has_data=1
            done
        done
    fi;;
esac
if [ "$has_data" -eq 1 ] && [ ! -f "$private_env" ]; then
    case "$command" in stop|down|status|resources|logs|reset|destroy) :;; *) fail 'Application data already exists but its .env is missing. Restore the saved configuration before continuing; new credentials were not generated.';; esac
fi
terminal_message INFO "Application: $app | Operation: $command"
code=0
if [ "$app" = pretix ] && [ "$command" = robot-init ]; then command=pull; set -- robot; fi
sh "$ROOT/apps/$app/scripts/adapter.sh" "$command" "$@" || code=$?
if [ "$code" -ne 0 ]; then
    terminal_message ERROR "Application $app did not complete $command (exit $code). Inspect status --app $app; use down --app $app before switching applications."
fi
exit "$code"
