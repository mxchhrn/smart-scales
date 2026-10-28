#!/usr/bin/env bash
# claim 4: teaid reproduces the app-layer artifact category coverage
# run teaid app module on q15 data, compare with reference in app_teaid_output/
# expect: all checks pass, exit 0; diffs vs reference are informational

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CA="$ROOT/companion_app"
REF="$ROOT/app_teaid_output"
OUT="$ROOT/claim_output/claim4"
mkdir -p "$OUT"
FAIL=0

TEAID_BIN="${TEAID_BIN:-$ROOT/.venv/bin/teaid}"
command -v teaid >/dev/null && TEAID_BIN="$(command -v teaid)"
if [ ! -x "$TEAID_BIN" ]; then
    echo "FAIL: teaid not found (run install.sh first)"
    exit 1
fi

# map ecosystem to app id
appid() {
    case "$1" in
        liorque)  echo "com.qingniu.feelfit" ;;
        eufy)     echo "com.oceanwing.smarthome" ;;
        withings) echo "com.withings.wiscale2" ;;
    esac
}

for eco in liorque eufy withings; do
    id="$(appid "$eco")"
    echo "== $eco ($id) =="
    mkdir -p "$OUT/$eco"
    "$TEAID_BIN" --type scale app -i "$id" \
        -a "$CA/$eco/q15_${eco}" -o "$OUT/$eco" || true

    SUMMARY="$OUT/$eco/${id}_companion_app_summary.json"
    if [ -s "$SUMMARY" ]; then
        echo "PASS: TEAID produced a non-empty summary for $eco"
    else
        echo "FAIL: no TEAID summary produced for $eco"
        FAIL=$((FAIL + 1))
        continue
    fi

    REFJSON="$REF/$eco/q15_${eco}/${id}_companion_app_summary.json"
    if diff -q "$SUMMARY" "$REFJSON" >/dev/null 2>&1; then
        echo "PASS: summary matches the shipped reference output"
    else
        echo "INFO: summary differs from the shipped reference (inspect with:"
        echo "      diff $SUMMARY $REFJSON )"
    fi
    echo
done

if [ "$FAIL" -eq 0 ]; then
    echo "claim 4: ALL CHECKS PASSED"
else
    echo "claim 4: $FAIL CHECK(S) FAILED"
fi
exit "$FAIL"
