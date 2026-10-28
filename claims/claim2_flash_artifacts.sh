#!/usr/bin/env bash
# claim 2: device-layer artifacts are recoverable from the flash dumps
# check artifact strings in the q13 dumps, run teaid firmware extraction (s1, s2)
# expect: all checks pass, exit 0; teaid output lands in claim_output/claim2/

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FD="$ROOT/flash_dump"
OUT="$ROOT/claim_output/claim2"
mkdir -p "$OUT"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# check artifact strings in the pre-reset dumps
check_dump() {
    local scale=$1 dump=$2 key=$3
    if grep -qa "$key" "$dump"; then
        pass "$scale flash dump (q13) contains '$key'"
    else
        fail "$scale flash dump (q13) is missing '$key'"
    fi
}

for key in sta.ssid sta.pswd wifi.yolanda.hk key_token; do
    check_dump "S1" "$FD/liorque/q13_liorque.bin" "$key"
done
for key in DEVICEID TOKEN api.eufylife.com; do
    check_dump "S2" "$FD/eufy/q13_eufy.bin" "$key"
done
check_dump "S3" "$FD/withings/q13_withings.bin" "wbs06-ws.withings.net"

echo
echo "== TEAID firmware extraction (S1, S2) =="
TEAID_BIN="${TEAID_BIN:-$ROOT/.venv/bin/teaid}"
command -v teaid >/dev/null && TEAID_BIN="$(command -v teaid)"
if [ -x "$TEAID_BIN" ]; then
    cd "$OUT"
    for eco in liorque eufy; do
        echo "-- running TEAID on q13_${eco}.bin"
        # run on a copy, teaid writes its output next to the input file
        cp "$FD/$eco/q13_${eco}.bin" "$OUT/"
        "$TEAID_BIN" --type scale firmware -p "${eco}_" \
            -f "$OUT/q13_${eco}.bin" || \
            echo "WARN: teaid exited non-zero for $eco (optional tools missing, see install.sh)"
    done
    # check nvs key/value extraction reproduced the wifi artifacts
    if grep -rqa "sta.ssid" "$OUT/liorque_/"; then
        pass "TEAID NVS extraction (S1) reproduces the Wi-Fi credential entries"
    else
        fail "TEAID NVS extraction (S1) is missing the Wi-Fi credential entries"
    fi
    if grep -rqa "sta.apinfo" "$OUT/eufy_/"; then
        pass "TEAID NVS extraction (S2) reproduces the Wi-Fi credential entries"
    else
        fail "TEAID NVS extraction (S2) is missing the Wi-Fi credential entries"
    fi
    echo "TEAID output written below $OUT"
else
    echo "WARN: teaid not found, skipping firmware extraction (run install.sh)"
fi
echo "NOTE: the S3 dump has no partition table; the measurement record is"
echo "      analyzed manually by hex offset as described in README and paper."

echo
if [ "$FAIL" -eq 0 ]; then
    echo "claim 2: ALL CHECKS PASSED"
else
    echo "claim 2: $FAIL CHECK(S) FAILED"
fi
exit "$FAIL"
