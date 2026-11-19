# PLC Simulation Lab — update v0.5 (layout + garagepoort)

## Installatie op je bestaande v0.4 project

1. Maak een **back-up** van de bestaande projectmap.
2. Kopieer de bestanden uit deze ZIP naar de root van je project, met behoud van de mapstructuur.
3. De ZIP bevat **geen** `README.md`, `License.md`, `frontend/style.css`, `backend/service.py` en **geen** `config/settings.json`. Je persoonlijke disclaimer en huidige werkende AMS Net ID blijven dus behouden.
4. De nieuwe bestand `config/settings.example.json` is slechts een naslagvoorbeeld en is **niet** de actieve configuratie.
5. De transportband gebruikt dezelfde PLC-symbolen als v0.3, inclusief `MAIN.bSensorReject`; de transportband-PLC-code hoeft niet aangepast te worden.
6. Start de bestaande `start_demo.cmd` of `start_live_compat.cmd`. Voor de transportband werkt de compatibiliteitscontrole zoals voorheen.

## Transportband — visuele en fysische wijziging

- De afvoerband is ongeveer 45 px korter.
- De diverter is circa 3,5 procentpunt naar links verplaatst.
- Het fysieke afbuigpunt is van genormaliseerde x=0.70 naar x=0.66 gegaan.
- De afvoerband is in de CSS naar hetzelfde x=0.66-punt verschoven.
- LS-03 is dynamisch gekoppeld aan y=0.62 van de **nieuwe** transportlengte en blijft werken.
- Zowel de horizontale als de neerwaartse beweging blijven afhangen van `MAIN.bConveyorMotor`; de selectie van het oranje pakket blijft afhangen van `MAIN.bDiverter`.

## Nieuwe module — garagepoort

- Tweede kaart op het startscherm is nu aanklikbaar.
- Onafhankelijk simulatiemodel voor poortpositie van 0% (gesloten) naar 100% (open).
- Eén druktoets, twee eindeloopcontacten, twee motoruitgangen en een cycluscounter.
- Er is een **offline demo** en een afzonderlijk LIVE ADS-profiel dat uitsluitend zijn eigen symbolen aanspreekt.
- Er is een conflictbeveiliging in het fysische model: als beide richtingen TRUE zijn, beweegt de poort niet en verschijnt een waarschuwing. De student moet de logica in TwinCAT zelf correct implementeren.

### Garagepoort testen zonder TwinCAT

1. Dubbelklik `start_demo.cmd`.
2. Klik op de garagepoortkaart en daarna **Verbinden**.
3. Druk op **DRUKTOETS S-01**. De poort opent gedurende circa 4 seconden.
4. Aan het einde wordt `LS-OPEN` actief. Druk nogmaals: de poort sluit tot `LS-CLOSED`.
5. Druk tijdens de beweging op de knop om te stoppen (tweede druk). Opnieuw drukken hervat het openen volgens de bijgeleverde demologica.

### Garagepoort testen met echte TwinCAT PLC-code

1. Gebruik in TwinCAT voor de garagepoort een **apart oefenproject** met `PROGRAM MAIN`.
2. Voeg `twincat/GARAGE_MAIN_declarations.txt` toe aan de `VAR`-declaraties van `MAIN`, niet als een tweede `PROGRAM MAIN`. De docent kan een voorbeeldalgoritme vinden in `docs/GARAGE_MAIN_example_TEACHER_ONLY.st`. Deze voorbeeldoplossing is **niet bedoeld om aan studenten te verspreiden**.
3. Declareer ook `bGateWasPressed : BOOL := FALSE;` als je de docentendemocode gebruikt.
4. Build, activeer je PLC-project op de juiste UMRT, Login en RUN.
5. Controleer dat je actieve `config/settings.json` nog steeds je werkelijke UMRT AMS Net ID en ADS-poort bevat.
6. Start de app met **`start_live.cmd`**, niet via `start_live_compat.cmd` zolang de garagepoort-PLC is geladen: de bestaande compatibiliteitslauncher verwacht namelijk de **transportband-symbolen**, en keurt het garagepoortprogramma anders terecht af.
7. Kies Garagepoort → Verbinden. Bij ontbrekende symbolen krijg je een duidelijke ADS-fout.
8. Schakel niet tussen beide **LIVE-verbindingen** zonder eerst op Verbreken te klikken. De app blokkeert een tweede gelijktijdige verbinding.

### Garagepoortvariabelen in `MAIN`

| Richting | Naam | Type |
|---|---|---|
| Python → PLC | `bGateButton` | BOOL |
| Python → PLC | `bGateLimitOpen` | BOOL |
| Python → PLC | `bGateLimitClosed` | BOOL |
| PLC → Python | `bGateMotorOpen` | BOOL |
| PLC → Python | `bGateMotorClose` | BOOL |
| PLC → Python | `nGateCycleCounter` | UDINT |

**Opgelet:** De simulator gebruikt momenteel *één motoruitgang voor beide transportbanden*; de garagepoort heeft twee **andere** motoruitgangen. Het zijn gescheiden oefeningen. Bij LIVE garagepoort moeten de PLC-symbolen van het geladen garageproject overeenkomen. De ADS-net-ID wordt gedeeld met de transportbandconfiguratie.

## Tests

```cmd
py -3 -m unittest discover -s tests -p "test_v05_garage.py" -v
```

Deze tests gebruiken Python-demomodi; echte TwinCAT-ADS moet je op je eigen Windows-pc testen. De oorspronkelijke `tests/test_phase1.py` en enkele `test_phase2.py`-verwachtingen zijn al verouderd en niet automatisch aangepast in deze update.

## Belangrijke distributienota

PyInstaller en het toekomstige docent-uitbreidingssysteem zijn nog niet aanwezig. De voorbeeldoplossing `docs/GARAGE_MAIN_example_TEACHER_ONLY.st` moet buiten een toekomstige studentenrelease blijven. Een `.exe` op basis van Python garandeert geen volledige codebeveiliging.
