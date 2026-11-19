#!/bin/sh
# Global engine and help commands never initialize an application adapter.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
REPOSITORY_ROOT=$ROOT
cd "$ROOT"
. "$ROOT/scripts/terminal.sh"
terminal_init
fail() { terminal_message ERROR "$*"; exit 2; }
. "$ROOT/scripts/memory_policy.sh"
command=${1:-doctor}
[ "$#" -le 1 ] || fail 'Global commands do not accept application options.'
case "$command" in
    wsl-vm-limit-help)
        guide="$ROOT/documents/helps/WSL_VM_MEMORY_LIMIT.md"
        [ -f "$guide" ] || fail 'The memory guide is missing. Extract the complete source package.'
        printf 'Help file: %s\nHelp link: file://%s\n' "$guide" "$guide"
        exit 0;;
    doctor)
        command -v docker >/dev/null 2>&1 || fail 'Docker CLI is missing. Install and start Docker.'
        type=$(terminal_wait 'Check Docker Engine' docker info --format '{{.OSType}}') || fail 'Docker is unreachable. Start the engine and retry.'
        [ "$type" = linux ] || fail 'Select Linux containers.'
        docker compose version
        check_engine_memory;;
    *) fail 'Use doctor or wsl-vm-limit-help.';;
esac
