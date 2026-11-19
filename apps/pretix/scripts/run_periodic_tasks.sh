#!/bin/sh
# Run periodic pretix tasks until Docker requests shutdown.
# Input: pretix configuration from the environment. Output: task logs and exit status.
# A failed task terminates this process so Compose can apply its restart policy.
set -eu
interval=${PERIODIC_INTERVAL_SECONDS:-300}
case "$interval" in
  ''|*[!0-9]*) printf '%s\n' 'ERROR: PERIODIC_INTERVAL_SECONDS must be an integer from 60 to 3600.' >&2; exit 2 ;;
esac
if [ "$interval" -lt 60 ] || [ "$interval" -gt 3600 ]; then
  printf '%s\n' 'ERROR: PERIODIC_INTERVAL_SECONDS must be an integer from 60 to 3600.' >&2
  exit 2
fi
trap 'exit 0' TERM INT
while :; do
  pretix cron
  sleep "$interval" &
  wait "$!"
done
