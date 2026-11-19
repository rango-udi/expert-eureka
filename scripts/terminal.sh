#!/bin/sh
# Keep Docker attached to the terminal and add compact command-stage indicators.
terminal_init() {
    ui_mode=${CMDC_UI:-rich}
    case "$ui_mode" in auto|rich|plain) :;; *) printf '%s\n' 'ERROR: CMDC_UI must be auto, rich or plain.' >&2; exit 2;; esac
    rich_terminal=0
    if [ "$ui_mode" = rich ] && [ -t 1 ] && [ -t 2 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${CI:-}" ]; then rich_terminal=1; fi
    if [ "$ui_mode" = auto ] && [ -t 1 ] && [ -t 2 ] && [ "${TERM:-dumb}" != dumb ] && [ -z "${CI:-}" ]; then rich_terminal=1; fi
    if [ "${NO_COLOR+x}" = x ]; then rich_terminal=0; fi
    export BUILDKIT_TTY_LOG_LINES=${BUILDKIT_TTY_LOG_LINES:-6}
    if [ "$rich_terminal" -eq 1 ]; then
        export COMPOSE_ANSI=always COMPOSE_PROGRESS=tty BUILDKIT_PROGRESS=tty
    else
        export COMPOSE_ANSI=never COMPOSE_PROGRESS=plain BUILDKIT_PROGRESS=plain
    fi
}
terminal_message() {
    kind=$1
    shift
    if [ "$rich_terminal" -eq 1 ]; then
        case "$kind" in RUN|INFO) color=36;; OK) color=32;; ERROR) color=31;; *) color=33;; esac
        printf '\033[%sm[%s]\033[0m %s\n' "$color" "$kind" "$*" >&2
    else
        printf '[%s] %s\n' "$kind" "$*" >&2
    fi
}
terminal_stage() {
    case "$*" in
        'build tools') stage_label='Build application image';;
        'build robot') stage_label='Build browser image';;
        *'tools init') stage_label='Initialize database and store data';;
        *'tools validate'*) stage_label='Validate application';;
        *'tools generate'*) stage_label='Generate test cases';;
        run*' report'*) stage_label='Export customer report';;
        run*' robot'*) stage_label='Run browser tests';;
        *'--wait shuup') stage_label='Start Shuup and wait for readiness';;
        *'--wait wowy') stage_label='Start Wowy and wait for readiness';;
        *'--wait oscar') stage_label='Start Oscar and wait for readiness';;
        'stop oscar'|'stop shuup'|'stop wowy'|'stop') stage_label='Stop application';;
        *'down --remove-orphans'*) stage_label='Remove project containers and network';;
        'run '*) stage_label='Run container task';;
        *) stage_label='';;
    esac
}

terminal_live() (
    # Serialize log output and the waiting row in one loop so neither overwrites the other.
    live_label=$1
    shift
    mkdir -p "$ROOT/.runtime"
    live_log=$(mktemp "$ROOT/.runtime/task-XXXXXX.log")
    live_child=
    live_cleanup() {
        [ -z "$live_child" ] || { kill "$live_child" 2>/dev/null || :; wait "$live_child" 2>/dev/null || :; }
        if [ "$rich_terminal" -eq 1 ]; then printf '\r\033[2K\033[?25h' >&2; fi
    }
    trap 'live_cleanup' EXIT
    trap 'exit 130' INT TERM
    COMPOSE_ANSI=never COMPOSE_PROGRESS=plain BUILDKIT_PROGRESS=plain "$@" >"$live_log" 2>&1 &
    live_child=$!
    live_started=$(terminal_clock_ms)
    live_printed=0
    live_frame=0
    if [ "$rich_terminal" -eq 1 ]; then printf '\033[?25l' >&2; fi
    while kill -0 "$live_child" 2>/dev/null; do
        live_lines=$(wc -l < "$live_log")
        if [ "$live_lines" -gt "$live_printed" ]; then
            if [ "$rich_terminal" -eq 1 ]; then printf '\r\033[2K' >&2; fi
            sed -n "$((live_printed + 1)),${live_lines}p" "$live_log"
            live_printed=$live_lines
        fi
        if [ "$rich_terminal" -eq 1 ]; then
            case "$live_frame" in 0) live_glyph='|';; 1) live_glyph='/';; 2) live_glyph='-';; *) live_glyph='\';; esac
            live_now=$(terminal_clock_ms)
            terminal_wait_frame "$live_glyph" "$live_label" "$((live_now - live_started))"
            live_frame=$(((live_frame + 1) % 4))
        fi
        sleep 0.12
    done
    live_code=0
    wait "$live_child" || live_code=$?
    live_child=
    if [ "$rich_terminal" -eq 1 ]; then printf '\r\033[2K' >&2; fi
    # Include a final unterminated line as well as complete lines written during the last poll.
    sed -n "$((live_printed + 1)),\$p" "$live_log"
    if [ -s "$live_log" ] && [ -n "$(tail -c 1 "$live_log")" ]; then printf '\n'; fi
    if [ "$live_code" -ne 0 ]; then printf 'Diagnostic output: %s\n' "$live_log" >&2; fi
    exit "$live_code"
)

