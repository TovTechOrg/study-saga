#!/usr/bin/env bash
# Syntax-checks every classic script and ES module in the deployed frontend
# and Functions code. Frontend scripts are unbundled with no build step, so
# without this a syntax error would only surface live in the browser.
set -euo pipefail
cd "$(dirname "$0")"

fail=0

for f in public/static/js/*.js; do
    if ! node --check "$f"; then
        echo "SYNTAX ERROR: $f"
        fail=1
    fi
done

for f in $(find functions -name '*.js'); do
    if ! node --input-type=module --check < "$f"; then
        echo "SYNTAX ERROR: $f"
        fail=1
    fi
done

if [ "$fail" -eq 0 ]; then
    echo "All JS files parsed cleanly."
fi
exit $fail
