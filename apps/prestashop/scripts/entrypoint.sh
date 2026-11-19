#!/bin/sh
# Native URLs and the container listener use the same stable loopback port.
set -eu
case "${HTTP_PORT:-}" in ''|*[!0-9]*) echo 'ERROR: HTTP_PORT must be numeric.' >&2; exit 2;; esac
[ "$HTTP_PORT" -ge 1024 ] && [ "$HTTP_PORT" -le 65535 ] || { echo 'ERROR: HTTP_PORT must be within 1024..65535.' >&2; exit 2; }
sed -i "s/^Listen .*/Listen $HTTP_PORT/" /etc/apache2/ports.conf
sed -i "s/<VirtualHost \*:.*>/<VirtualHost *:$HTTP_PORT>/" /etc/apache2/sites-available/000-default.conf
exec /tmp/docker_run.sh
