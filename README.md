# Artifact Repository — "Scaling Up: IoT Ecosystem Forensics via Coupled State Machines, Applied to Smart Scales"

This repository accompanies the paper by Maximilian Eichhorn, Christian Minuth, and Felix Freiling (Friedrich-Alexander-Universität Erlangen-Nürnberg), accepted at ACSAC 2026.
It provides the TEAID framework, the EufyLife Realm export script, TEAID JSON outputs, and anonymized companion app databases and flash dumps for all three target ecosystems.

The following fields have been replaced with the placeholder `[redacted]` in all included data files: email addresses, GPS coordinates, authentication and session tokens, and the primary account name (firstname and shortname).
In the binary flash dumps the replacement is applied in place with the original field length, so the NVS structure stays parseable: the Eufy NVS token entries `TOKEN`, `ACESSTOKEN`, and `WIFICODE` hold padded placeholders, and the 3-byte short username field of the Withings Body dumps has been replaced with `ABC` (`41 42 43`), matching the hexdump figure in the paper.
Wi-Fi credentials of the dedicated test network, MAC addresses, and device identifiers are preserved, as they are the device-layer evidence verified by claim 2 (see `PROVENANCE.md`).
Measurement records and their structural encoding are preserved intact, as they constitute the primary forensic evidence reported in the paper.
No raw health data linked to identifiable individuals is included.

---

## Repository Structure

```
.
├── teaid/                  TEAID framework (Python)
├── scripts/                EufyLife Realm DB export script and manual
├── claims/                 Claim scripts for artifact evaluation (run_all.sh runs all four)
├── udim/                   UDIM interaction graphs of the three ecosystems (JSON, DOT, SVG, PDF)
├── install.sh              Evaluation environment setup
├── metadata.toml           Artifact metadata
├── PROVENANCE.md           Data collection methodology
├── ETHICS.md               Ethics statement
├── LICENSE                 MIT (code) and CC BY 4.0 (data)
├── flash_dump/             Anonymized binary flash dumps per playbook step
│   ├── liorque/
│   ├── eufy/
│   └── withings/
├── companion_app/          Companion app data per playbook step (primary databases only)
│   ├── liorque/
│   ├── eufy/
│   └── withings/
└── app_teaid_output/       TEAID JSON summary output per playbook step
    ├── liorque/
    ├── eufy/
    └── withings/
```

---

## Artifact Evaluation

The artifact reproduces the paper's main claims offline on a minimal x86-64 Linux VM (2 GB RAM, ~2 GB free disk). No physical devices, cloud access, GPU, or GUI are required. The distribution must ship SQLCipher 4 (Ubuntu 24.04, Debian 12, or newer): the Feelfit database uses the SQLCipher 4 format, which the SQLCipher 3.4.1 command line tool of Ubuntu 22.04 cannot open (claims 1 and 3 report this explicitly). The mapping between claims and scripts is given in `metadata.toml`.

**Setup** (creates `.venv/`, installs TEAID with pinned direct dependencies, fetches pinned ESP-IDF helper tools):

```bash
sudo apt-get install -y python3 python3-venv python3-pip build-essential sqlcipher libsqlcipher-dev libleveldb-dev sqlite3 curl
./install.sh
```

**Reproduce the claims** (each prints PASS/FAIL per check and exits 0 on success):

```bash
./claims/run_all.sh                # all four claims in sequence, with a summary
./claims/claim1_sanitization.sh    # factory reset is no ecosystem-wide sanitization
./claims/claim2_flash_artifacts.sh # device-layer artifacts recoverable from flash dumps
./claims/claim3_feelfit_decrypt.sh # Feelfit DB decrypts with the hard-coded key
./claims/claim4_coverage.sh        # TEAID reproduces the app-layer extraction
```

Outputs are written to `claim_output/`. Claims 1 to 3 run in seconds and need only the system prerequisites; claim 4 and the TEAID part of claim 2 require `install.sh` to have completed. Claim 2 verifies the presence of the NVS entries by key name and structure (for example `sta.pswd`, `TOKEN`); the token values themselves are redacted placeholders, see above. See `PROVENANCE.md` for how the data was collected and anonymized, and `ETHICS.md` for the ethics statement and expectations for evaluators.

**APK files are not included.** The companion apps used in this study are available from the Google Play Store. The versions used were:

| Device | App | Initial version (σ₁–σ₁₀) | Updated version (σ₁₁–σ₁₅) |
|---|---|---|---|
| LIORQUE CS20A | Feelfit (`com.qingniu.feelfit`) | 4.14.0 | 4.16.2 |
| Eufy Smart Scale P3 | EufyLife (`com.oceanwing.smarthome`) | 3.3.5 | 3.3.9 |
| Withings Body | Health Mate (`com.withings.wiscale2`) | 7.3.2 | 8.0.0 |

Note: The Eufy companion app data for q₂–q₄ (`q02_q04_eufy`) was captured with app version 3.2.5, before the main investigation began with 3.3.5.

---

## Playbook

The 15 action sequences applied to each ecosystem correspond to the following folder and file naming convention used throughout this repository:

