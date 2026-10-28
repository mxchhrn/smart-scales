#!/usr/bin/env bash
# claim 3: feelfit oversea.db decrypts with the hard-coded sqlcipher key
# key is identical across installations, recoverable via strings on the apk
# (apk not included, see README)
# expect: all checks pass, exit 0; prints schema and measurement row count

set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/claim_output/claim3"
mkdir -p "$OUT"
FAIL=0

if ! command -v sqlcipher >/dev/null; then
    echo "FAIL: sqlcipher not found (run install.sh prerequisites)"
    exit 1
fi
# the feelfit database uses the sqlcipher 4 format, sqlcipher 3.x cannot open it
CIPHER_VERSION=$(sqlcipher :memory: "PRAGMA cipher_version;" 2>/dev/null | head -1)
if [ "${CIPHER_VERSION%%.*}" -lt 4 ] 2>/dev/null; then
    echo "FAIL: sqlcipher $CIPHER_VERSION found, SQLCipher 4 required (Ubuntu 22.04 ships 3.4.1; use Ubuntu 24.04, Debian 12 or newer)"
    exit 1
fi

# copy db to keep the artifact data read-only
DB="$OUT/oversea_q15.db"
cp "$ROOT/companion_app/liorque/q15_liorque/databases/oversea.db" "$DB"

echo "== decrypting oversea.db (state q15) with the hard-coded key =="
TABLES=$(sqlcipher "$DB" "PRAGMA key='db_encrypt_key';" ".tables" 2>/dev/null)
if [ -n "$TABLES" ]; then
    echo "PASS: database opens with the documented key, schema:"
    echo "$TABLES"
else
    echo "FAIL: database could not be decrypted with the documented key"
    FAIL=$((FAIL + 1))
fi

echo
N=$(sqlcipher "$DB" \
    "PRAGMA key='db_encrypt_key'; SELECT count(*) FROM MEASURE_DATA;" \
    2>/dev/null | tail -1)
if [ "${N:-0}" -gt 0 ] 2>/dev/null; then
    echo "PASS: measurement history readable, $N rows in MEASURE_DATA"
else
    echo "FAIL: no readable rows in MEASURE_DATA"
    FAIL=$((FAIL + 1))
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "claim 3: ALL CHECKS PASSED"
else
    echo "claim 3: $FAIL CHECK(S) FAILED"
fi
exit "$FAIL"
