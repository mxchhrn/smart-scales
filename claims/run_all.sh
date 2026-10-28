#!/usr/bin/env bash
# run all four claim scripts in sequence and summarize
# expect: one PASS line per claim, exit 0 when every claim passed

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAIMS=(claim1_sanitization claim2_flash_artifacts claim3_feelfit_decrypt claim4_coverage)
FAILED=0
SUMMARY=()

for c in "${CLAIMS[@]}"; do
    echo "################ $c ################"
    if bash "$ROOT/claims/$c.sh"; then
        SUMMARY+=("PASS: $c")
    else
        SUMMARY+=("FAIL: $c (exit $?)")
        FAILED=$((FAILED + 1))
    fi
    echo
done

echo "################ summary ################"
printf '%s\n' "${SUMMARY[@]}"
if [ "$FAILED" -eq 0 ]; then
    echo "all claims: PASSED"
else
    echo "all claims: $FAILED FAILED"
fi
exit "$FAILED"
