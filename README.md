# PLC Simulation Lab — Fase 1 (ADS Proof of Concept)

**Versie:** 0.1 · **Platform:** Windows + TwinCAT 3 · **Talen:** Structured Text, Python, HTML/CSS/JavaScript  
**Doel:** aantonen dat een *lokaal uitgevoerde* TwinCAT PLC-runtime variabelen kan uitwisselen met een Python-applicatie via ADS, zonder fysieke PLC.

> **Belangrijk:** dit is fase 1, geen volledige transportbandsimulatie. De motoranimatie volgt de PLC-uitgang, maar een pakket beweegt nog niet door het systeem. De lichtsluis is daarom **handmatig**. De demomodus vervangt TwinCAT door een eenvoudige Python-nabootsing om de interface te testen; hij bewijst geen ADS-communicatie.

## Wat zit in dit project?

- `twincat/MAIN_declarations.txt` — declaraties voor `PROGRAM MAIN` in TwinCAT.
- `twincat/MAIN_implementation.st` — eenvoudige PLC-logica die je in TwinCAT plakt.
- `backend/plc.py` — echte ADS-communicatie via `pyads` plus afzonderlijke offline demonstratiemodus.
- `app.py` — hoofdprogramma, PyWebView-interface en optionele CMD-console.
- `frontend/` — eerste scherm met motor, knoppen, lichtsluis en een I/O-monitor.
- `config/settings.json` — AMS Net ID, PLC-runtimepoort en symbolen.
- `tests/` — automatische tests zonder TwinCAT.
- `start_demo.cmd`, `start_live.cmd`, `start_cli.cmd` — opstartbestanden voor Windows.

## Benodigdheden

1. **Windows 10 of Windows 11**.
2. **Python 3.11 of 3.12 (64-bit aanbevolen)**, geïnstalleerd en toegankelijk via `py` of `python`.
3. **TwinCAT 3 XAE + een lokale PLC-runtime** voor de *echte* ADS-test. Als Windows Hyper-V/VBS de realtime-runtime blokkeert, gebruik dan **Usermode Runtime (UMRT)**. Vanaf TwinCAT 3.1 build 4026 is die beschikbaar, zonder harde realtimegarantie.
4. Voor het desktopvenster: **Microsoft Edge WebView2 Runtime** (meestal reeds aanwezig op Windows 11).
5. Internetverbinding **alleen voor het eenmalig installeren van Python-dependencies**.

De Windows-ADS-bibliotheek wordt normaliter door TwinCAT aangeleverd. De PLC-runtime kan afhankelijk van de geïnstalleerde componenten/licenties een testlicentie vereisen. Voor fase 1 hoef je geen fysieke PLC aan te sluiten.

## A. Eerst de demo-interface proberen (zonder TwinCAT)

1. Pak deze ZIP uit, bijvoorbeeld naar `C:\PLC_Simulation_Lab_Fase1`.
2. Dubbelklik **`install.cmd`**. Het installeert `pyads` en `pywebview`.
3. Dubbelklik **`start_demo.cmd`**.
4. Klik in het desktopvenster op **Verbinden**, dan op **START**.
5. De motorindicator wordt groen en de bandanimatie beweegt.
6. Zet de lichtsluis aan: de motor stopt. Zet de lichtsluis uit en druk opnieuw op START.
7. **STOP** stopt de motor direct.

De interface toont nu `DEMONSTRATIE`. Dat is een lokale oefenmodus **zonder** echte TwinCAT-runtime.

## B. TwinCAT-project aanmaken voor de echte ADS-test

