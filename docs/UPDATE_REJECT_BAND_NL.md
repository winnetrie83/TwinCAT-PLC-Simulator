# Update 0.3 — loodrechte reject-band + LS-03

## Installatie op je bestaande repo (GEEN GitHub-wijzigingen)

1. Maak eerst een back-up van je huidige map en van je eigen `config/settings.json`.
2. Kopieer de inhoud van deze ZIP naar de **hoofdmap** van je bestaande project;
   vervang uitsluitend de bestanden die in de ZIP staan. `README.md`, `License.md`,
   `app.py`, `backend/service.py`, je bestaande `frontend/style.css` en overige
   bestanden worden NIET geleverd of overschreven.
3. LET OP: `config/settings.json` in deze ZIP heeft de voorbeeld-Net ID
   `127.0.0.1.1.1`. **Herstel je werkende AMS Net ID** (bij jou eerder
   `199.4.42.250.1.1`) en bevestig of ADS-poort `851` klopt. Je kunt ook
   je eigen settings-bestand behouden en enkel de regel toevoegen:
   `"sensor_reject": "MAIN.bSensorReject"` onder `symbols`.
4. Open je TwinCAT-project. Voeg in de declaraties van `MAIN` dit toe:
   `bSensorReject : BOOL := FALSE;`
   Of gebruik het volledige voorbeeld `twincat/MAIN_declarations.txt` indien
   je nog dezelfde voorbeeld-POU gebruikt. **Laat je bestaande PLC-logica staan.**
   `twincat/MAIN_implementation.st` is alleen de oorspronkelijke docentendemocode.
5. Build het PLC-project, activeer je configuratie indien nodig, log opnieuw in,
   start PLC in RUN en controleer `MAIN.bSensorReject` in de symbolen.
6. Start `start_live_compat.cmd` met je werkelijke UMRT Net ID en poort 851.
   Alle symbolen, inclusief de nieuwe LS-03, moeten leesbaar zijn.
7. Druk op START en voeg een oranje pakket toe. D-01 moet actief worden en
   het pakket loodrecht naar beneden overnemen. Bij LS-03 gaat de indicator
   kort rood en wordt `MAIN.bSensorReject` TRUE, daarna weer FALSE.

## Techniek

- De bestaande `MAIN.bConveyorMotor` laat beide banden bewegen.
- De bestaande `MAIN.bDiverter` beslist of er wordt afgesplitst.
- Het pakket blijft op een vaste x-positie op de reject-band en beweegt
  alleen nog langs de neerwaartse y-as.
- LS-03 is een virtuele ingang: **Python schrijft**, TwinCAT kan lezen.
- De referentie-PLC-code hoeft LS-03 nog niet te gebruiken; je kunt deze
  later bij oefeningen inzetten voor tellers of alarmen.
- Om overzichtelijk te blijven, staat er nog steeds één pakket tegelijk op
  het transportsysteem. Meerdere pakketten volgen in een latere fase.

## Test

`py -3 -m unittest discover -s tests -p "test_reject_conveyor.py" -v`

De bestaande oude `tests/test_phase1.py` verwijst nog naar verwijderde fase-1
interfaces en is ook in de oorspronkelijke repository niet compatibel met
fase 2. `tests/test_phase2.py` telt nog exact zes ADS-schrijfacties; door LS-03
is dat in de huidige code zeven. Deze verouderde tests moeten apart worden
bijgewerkt; ze zijn niet stilzwijgend aangepast in deze ZIP.

## Opmerking

De hoofdband, de overgang en de reject-band zijn een vereenvoudigde virtuele
machine. Er is nog geen aparte reject-motor of fysieke botsingsdetectie.
