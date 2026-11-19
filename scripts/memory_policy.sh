# Shared engine memory validation; application budgets remain separate.
check_engine_memory() {
    total=$(terminal_wait 'Check Docker Engine' docker info --format '{{.MemTotal}}') || fail 'Docker Engine information is unavailable. Start Docker and retry cmdc doctor.'
    case "$total" in ''|*[!0-9]*) fail 'Docker returned an unreadable RAM size. No image preparation was started. Retry cmdc doctor.';; esac
    [ "${#total}" -le 15 ] && [ "$total" -gt 0 ] || fail 'Docker returned an invalid RAM size. Retry cmdc doctor.' 
    policy="$REPOSITORY_ROOT/config/host-memory.env"
    [ -f "$policy" ] || fail 'Memory policy is missing. Restore config/host-memory.env.'
    policy_values=$(awk '
        { sub(/\r$/, "") }
        /^[[:space:]]*#/ || /^[[:space:]]*$/ { next }
        {
            if ($0 !~ /^(HOST_MEMORY_TARGET_MIB|HOST_MEMORY_TOLERANCE_MIB)=[0-9]+$/) exit 2
            split($0, parts, "=")
            if (seen[parts[1]]++) exit 2
            values[parts[1]] = parts[2]
        }
        END {
            if (!seen["HOST_MEMORY_TARGET_MIB"] || !seen["HOST_MEMORY_TOLERANCE_MIB"]) exit 2
            print values["HOST_MEMORY_TARGET_MIB"], values["HOST_MEMORY_TOLERANCE_MIB"]
        }' "$policy") || fail 'Invalid memory policy. Keep one whole-number value per key in config/host-memory.env.'
    default_target=${policy_values%% *}
    default_tolerance=${policy_values#* }
    target=${HOST_MEMORY_TARGET_MIB:-${HOST_MEMORY_MAX_MIB:-$default_target}}
    tolerance=${HOST_MEMORY_TOLERANCE_MIB:-$default_tolerance}
    for number in "$target" "$tolerance"; do
        case "$number" in ''|*[!0-9]*|0[0-9]*) fail 'Memory target and tolerance must be whole numbers without leading zeros.';; esac
        [ "${#number}" -le 7 ] && [ "$number" -le 1048576 ] || fail 'Memory target and tolerance must be within 0..1048576 MiB.'
    done
    [ "$target" -gt 0 ] || fail 'HOST_MEMORY_TARGET_MIB must be positive.'
    ceiling=$((target + tolerance))
    reported=$(((total + 1048575) / 1048576))
    echo "Engine reports $reported MiB. Memory policy: target $target MiB; upward tolerance $tolerance MiB; accepted maximum $ceiling MiB."
    if [ "$total" -gt "$((ceiling * 1048576))" ]; then
        fail "Image preparation blocked: Docker Engine reports $reported MiB; the accepted maximum is $ceiling MiB (target $target MiB + tolerance $tolerance MiB).
No image preparation was started.
Next step: run sh cmdc wsl-vm-limit-help. Adjust the VM limit or the project memory policy, restart Docker if its VM settings changed, then retry."
    fi
    if [ "$total" -lt "$((target * 1048576))" ]; then
        terminal_message WARNING "Engine RAM is below the nominal target ($reported MiB available; target $target MiB). Preparation may continue; check workload memory if it fails."
    fi
}
