# Require informed per-invocation consent before resource-heavy Native commerce operations.
confirm_commerce_risk() {
    case "$command" in
        setup|bootstrap|start|up|restart|init|robot-init|robot|pull|source|env|manage|backup|restore|validate|generate) :;;
        *) return 0;;
    esac
    terminal_message WARNING 'Native commerce starts several services and may exhaust host RAM or saturate disk during pull, unpack, migration and startup. Container ceilings and WSL cache reclaim do not guarantee host stability.'
    terminal_message WARNING 'Review documents/guides/NATIVE_COMMERCE.md. Stop other workloads and check the active VM limit before continuing.'
    policy="$ROOT/config/commerce-safety.env"
    [ -f "$policy" ] || fail 'Native commerce safety policy is missing. Restore config/commerce-safety.env.'
    minimum=$(awk '
        /^[[:space:]]*(#|$)/ {next}
        /^HOST_FREE_MEMORY_MIN_MIB=[0-9]+$/ { if (seen++) exit 1; split($0,p,"="); value=p[2]; next }
        {exit 1}
        END {if (seen != 1 || value < 1 || value > 1048576) exit 1; print value}
    ' "$policy") || fail 'Invalid Native commerce safety policy. Set one positive HOST_FREE_MEMORY_MIN_MIB value.'
    if [ -r /proc/meminfo ]; then
        available=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
        case "$available" in ''|*[!0-9]*) fail 'Host available RAM could not be read. Check /proc/meminfo before retrying.';; esac
        terminal_message INFO "Host available RAM: $available MiB; stop threshold: $minimum MiB. This is not a workload fit guarantee."
        [ "$available" -ge "$minimum" ] || fail 'Not enough host RAM reserve for Native commerce. Free memory or choose another app; the risk acknowledgement does not bypass this check.'
    else
        terminal_message WARNING 'Host free RAM is not available through /proc/meminfo. Verify it with the host operating system before proceeding.'
    fi
    [ -z "${WSL_DISTRO_NAME:-}" ] || terminal_message WARNING 'Linux MemAvailable describes the WSL guest, not Windows free RAM. Check Windows Task Manager separately.'
    if [ "$accept_resource_risk" -ne 1 ]; then
        if [ -z "${CI:-}" ] && [ -t 0 ] && [ -t 2 ]; then
            printf "Type $app to continue this operation, or press Enter to cancel: " >&2
            answer=
            read -r answer || :
            [ "$answer" = "$app" ] || fail 'Native commerce operation cancelled. No Docker operation was started.'
        else
            fail 'Native commerce requires explicit confirmation. Review the resource warning, then add --accept-resource-risk for this operation. No Docker operation was started.'
        fi
    fi
}
