# Data Provenance

This document describes how the data in this repository was collected and processed. Full methodological detail is given in the paper (Section on method and acquisition).

## Origin

All data was produced by applying a fixed playbook of 15 action sequences to three smart scale ecosystems. Each ecosystem consists of the physical device, its Android companion app, and the vendor cloud. The playbook states q0 to q15 and their naming convention are listed in `README.md`.

| Scale | Device | SoC / storage | Companion app |
|---|---|---|---|
| S1 | LIORQUE CS20A | Espressif ESP32-S0WD | Feelfit (`com.qingniu.feelfit`) |
| S2 | Eufy Smart Scale P3 | Espressif ESP8266EX | EufyLife (`com.oceanwing.smarthome`) |
| S3 | Withings Body | NXP Kinetis K22, external SPI NOR flash | Health Mate (`com.withings.wiscale2`) |

The devices were purchased new and were owned and operated by the research team for the sole purpose of this study.

## Acquisition per layer

**Device flash (`flash_dump/`).** Binary dumps were acquired after each playbook state with the device powered off. For the ESP-based scales (S1, S2), dumps were read with `esptool` over UART in flash mode via the ROM bootloader. For S3, the SPI NOR flash was read with `flashrom` over a soldered SPI connection. Dumps are complete for S1 and S3. For S2, chip-detection limits restricted acquisition to 2 MB of the 8 MB flash, consistently across all states. State differences were computed over SHA-256 hashes of the dumps.

**Companion app (`companion_app/`).** After each state, a logical image of `/data/data/<AppID>` was taken with `adb` from a Magisk-rooted Android phone. This repository contains the primary forensic databases per state and, for q0 and q15, the additional files listed in `README.md`. Runtime caches and telemetry files were excluded. The app versions in use per state are listed in `README.md`.

**Network traffic.** TLS traffic between app and vendor cloud was captured with PCAPdroid and decrypted with mitmproxy. Certificate pinning was bypassed with an LSPosed SSL-unpinning module. The captures were used for attributing cloud coupling and are not part of this repository.

**Vendor cloud.** Direct REST API access was established after the full playbook. Cloud data is not included in this repository. All artifact categories reported in the paper are recoverable from the device and app layers alone.

**TEAID outputs (`app_teaid_output/`).** The JSON summaries were produced by running the included TEAID framework on the companion app data of each state. They serve as reference outputs for the claim scripts in `claims/`.

## Processing and anonymization

The published files are anonymized derivatives of the original evidence. Email addresses, GPS coordinates, authentication and session tokens, and the primary account name were replaced with the placeholder `[redacted]` in all data files. Measurement records and their structural encoding were left intact, as they constitute the forensic evidence reported in the paper.

In the binary flash dumps, redaction is applied in place and preserves the original field length, so that offsets, the NVS entry structure, and the state differences between dumps are unchanged. In the S3 dumps, the 3-byte short username was replaced with `ABC`. In the S2 dumps, the values of the three NVS string entries that hold secrets provisioned by the vendor cloud at first login were replaced with `[redacted]` padded with underscores to the original length: `TOKEN` (80 characters), `ACESSTOKEN` (26 characters, the firmware's spelling of the entry the paper calls `ACCESSTOKEN`), and `WIFICODE` (26 characters, a binding code provisioned together with the tokens). Stale copies of these entries were treated alike, and the data and header CRC32 fields of each entry were recomputed, so the partition remains parseable by `nvs_tool`. The S1 dumps contain no cloud token; the entry `key_token` is a 16-digit value of undetermined purpose (paper, Section on device artifacts) that also appears unredacted in the companion app data and was left in place.

Deliberately preserved, because the paper reports their presence and claim 2 verifies them, are the SSID and password of the dedicated test Wi-Fi network used for the study (the password has since been retired), the MAC addresses, the device identifiers (`SN`, `DEVICEID`, `WIFIUID`), the TLS certificates, and the S1 BLE bonding data. The S1 `user_info_key` blobs are binary and contain no names.

For the Feelfit ecosystem (S1), the published q0 app state was recaptured after the study from the archived version 4.14.0 APK, sideloaded onto a rooted Google Pixel 8a (Android 16) and launched once without account creation and without network access. The tree was acquired with the same adb-based logical imaging method as all other states, and its TEAID reference output was regenerated from it. Device-scoped identifiers and file timestamps in this state therefore reflect the recapture device and date.

Two consequences of this processing should be noted. First, hashes of the published dumps differ from those of the original acquisitions, so the hash values in the paper cannot be recomputed from this repository. Second, the state differences that carry the paper's findings are preserved, since the redaction replaces values in place and is applied consistently across states. The original unredacted evidence is retained by the authors.

## Changes after artifact evaluation

The version evaluated by the ACSAC artifact evaluation committee was anonymized. For the archival release, the repository was de-anonymized: author names were added to `LICENSE` and `README.md`, the citation and the repository links in `metadata.toml` were replaced with their non-anonymous counterparts, and the TEASR reference in `README.md` now points to the public repository.

In addition, `app_teaid_output/eufy/q14_eufy/` was removed. It contained a byte-identical copy of the q15 reference output in the q14 slot, although the Eufy q14 app state was never captured (see `README.md`). No claim script referenced it.

In response to the artifact evaluation reviews (2026-10-28), the following changes were made. The S2 NVS entries `TOKEN`, `ACESSTOKEN`, and `WIFICODE` were redacted in place as described above; the evaluated version still contained their values (13 dumps from q2 to q15, 190 bytes changed per dump, nothing else touched). `claims/run_all.sh` runs the four claim scripts in sequence. `install.sh` installs TEAID with pinned direct dependencies (`teaid/constraints.txt`). The SQLCipher binding was changed from the abandoned `pysqlcipher3` (last release 2023, fails to compile against Python 3.13 and later) to the maintained drop-in `sqlcipher3`; TEAID falls back to `pysqlcipher3` where only that is installed, and its database access is otherwise unchanged. The author names were added to `teaid/pyproject.toml`. The `sqlite3` command line tool used by claim 1 was added to the documented prerequisites, and claims 1 and 3 now report explicitly when the installed `sqlcipher` tool is older than SQLCipher 4 (Ubuntu 22.04 ships 3.4.1, which cannot open the Feelfit database); their checks are otherwise unchanged. The UDIM interaction graphs referenced in the paper were added under `udim/`.

Apart from the in-place redaction of the three S2 token entries, the claim scripts and all data files read by the claims are unchanged from the evaluated version. The claim scripts check NVS key names and entry structure, not token values, and pass unchanged.
