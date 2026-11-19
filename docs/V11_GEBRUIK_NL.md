# v1.1 — I/O-mapping en PLC-oefeningtests

## Installatie
Dit is een **overlaypatch boven op v1.0.1**; geen zelfstandig distributiepakket. Maak eerst een back-up van je project. Sluit de applicatie af en kopieer de meegeleverde bestanden naar de projectroot met behoud van de directorystructuur. De bestaande `README.md`, disclaimer, licentie, `config/settings.json`, TwinCAT-projecten en gebruikersprojecten worden niet overschreven.

Start daarna `start_demo.cmd` of `start_live.cmd`.

## I/O-mapping
In de applicatie staat een knop **PLC I/O-mapping & oefeningtests** rechtsonder. Kies een van de drie vaste oefeningen (transportband, garagepoort of drukvat), pas de PLC-symbolen aan en kies *Mapping opslaan*. De gewijzigde symbolen worden onmiddellijk van kracht voor nieuwe verbindingen. Verbreek eerst elke actieve simulatorverbinding. De knop *Standaard herstellen* zet de waarden van de installatieconfiguratie terug.

De mappings staan per gebruiker in `%LOCALAPPDATA%\PLC-Simulation-Lab\io_mapping.json`. De bestaande ADS-profielen blijven in `connections.json`. De Custom Simulator gebruikt zijn eigen dynamische PLC-koppelingen in de opgeslagen project-JSON en is **niet** onderdeel van dit scherm.

Let op: ontbrekende symbolen blijven zichtbaar in de live-I/O-diagnostiek. Een geldige symboolnaam betekent **niet** dat die daadwerkelijk in TwinCAT bestaat of het juiste datatype heeft. De LIVE-verbinding controleert dat pas bij verbinden.

## Gedragstests
1. Selecteer de vaste oefening, verbind in DEMO of met een **lokale didactische TwinCAT-runtime**.
2. Open *PLC I/O-mapping & oefeningtests* en kies dezelfde oefening.
3. Klik *Testscenario starten* en bevestig dat virtuele drukknoppen worden bediend.
4. Wacht tot het resultatenpaneel de geslaagde en mislukte controles vermeldt.

Geteste scenario's:
- Transportband: START activeert de motor; STOP schakelt hem weer uit.
- Garagepoort: bij een **volledig gesloten** poort activeert de drukknop de openingsmotor; beide motoren zijn niet gelijktijdig actief; de open-eindschakelaar stopt de openingsmotor.
- Drukvat: bij beginstand onder 78% schakelt START P1 in, de bovengrens bij 80% stopt P1 en er is geen pompconflict.

Deze tests **bedienen de PLC-ingangen** en zijn daarom niet geschikt voor een echte fysieke machine of productie-PLC. Het is geen veiligheidskeuring, volledige testdekking of automatische ST-codebeoordeling. Een mislukte test kan ook door een ongeschikt beginniveau of door een andere bedoelde PLC-implementatie komen. De tests wijzigen geen actuatoruitgangen rechtstreeks; de PLC blijft besturend. Bij een onderbreking wordt waar mogelijk een STOP-puls verzonden, maar dat vervangt geen veilige PLC-logica.

## Custom Simulator
- Geselecteerde componenten kunnen met **Ctrl+D** of de knop **Dupliceren** worden gekopieerd. PLC-symbolen van kopieën blijven bewust leeg om conflicten te vermijden.
- Transportbanden kunnen met **R** of de knop **Roteer 90°** worden gedraaid (alleen in Edit Mode).
- Animatievoorspelling voor links- en omhooglopende transportbanden is verbeterd.
- Namen van PLC-symbolen worden bij validatie getrimd, zodat spaties aan de uiteinden geen onverwachte mappings opleveren.

## Tests
Vanuit de projectroot:

```cmd
py -3 -m unittest discover -s tests -v
```

De nieuwe module `tests/test_v11_features.py` controleert opslag, validatie en het testsysteem met fake services. Een echte TwinCAT/UMRT-integratietest en een Windows-GUI-test moeten op de doelcomputer gebeuren.
