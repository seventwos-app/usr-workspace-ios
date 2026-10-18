#!/bin/bash
set -eu

: "${CODEQL_REAL_SWIFTC:?Set CODEQL_REAL_SWIFTC to the Xcode Swift compiler}"
for argument in "$@"; do
    if [ "$argument" = "-frontend" ]; then
        exec "$CODEQL_REAL_SWIFTC" "$@"
    fi
done

exec "$CODEQL_REAL_SWIFTC" "$@" -j1
