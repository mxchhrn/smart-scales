# UDIM Interaction Graphs

This folder contains the User-Device Interaction Model (UDIM) graph of each smart scale ecosystem examined in the paper. UDIM is the device-centric graph model of Eichhorn, Hammer, Pugliese, and Freiling, "UDIM: Formal user-device interaction model for approximating artifact coverage in IoT forensics" (SDIoTSec 2026, co-located with NDSS). It enumerates the possible interactions between a device and its users, its environment, and other devices or services, ordered by interaction distance. The graphs complement the coupled state machine analysis of the paper by characterizing, prior to the investigation, where artifacts of an interaction can arise.

## Files

| Ecosystem | Graph | Rendering |
|---|---|---|
| S1, LIORQUE CS20A | `s1_liorque_cs20a.json` | `s1_liorque_cs20a.{dot,svg,pdf}` |
| S2, Eufy Smart Scale P3 | `s2_eufy_smart_scale_p3.json` | `s2_eufy_smart_scale_p3.{dot,svg,pdf}` |
| S3, Withings Body | `s3_withings_body.json` | `s3_withings_body.{dot,svg,pdf}` |

`render_dot.py` checks the JSON files (unique ids, central device present, edge endpoints exist and belong to the edge's subgraph) and writes the DOT files. Rendering needs Graphviz:

```bash
python3 render_dot.py
dot -Tsvg -o s1_liorque_cs20a.svg s1_liorque_cs20a.dot
```

## Notation

Each JSON file has three parts.

- `device`: vendor, model, SoC, and form factor of the central device `d`. `local_api` is empty for all three scales, as none exposes a local interface without the vendor app.
- `nodes`: entities with a `type` (`dev` for devices and hosted services, `usr` for users, `env` for the environment the device senses) and their membership in the three UDIM subgraphs: `alpha` (proximity: the spatial surroundings of the device), `beta` (internal network: the same Bluetooth or Wi-Fi network as the device), and `gamma` (external network). The central device belongs to `alpha` and `beta`; the router belongs to `beta` and `gamma`.
- `edges`: potential interactions, each assigned to one subgraph. `bidirectional: true` denotes information flow in both directions; otherwise `from` and `to` give the direction. The edge from `d` to `d` is the device-internal interaction of the UDIM paper (interaction pair 4), always present.

The four UDIM interaction pairs appear as follows. User-device (1): `u_alpha` steps onto the platform (direct), `u_beta` acts through the companion app on a phone paired via BLE (single-step transitive), and `u_gamma` acts through the app and the vendor cloud from outside the home network (multi-step transitive). Device-device (2): the scale talks to the phone over BLE and to the vendor endpoints over Wi-Fi through the router; the phone talks to the cloud. Device-environment (3): the load cell, and on S1 and S2 the bioimpedance electrodes, sense whatever is placed on the platform, which includes pets and objects (the paper's reference weight and the pet sub-account on S2 show that such measurements are recorded), and the display shows readings to anyone present. Device-internal (4): the firmware's own persistent storage, which is the device layer of the paper.

The rendering nests the proximity subgraph inside the internal network subgraph, as in Figure 1 of the UDIM paper, and colors edges by subgraph (blue: proximity, green: internal network, orange: external network). The central device is drawn with a double border, environments with a dashed border.

## Grounding

Nodes and edges are grounded in the evidence of the study rather than in datasheets: the cloud endpoints are the hostnames found in the device flash dumps (`flash_dump/`), in the decrypted app traffic, and in the companion app packages, and the companion app package names are those of the analyzed APKs (see the version table in the top-level `README.md`). The `metadata.flags` list of each file records such grounding notes and the modeling limits. Third-party fitness integrations offered by the companion apps lie outside the playbook of the paper and are not modeled.
