#!/usr/bin/env bash
# claim 1: factory reset (sigma_14) triggers no ecosystem-wide sanitization
# check nvs survival (s1, s2), flash change (s3), app measurement survival (s1-s3)
# expect: all checks pass, exit 0

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FD="$ROOT/flash_dump"
CA="$ROOT/companion_app"
OUT="$ROOT/claim_output/claim1"
mkdir -p "$OUT"
FAIL=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# get sha256 portably (sha256sum or shasum)
sha256() {
    if command -v sha256sum >/dev/null; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

echo "== device layer =="

# check s1 nvs entries survive the reset
for key in sta.ssid sta.pswd sta.apinfo key_token; do
    if grep -qa "$key" "$FD/liorque/q14_liorque.bin"; then
        pass "S1 post-reset flash (q14) still contains NVS entry '$key'"
    else
        fail "S1 post-reset flash (q14) is missing NVS entry '$key'"
    fi
done

# check s2 wifi credentials survive in sta.apinfo
if grep -qa "sta.apinfo" "$FD/eufy/q14_eufy.bin"; then
    pass "S2 post-reset flash (q14) still contains 'sta.apinfo'"
else
    fail "S2 post-reset flash (q14) is missing 'sta.apinfo'"
fi

# check s3 flash changed across the reset
H13=$(sha256 "$FD/withings/q13_withings.bin")
H14=$(sha256 "$FD/withings/q14_withings.bin")
if [ "$H13" != "$H14" ]; then
    pass "S3 flash differs between q13 and q14 (device-side restoration)"
else
    fail "S3 flash is identical between q13 and q14"
fi
echo "NOTE: the byte-level restoration of the S3 measurement record region"
echo "      is verified manually via the hexdump figure in the paper."

echo
echo "== app layer (measurement history survives the reset) =="

# check s1 measurement rows survive (sqlcipher db, needs sqlcipher 4: the app uses the v4 format)
CIPHER_VERSION=$(sqlcipher :memory: "PRAGMA cipher_version;" 2>/dev/null | head -1)
if ! command -v sqlcipher >/dev/null; then
    fail "sqlcipher not found (run install.sh prerequisites)"
elif [ "${CIPHER_VERSION%%.*}" -lt 4 ] 2>/dev/null; then
    fail "sqlcipher $CIPHER_VERSION found, SQLCipher 4 required (Ubuntu 22.04 ships 3.4.1; use Ubuntu 24.04, Debian 12 or newer)"
else
    cp "$CA/liorque/q14_liorque/databases/oversea.db" "$OUT/oversea_q14.db"
    N=$(sqlcipher "$OUT/oversea_q14.db" \
        "PRAGMA key='db_encrypt_key'; SELECT count(*) FROM MEASURE_DATA;" \
        2>/dev/null | tail -1)
    if [ "${N:-0}" -gt 0 ] 2>/dev/null; then
        pass "S1 app database (q14) holds $N rows in MEASURE_DATA"
    else
        fail "S1 app database (q14) holds no MEASURE_DATA rows"
    fi
fi

# check s2 measurement rows (q14 not captured, see README)
for q in q13 q15; do
    N=$(sqlite3 -readonly "$CA/eufy/${q}_eufy/databases/EufyLifeDb.db" \
        "SELECT count(*) FROM bodyfathistorym;" 2>/dev/null)
    if [ "${N:-0}" -gt 0 ] 2>/dev/null; then
        pass "S2 app database ($q) holds $N rows in bodyfathistorym"
    else
        fail "S2 app database ($q) holds no bodyfathistorym rows"
    fi
done

# check s3 measurement rows survive (wal db, open immutable)
N=$(sqlite3 "file:$CA/withings/q14_withings/databases/Withings-WiScale?immutable=1" \
    "SELECT count(*) FROM measure;" 2>/dev/null)
if [ "${N:-0}" -gt 0 ] 2>/dev/null; then
    pass "S3 app database (q14) holds $N rows in measure"
else
    fail "S3 app database (q14) holds no measure rows"
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "claim 1: ALL CHECKS PASSED"
else
    echo "claim 1: $FAIL CHECK(S) FAILED"
fi
exit "$FAIL"