1. Open **TwinCAT XAE**.
2. Maak een nieuw **TwinCAT XAE Project** en voeg een **Standard PLC Project** toe onder PLC (of gebruik een bestaand PLC-project).
3. Open de POU **MAIN** in **Structured Text (ST)**. Maak MAIN aan als die ontbreekt.
4. Plak de inhoud van `twincat/MAIN_declarations.txt` in het **declaratiegedeelte** van MAIN. Daar staat `PROGRAM MAIN`, `VAR`, enzovoort.
5. Plak de inhoud van `twincat/MAIN_implementation.st` in het **implementatiegedeelte** van MAIN, onder de declaraties. Het zijn twee verschillende editorvakken.
6. **Build** het PLC-project en controleer of er geen fouten zijn.
7. Selecteer je **lokale runtime** als TwinCAT-target. Als je eerder naar **UMRT** moest overschakelen om lokaal te kunnen draaien, gebruik diezelfde Usermode Runtime opnieuw. De gekozen UMRT kan een eigen AMS Net ID hebben.
8. Kies **Activate Configuration**, bevestig de meldingen, daarna **PLC → Login** en **PLC → Start** (`F5`). De PLC-code moet in RUN staan, niet alleen de systeemconfiguratie.
9. Controleer online in TwinCAT dat `MAIN.nCycleCounter` blijft oplopen.

**Gebruik geen `AT %I*` / `AT %Q*`-hardwarekoppelingen voor deze proef.** De Python-app spreekt de normale PLC-symbolen direct aan. Er zijn geen fysieke I/O-modules nodig.

### De vijf PLC-symbolen

| Symbool | Type | Wie schrijft? | Betekenis |
| --- | --- | --- | --- |
| `MAIN.bStartButton` | `BOOL` | Python | Virtuele START-drukknop (250 ms puls) |
| `MAIN.bStopButton` | `BOOL` | Python | Virtuele STOP-drukknop (250 ms puls) |
| `MAIN.bSensor` | `BOOL` | Python | Virtuele lichtsluis (handmatig aan/uit) |
| `MAIN.bMotor` | `BOOL` | TwinCAT | Motoruitgang |
| `MAIN.nCycleCounter` | `UDINT` | TwinCAT | Telt PLC-cycli op |

De minimale ST-code laat de motor **in werking blijven na een START-puls**, en laat STOP of sensor voorrang hebben. Dit bewijst dat Python niet zelf de motorbesturing uitvoert.

## C. Echte verbinding met de lokale TwinCAT-runtime

1. Open `config/settings.json` met Kladblok/VS Code.
2. Vul bij `ams_net_id` de **AMS Net ID van de geselecteerde TwinCAT-targetruntime** in. Het getoonde `127.0.0.1.1.1` is **een voorbeeld** en hoeft op jouw computer niet juist te zijn. Je vindt de juiste Net ID via **TwinCAT System → Routes / NetId Management**, de TwinCAT-tray/router of in de targetkeuze van XAE. **Kies niet automatisch de Net ID van een andere lokale runtime als je UMRT gebruikt.**
3. Laat `ads_port` op `851` staan als je de eerste PLC-runtime gebruikt (PLC1). Een tweede runtime kan poort `852` gebruiken.
4. Controleer dat de symbolenamen overeenkomen met jouw MAIN-programma. Houd de symbolen herkenbaar, of pas ze in JSON aan.
5. Dubbelklik **`start_live.cmd`**.
6. Klik op **Verbinden**. Als de verbinding lukt, zie je onder andere `nCycleCounter` oplopen.
7. Druk op **START**: `bMotor` wordt TRUE en de animatie start.
8. Activeer **Lichtsluis LS-01**: `bMotor` wordt FALSE en de animatie stopt.
9. Zet de lichtsluis uit; druk weer op **START**. Test daarna **STOP**.

**Let op:** Dit is een **lokale** proef. Er wordt geen route naar externe PLC's automatisch geconfigureerd. Voer dit niet uit tegen een fysieke installatie of productiebesturing.

## D. Liever eerst via CMD testen?

Dezelfde backend kan zonder PyWebView getest worden:

```cmd
cd /d C:\PLC_Simulation_Lab_Fase1
py -3 app.py --cli --demo
```

Of voor de echte TwinCAT-runtime:

```cmd
py -3 app.py --cli
```

Beschikbare consoleopdrachten:

```text
connect
status
start
sensor on
sensor off
stop
disconnect
quit
```

Met `status` lees je alle vijf variabelen in. START en STOP zijn **geen blijvende TRUE**, maar een puls van 250 milliseconden; deze tijd is instelbaar via `pulse_ms`.