terminal_clock_ms() {
    # Linux uptime is monotonic; other POSIX hosts fall back to wall-clock seconds.
    if [ -r /proc/uptime ]; then awk '{printf "%.0f\n", $1 * 1000}' /proc/uptime
    else printf '%s000\n' "$(date +%s)"; fi
}

terminal_wait_frame() {
    # Reserve the rightmost cells for monotonic stage duration and avoid line wrapping.
    glyph=$1; label=$2; elapsed=$3
    columns=$(stty size 2>/dev/null < /dev/tty | awk '{print $2}') || columns=
    case "$columns" in ''|*[!0-9]*) columns=${COLUMNS:-80};; esac
    case "$columns" in ''|*[!0-9]*) columns=80;; esac
    [ "$columns" -ge 24 ] || columns=24
    seconds=$((elapsed / 1000)); fraction=$(((elapsed % 1000) / 100))
    timer="${seconds}.${fraction}s"
    available=$((columns - ${#timer} - 7))
    short=$(printf '%s' "$label" | cut -c "1-$available")
    padding=$((columns - ${#short} - ${#timer} - 5))
    [ "$padding" -ge 1 ] || padding=1
    printf '\r\033[2K\033[36m[%s]\033[0m %s%*s%s' "$glyph" "$short" "$padding" '' "$timer" >&2
}

terminal_wait() (
    # Quiet noninteractive stages use a spinner; build/pull keep native Docker progress.
    wait_label=$1
    shift
    mkdir -p "$ROOT/.runtime"
    wait_log=$(mktemp "$ROOT/.runtime/task-XXXXXX.log")
    wait_child=
    wait_spinner=
    wait_cleanup() {
        [ -z "$wait_spinner" ] || { kill "$wait_spinner" 2>/dev/null || :; wait "$wait_spinner" 2>/dev/null || :; }
        if [ "$rich_terminal" -eq 1 ]; then printf '\r\033[2K\033[?25h' >&2; fi
    }
    trap 'wait_cleanup' EXIT
    trap '[ -z "$wait_child" ] || kill "$wait_child" 2>/dev/null || :; exit 130' INT TERM
    COMPOSE_ANSI=never COMPOSE_PROGRESS=plain BUILDKIT_PROGRESS=plain "$@" >"$wait_log" 2>&1 &
    wait_child=$!
    if [ "$rich_terminal" -eq 1 ]; then
        printf '\033[?25l' >&2
        (
            frame=0
            wait_started=$(terminal_clock_ms)
            while kill -0 "$wait_child" 2>/dev/null; do
                case "$frame" in 0) glyph='|';; 1) glyph='/';; 2) glyph='-';; *) glyph='\';; esac
                wait_now=$(terminal_clock_ms)
                terminal_wait_frame "$glyph" "$wait_label" "$((wait_now - wait_started))"
                frame=$(((frame + 1) % 4))
                sleep 0.12
            done
        ) &
        wait_spinner=$!
    fi
    wait_code=0
    wait "$wait_child" || wait_code=$?
    wait_child=
    wait_cleanup
    wait_spinner=
    if [ "$wait_code" -eq 0 ]; then
        cat "$wait_log"
    else
        awk '/^ERROR:|^Error:|^WARNING:|^Review / {print}' "$wait_log" >&2
        printf 'Diagnostic output: %s\n' "$wait_log" >&2
    fi
    exit "$wait_code"
)
