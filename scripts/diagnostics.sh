#!/bin/sh
# Read bounded local diagnostics without Docker, hiding configured secret values.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
app=${1:-}
case "$app" in oscar|pretix|shuup|wowy|nopcommerce|prestashop|woocommerce) :;; *) echo 'ERROR: Select a registered app.' >&2; exit 2;; esac
base="$ROOT/apps/$app"
[ ! -L "$base/.runtime" ] && [ ! -L "$base/.env" ] || { echo 'ERROR: Diagnostic paths must not be filesystem links.' >&2; exit 2; }
env_file="$base/.env"
[ -f "$env_file" ] || env_file=/dev/null
found=0
for name in prestashop-install.log seed-diagnostic.log django-migrate.log django-seed_demo.log django-collectstatic.log django-reindex_product_catalog.log maintenance-errors.log server-errors.log data/request-errors.log data/request-errors.log; do
    path="$base/.runtime/$name"
    [ ! -L "$path" ] || { echo 'ERROR: Diagnostic files must not be filesystem links.' >&2; exit 2; }
    [ -f "$path" ] || continue
    found=1
    printf '\nDiagnostic: apps/%s/.runtime/%s (last 120 lines)\n' "$app" "$name"
    awk '
        FILENAME == ARGV[1] {
            key=$0; sub(/=.*/, "", key)
            if (key ~ /(PASSWORD|SECRET|TOKEN|KEY)/ && index($0,"=")) {
                value=substr($0,index($0,"=")+1); sub(/\r$/, "", value)
                quote=substr(value,1,1)
                if ((quote=="\"" || quote==sprintf("%c",39)) && substr(value,length(value),1)==quote) value=substr(value,2,length(value)-2)
                if (length(value)>=4) secrets[++count]=value
            }
            next
        }
        {
            line=$0
            for (i=1;i<=count;i++) {
                result=""
                while ((position=index(line,secrets[i]))>0) {
                    result=result substr(line,1,position-1) "[hidden]"
                    line=substr(line,position+length(secrets[i]))
                }
                line=result line
            }
            lines[NR%120]=line; total++
        }
        END { start=NR-total+1; if (total>120) start=NR-119; for (i=start;i<=NR;i++) print lines[i%120] }
    ' "$env_file" "$path"
done
[ "$found" -eq 1 ] || printf 'No backend diagnostic is available under apps/%s/.runtime. Keep the task log; rerun the failing operation after correcting configuration.\n' "$app"
printf '\nKnown configured secrets were hidden. Review diagnostics before sharing.\n'