| State | Label | Action sequence |
|---|---|---|
| q₀  | Initial image         | Factory image; no prior actions performed |
| q₁  | Offline Usage         | First boot without network; weight measurements |
| q₂  | First Login + BT      | Companion app pairing via Bluetooth; account registration; weight measurements |
| q₃  | Connect Wi-Fi         | Wi-Fi credential entry; device-specific setup; weight measurements |
| q₄  | Add Users             | Secondary user profile creation; per-user weight measurements |
| q₅  | Daily Measurements 1  | Weight measurements with all registered users |
| q₆  | Daily Measurements 2  | Weight measurements with all registered users |
| q₇  | Daily Measurements 3  | Weight measurements with all registered users |
| q₈  | Daily Measurements 4  | Weight measurements with all registered users |
| q₉  | Daily Measurements 5  | Weight measurements with all registered users |
| q₁₀ | Check for Updates     | Firmware update check triggered via companion app |
| q₁₁ | App Update + DM 6     | Companion app updated; weight measurements |
| q₁₂ | Daily Measurements 7  | Weight measurements with all registered users |
| q₁₃ | Daily Measurements 8  | Weight measurements with all registered users |
| q₁₄ | Factory Reset         | Device reset to factory state via companion app |
| q₁₅ | Repeat Initial Actions | Repeat offline actions of σ₁ |

---

## Companion App Data

The intermediate states contain only the files that hold forensic artifacts as reported in the paper; the q₀ and q₁₅ states include the full application tree.

| App | Primary forensic database | Additional files (q₀ and q₁₅ only) |
|---|---|---|
| Feelfit (S₁) | `oversea.db` | `king_new_foreign.db`, `com.qingniu.feelfit_preferences.xml` |
| EufyLife (S₂) | `EufyLifeDb.db` | `android_room_dev.db`, `FlutterSharedPreferences.xml`, `share_data.xml` |
| Health Mate (S₃) | `Withings-WiScale` | `room-healthmate.db`, `rl_persistence.db`, `account.xml`, `user.xml`, `withings-library.xml`, `com.withings.wiscale2_preferences.xml` |

**Per-state coverage:**

- **q₀** — full directory tree of the unmodified app installation; no personal data present. For S1 (Feelfit), this state was recaptured post-study from the archived version 4.14.0 APK (see `PROVENANCE.md`).
- **q₁** — not included for any ecosystem (offline usage precedes companion app involvement).
- **q₂–q₄ through q₁₄** — `databases/` subfolder containing the primary forensic database only (see table above). Eufy q₁₄ was not captured (factory reset does not affect companion app data).
- **q₁₅** — full directory tree, including all files listed above.

**Note on LIORQUE:** `oversea.db` is SQLCipher-encrypted. Open it with the key `db_encrypt_key` (recoverable by string search of `classes3.dex` in the APK): `PRAGMA key = 'db_encrypt_key';`

See `PROVENANCE.md` for the acquisition method and the anonymization applied to all included files.

---

## TEAID Framework

TEAID (Tool for Evidence Acquisition from IoT Devices) is a four-component Python framework that extends the TEASR framework (https://github.com/mxchhrn/teasr) to cover smart scale ecosystems alongside smart relay ecosystems.

See `teaid/README.md` for installation and usage instructions; `install.sh` performs the installation automatically.

**Components:**
- `firmware` — ESP-specific NVS extraction (`gen_esp32part.py`, `nvs_tool`) with generic string/JSON fallback
- `app` — Companion app data extraction by AppID; outputs `companion_app_summary.json`
- `network` — PCAP analysis with optional TLS decryption (mitmproxy flow or SSLKEYLOGFILE)
- `remote` — Vendor cloud API queries (implemented for smart relays; not yet implemented for smart scales)

---

## EufyLife Realm Database Export

The EufyLife companion app uses an encrypted Realm database (`files/default.realm`).
The encryption key (`DATABASE_ENCRYPTION_KEY`) is present in `DatabaseSDK.java` of the decompiled APK.

The export script in `scripts/` extracts the database contents using the Node.js Realm SDK in debug mode, bypassing the need for a full Realm-to-SQLite converter. This script is optional, requires Chrome DevTools, and is not needed to reproduce any result in the paper; the Eufy evidence used by the paper is the plain-SQLite `EufyLifeDb.db` included in this repository.

**Usage:**

```bash
npm install realm
node --inspect-brk scripts/eufy_export_encrypted_realm_DB.js <path_to_default.realm>
# Then open chrome://inspect and connect to the Node.js debugger
```

See `scripts/How_to_run_js.md` for step-by-step instructions.

---

## UDIM Interaction Graphs

`udim/` contains the User-Device Interaction Model (UDIM) graph of each ecosystem, as referenced in the paper's related work section: `s1_liorque_cs20a`, `s2_eufy_smart_scale_p3`, and `s3_withings_body`, each as a machine-readable JSON file (nodes typed device, user, or environment, assigned to the subgraphs proximity, internal network, and external network, plus directed or bidirectional edges) and as a Graphviz rendering (DOT, SVG, PDF). `udim/README.md` explains the notation and the modeling decisions; `udim/render_dot.py` checks the JSON files and regenerates the DOT files.

---

## How to Cite

The evaluated artifact is archived on Zenodo: https://doi.org/10.5281/zenodo.23594059

If you use this artifact in academic work, please cite the paper:

```bibtex
@inproceedings{eichhorn2026scales,
  author    = {Eichhorn, Maximilian and Minuth, Christian and Freiling, Felix},
  title     = {Scaling Up: {IoT} Ecosystem Forensics via Coupled State Machines, Applied to Smart Scales},
  booktitle = {Proceedings of the Annual Computer Security Applications Conference (ACSAC)},
  publisher = {IEEE},
  year      = {2026}
}
```
