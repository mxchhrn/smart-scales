# TEAID
Tool for Evidence Acquisition from IoT Devices (TEAID)

## External Dependencies
- Network
    - tshark (e.g. `sudo apt install tshark`)
- Firmware
    - [bulk_extractor](https://github.com/simsong/bulk_extractor)
        - Dependencies:
            - openssl
            - libssl-dev
            - flex
            - libewf-dev
            - libre2-dev
    - [mklittlefs](https://github.com/earlephilhower/mklittlefs/releases/download/4.0.2/x86_64-linux-gnu-mklittlefs-db0513a.tar.gz)
    - [bk7231tools](https://github.com/tuya-cloudcutter/bk7231tools)
    - [gen_esp32part.py](https://github.com/espressif/esp-idf/blob/master/components/partition_table/gen_esp32part.py)
    - [esp-idf](https://github.com/espressif/esp-idf)

If some external components are not installed system-wide, you can simply place them in `ext/<subdir>/` (e.g. `ext/esp-idf/` for the ESP-IDF tools), and TEAID will find them automatically. The artifact's `install.sh` fetches the ESP-IDF tools into this location.

## Installation
Prepare a virtual environment
```
python3 -m venv <name of your env>
```
Activate your environment
```
source <name of your env>/bin/activate
```
Install your local package (editable, so TEAID resolves helper scripts in `ext/`)
```
python -m pip install -e .
```

## Run TEAID
```
teaid --help
```