## E. Wat moet je zien wanneer alles klopt?

**Controle 1 — PLC echt actief:** `MAIN.nCycleCounter` loopt op. Een stilstaande teller wijst erop dat MAIN niet draait, of dat je de verkeerde runtime observeert.

**Controle 2 — schrijven Python → TwinCAT:** als je in de GUI op START klikt, wordt `MAIN.bStartButton` kort TRUE in TwinCAT.

**Controle 3 — lezen TwinCAT → Python:** de PLC zet `MAIN.bMotor` TRUE; de GUI geeft de motor als TRUE weer.

**Controle 4 — rondgang:** de GUI schrijft `MAIN.bSensor = TRUE`; de PLC verwerkt dit; `MAIN.bMotor` gaat FALSE; de GUI toont dat resultaat. Daarmee zijn beide richtingen bewezen.

De statusweergave vraagt periodiek de PLC-waarden op (fase 1: ongeveer drie keer per seconde). De daadwerkelijke PLC-cyclus draait onafhankelijk van die weergavefrequentie.

## F. Als iets niet werkt

| Symptoom | Controle |
| --- | --- |
| `py` of `python` onbekend | Python installeren of aan PATH toevoegen; daarna CMD opnieuw openen |
| `No module named pyads` | `install.cmd` opnieuw uitvoeren met de Python-interpreter waarmee je ook opstart |
| `TcAdsDll.dll` of ADS-bibliotheek ontbreekt | TwinCAT/ADS Runtime op Windows installeren of herstellen |
| Doelpoort niet gevonden (ADS 0x6) | Staat de PLC-runtime in RUN? Is PLC1 op poort 851 bereikbaar? |
| AMS-route fout (ADS 0x7) | Net ID uit target controleren; bij UMRT de juiste runtime kiezen |
| `symbol not found` | Exacte symboolnaam, MAIN, datatype en geactiveerd/ingelogd project controleren |
| Verbonden, maar motor reageert niet | PLC-code in **RUN**? Teller loopt op? Is sensor uitgeschakeld? |
| Geen zichtbaar venster | WebView2 Runtime controleren; probeer de `--cli`-modus |
| TwinCAT meldt licentieprobleem | Benodigde PLC-runtime-licentie/trial of schoollicentie controleren |
| UMRT target niet beschikbaar | Usermode Runtime via TwinCAT Package Manager installeren en starten |

## G. Tests uitvoeren

```cmd
cd /d C:\PLC_Simulation_Lab_Fase1
py -3 -m unittest discover -s tests -v
```

Deze automatische tests controleren de demo en de Python-ADS-adapter met een nep-ADS-bibliotheek. **Ze bewijzen niet dat de echte Beckhoff-runtime op jouw computer werkt.** De echte test voer je zelf uit met stappen B en C.

## Wat doen we in fase 2?

De handmatige lichtsluis vervangen door echte **pakketpositie-simulatie**, een transportband met instelbare snelheid, meerdere lichtsluizen, een diverter en afwisselende oefeningen. Ook dan blijft de **PLC-code** verantwoordelijk voor de besturingsbeslissingen. Python simuleert alleen de machine en wisselt I/O uit.

## Bronnen / naslag

- Beckhoff – PLC project activeren, inloggen en starten: https://infosys.beckhoff.com/content/1033/tc3_plc_intro/3470887819.html
- Beckhoff – Usermode Runtime installatie: https://infosys.beckhoff.com/content/1033/tc170x_tc3_usermode_runtime/11319883275.html
- Beckhoff – Verschil tussen real-time en user-mode runtime: https://infosys.beckhoff.com/content/1033/tc3_installation/20830884491.html
- pyads – Connection/read_by_name/write_by_name: https://pyads.readthedocs.io/en/stable/documentation/connection.html
- pyads – Windows-installatie: https://pyads.readthedocs.io/en/latest/installation.html
- pyads op PyPI: https://pypi.org/project/pyads/
- pywebview op PyPI: https://pypi.org/project/pywebview/
