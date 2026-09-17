# Rejected Release-Corpus Fixtures

These manifests were removed from the active 420-fixture release corpus after
the approved human-review cleanup on 2026-09-08. Their raw source files remain
unchanged under `raw/` for auditability. Rejected IDs remain reserved and the
collectors will not re-add them automatically.

| Group | Count | Decision |
| --- | ---: | --- |
| `ATOM-FR-MARITIME-LABOR-PAGE-*` | 20 | Search-result pages are research leads, not individual event fixtures. |
| `ATOM-FR-SANCTIONS-SECURITY-PAGE-*` | 20 | Search-result pages are research leads, not individual event fixtures. |
| `ATOM-SYN-AMB-EN-045`, `ATOM-SYN-AMB-EN-048` | 2 | Redundant generated ambiguity fixtures; oracle fixtures `ATOM-SYN-AMBIG-01` and `ATOM-SYN-AMBIG-02` remain active. |
| 12 `ATOM-CWA-TDB-*` records | 12 | Removed from the monitor queue to retain an 18-record, split-balanced CWA review subset. |
| 9 `ATOM-NOAA-BERYL-*` records | 9 | Redundant Taiwan-route weather negative controls (`06`, `08`, `10`, `12`, `14`, `16`, `18`, `22`, `24`), archived to restore the fixed category balance. |

This directory is not scanned as active benchmark input by the validator or
bakeoff harness.
