# TwinCAT PLC Simulator — ADS compatibility & first LIVE test

This is an **additive update**. It deliberately does **not** include or overwrite `README.md`, `app.py`, `config/settings.json`, or any TwinCAT program. Apply it to the root of your existing simulator (phase 2 or phase 3).

## Supported design

The simulator talks to the **PLC runtime** using pyads and ADS, not to the TwinCAT engineering IDE. It does not select behavior by product year.

- **TwinCAT 2024 / separately started UMRT:** start your UMRT first. Note the **actual** `AmsNetId` printed by the UMRT; it may not be `127.0.0.1.1.1`.
- **TwinCAT 2026 and later:** use the runtime's actual AMS Net ID and PLC ADS port in exactly the same manner. A 2026 installation can also require a separate UMRT, depending on its configuration.
- PLC Runtime 1 normally uses **ADS port 851**; Runtime 2 normally uses 852. This is **not** TCP port 48898.
- This compatibility layer is designed for these versions but a real integration check must be carried out on each supported TwinCAT release. Future releases cannot be guaranteed without testing.

## First test — Windows

1. Run `install.cmd` once if Python dependencies have not been installed.
2. Start the Usermode Runtime using your existing **TwinCAT SysTray** or its installed **`start.bat`** (do not confuse this with our `start_live_compat.cmd`). On some versions that file is located under `C:\ProgramData\Beckhoff\TwinCAT\3.1\Runtimes\UmRT_Default\start.bat`; on older installations it can be under `C:\TwinCAT\3.1\Runtimes\UmRT_Default\start.bat`. Check your installation.
3. In the UMRT console, write down the `AmsNetId:` value. Keep the runtime running.
4. In TwinCAT XAE, select that UMRT as the **Target System**, then activate the configuration, login to your PLC program, and start it (`RUN`). Make sure the PLC application contains the symbols specified in your simulator settings.
5. Double-click **`start_live_compat.cmd`** in the simulator root.
6. Enter the UMRT's AMS Net ID (six numbers) and the PLC ADS port (typically `851`). The utility checks the ADS state and reads each configured PLC symbol **without changing any PLC variables**.
7. Only when this diagnostic succeeds, confirm that you want to launch the existing simulator in LIVE mode. The simulator now drives its virtual sensor inputs; the student's PLC program is responsible for all motor/diverter outputs.

**CLI / headless read-only test:**

```cmd
py -3 tools\twincat_compat.py --net-id 199.4.42.250.1.1 --port 851 --check-only
```

Replace `199.4.42.250.1.1` with the **real value shown in your UMRT console**. This is only an example.

## Advanced / phase-3 multi-package example

The default config (`config/settings.json` or `config/settings.default.json`) is selected automatically. If your phase-3 project uses the additional diverter sensor, you can select your advanced configuration instead:

```cmd
py -3 tools\twincat_compat.py --config config\settings.phase3-advanced.json
```

This reads all the configured symbols (including `sensor_diverter` when present); it does **not** replace your advanced settings.

## Common connection issues

| Symptom | Cause to check |
|---|---|
| `ADS connection failed` | Separate UMRT not started, wrong *runtime* AMS Net ID, no appropriate route, or wrong ADS port |
| `ADS state not RUN` | Activate the configuration and start the PLC program in TwinCAT |
| `PLC symbol not found` | Declarations not downloaded, wrong name or wrong POU path (e.g. `MAIN` vs `PLC1.MAIN`) |
| Wrong `counter` type | `nCycleCounter` must be `UDINT`; the I/O variables used by this project must be `BOOL` |
| `pyads` cannot be imported | Run `install.cmd`; verify compatible Python and the ADS library installation |
| Live simulation does not match demo | Demo runs example logic; LIVE executes the PLC code currently loaded into TwinCAT |

### Important safety distinction

The initial **diagnostic is read-only**. Once the simulator itself is launched in LIVE mode it *will write its virtual button and sensor inputs* to the PLC, as designed. Do not connect this teaching simulator to a real machine or production PLC.

## Compatibility test status

The utility has automated tests with simulated ADS responses. **Real ADS integration on Windows + your TwinCAT 2024 UMRT remains to be verified**, as does a full test on 2026 or later releases. The installed version and product year should not be guessed from the AMS Net ID.

### References

- Beckhoff — Usermode Runtime FAQ: https://infosys.beckhoff.com/content/1033/tc170x_tc3_usermode_runtime/16309329035.html
- Beckhoff — Starting the UMRT: https://infosys.beckhoff.com/content/1033/tc170x_tc3_usermode_runtime/16309327883.html
- Beckhoff — ADS ports: https://infosys.beckhoff.com/content/1033/tc3_userinterface/7738288651.html
