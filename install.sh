#!/usr/bin/env bash
# set up the evaluation environment: venv, teaid, pinned esp-idf tools
# target: minimal x86-64 linux vm (ubuntu 24.04, debian 12 or newer: claims 1
#   and 3 need the sqlcipher 4 cli, ubuntu 22.04 ships sqlcipher 3.4.1)
# prerequisites: sudo apt-get install -y python3 python3-venv python3-pip \
#   build-essential sqlcipher libsqlcipher-dev libleveldb-dev sqlite3 curl

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[1/4] creating virtual environment in $ROOT/.venv"
python3 -m venv "$ROOT/.venv"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
pip install --upgrade pip >/dev/null

echo "[2/4] installing TEAID (editable install, pinned direct dependencies)"
# editable install so teaid resolves ext/ scripts in the source tree
pip install -c "$ROOT/teaid/constraints.txt" -e "$ROOT/teaid"

echo "[3/4] fetching pinned ESP-IDF tools (v5.2.2) into teaid/ext/esp-idf/"
EXT="$ROOT/teaid/ext/esp-idf"
mkdir -p "$EXT"
IDF="https://raw.githubusercontent.com/espressif/esp-idf/v5.2.2"
curl -fsSL -o "$EXT/gen_esp32part.py" "$IDF/components/partition_table/gen_esp32part.py"
curl -fsSL -o "$EXT/nvs_tool.py"      "$IDF/components/nvs_flash/nvs_partition_tool/nvs_tool.py"
curl -fsSL -o "$EXT/nvs_parser.py"    "$IDF/components/nvs_flash/nvs_partition_tool/nvs_parser.py"
curl -fsSL -o "$EXT/nvs_logger.py"    "$IDF/components/nvs_flash/nvs_partition_tool/nvs_logger.py"
curl -fsSL -o "$EXT/nvs_check.py"     "$IDF/components/nvs_flash/nvs_partition_tool/nvs_check.py"
# normalize 'env python' shebangs, minimal systems only ship python3
sed -i.bak '1s|^#!/usr/bin/env python$|#!/usr/bin/env python3|' "$EXT"/*.py
rm -f "$EXT"/*.py.bak
chmod +x "$EXT"/*.py

echo "[4/4] making claim scripts executable"
chmod +x "$ROOT"/claims/*.sh

echo
echo "Installation finished. Verify with:"
echo "  source $ROOT/.venv/bin/activate"
echo "  teaid --help"
echo
echo "Then reproduce the paper claims with ./claims/run_all.sh, or individually:"
echo "  ./claims/claim1_sanitization.sh"
echo "  ./claims/claim2_flash_artifacts.sh"
echo "  ./claims/claim3_feelfit_decrypt.sh"
echo "  ./claims/claim4_coverage.sh"
echo
echo "Optional (not needed for any claim): bulk_extractor and mklittlefs"
echo "enrich the TEAID firmware output when found on PATH."
