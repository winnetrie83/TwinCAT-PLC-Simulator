# ADS Compatibility Update

## Additive compatibility helper (2026-11-12)

- Add **read-only** ADS runtime/symbol diagnostics for TwinCAT 2024-era separate UMRT and newer runtimes.
- Add a guided LIVE launcher that uses the runtime's *actual* AMS Net ID and PLC ADS port.
- Keep `README.md` and the existing simulator configuration unchanged, including any custom disclaimer.
- Preserve full configured symbols (phase 2 and optional phase 3 diverter sensor).
- Provide English setup documentation with troubleshooting tips.
- Add mocked automated tests for diagnostics; no live TwinCAT hardware/UMRT access in the development environment.

Files introduced: `start_live_compat.cmd`, `tools/twincat_compat.py`, `docs/TWINCAT_ADS_COMPATIBILITY.md`, `tests/test_twincat_compat.py`.
