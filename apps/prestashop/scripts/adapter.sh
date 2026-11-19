#!/bin/sh
# Forward only a guarded selection to the common native coordinator.
exec sh "$(dirname -- "$0")/../../../scripts/commerce/adapter.sh" "$@"
