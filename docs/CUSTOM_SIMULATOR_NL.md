# Custom Simulator — v0.9

## Gebruiken
1. Start `start_demo.cmd` en open **Custom Simulator** in het hoofdmenu.
2. Het voorbeeld bevat invoerbak IN, transportband, lichtsluis, opvangbak, drukknop en lamp.
3. Klik **Start / Verbinden**; klik op de groene drukknop om de demo-motor te starten of stil te zetten.
4. De invoerbak produceert volgens een instelbaar patroon, de band beweegt, de sensor detecteert pakketten en de opvangbak telt ze.
5. Klik **Stop** om te wijzigen; kies een component, wijzig de eigenschappen of versleep het object. Gebruik **Opslaan** / **Openen** voor eigen JSON-projecten.

## Nieuwe componenten
- **Invoerbak**: `mode = fixed | random | pattern`, `color = blue | orange | green | red | yellow | purple`, `pattern = blue,orange,green`, `interval` in seconden. Optionele PLC `enabled` uitgang: geen symbool betekent automatisch produceren.
- **Opvangbak**: `capacity` pakketten (1–250) en een `full` BOOL-ingang naar de PLC. Bij een volle opvangbak blijven pakketten op de band wachten; gebruik **Opvangbak leegmaken**.
- **Transportband**: `rotation = 0/90/180/270`, `length`, `speed` (virtuele eenheden per seconde), `motor` PLC-uitgang.
- **Lichtsluis**: plaats naast een transportband, bijvoorbeeld ongeveer 40 eenheden zijdelings van de hartlijn. De getekende straal loopt over de band. `detected` gaat waar als een pakket de meetpositie passeert.
- **Startpakket**: initieel object dat bij een nieuwe run op een dichtbije band wordt geplaatst. De permanente pakketproductie gebeurt via een invoerbak.

## Automatisch koppelen
- Plaats een invoerbak binnen 110 scene-eenheden van het **begin** van een band.
- Plaats een opvangbak binnen 110 eenheden van het **einde** van een band.
- Plaats de start van de volgende band maximaal 40 eenheden van het einde van de vorige.
- De editor biedt snapping bij verslepen; verbindingslijnen verschijnen automatisch. Dit zijn mechanische verbindingen, geen PLC-bedrading.
- Pakketten stoppen aan het einde als er geen vrije bestemming is. Overdracht naar een volgende band vergt dat de ontvangende band draait.

## Live ADS
Stel bij een component het bijbehorende `MAIN.*`-BOOL-symbool in. PLC-uitgangen worden door TwinCAT bepaald, ingangen door de simulator gemeten. Ontbrekende symbolen geven een diagnostische melding. De eventuele optionele invoerbak-enable kan leeg blijven: de bak is dan automatisch actief, ook in LIVE-modus.

Voor het oorspronkelijke voorbeeld geldt:
- `MAIN.bCustomMotor`: PLC -> motor
- `MAIN.bCustomSensor`: lichtsluis -> PLC
- `MAIN.bCustomButton`: drukknop -> PLC
- `MAIN.bCustomLamp`: PLC -> lamp

**Let op:** De offline demo is geen echte PLC-verbinding. Test ook met een echte Windows/TwinCAT UMRT vóór gebruik in de les.

## Opslag
Projectbestanden worden buiten de installatie opgeslagen in `%LOCALAPPDATA%\PLC-Simulation-Lab\projects`. Bestaande v0.8-projecten met JSON-versie 1 blijven bruikbaar.


## Weergave en navigatie (v0.9.1)

- **Muiswiel** boven de 2D-werkruimte: zoom in/uit rond de muiscursor (35%–500%).
- **Lege ruimte slepen**: pannen; ook **Shift+slepen**, **middelste muisknop** of **rechtermuisknop slepen**.
- **+ / −**: stapsgewijs zoomen rond het midden; **Reset**: terug naar 100% volledig overzicht.
- **Links slepen op een component**: component verplaatsen, uitsluitend in editmodus.
- Zoom en pan zijn alleen visuele weergave-instellingen: opgeslagen componentcoördinaten en PLC-symbolen veranderen niet.
- De renderer extrapoleert maximaal 180 ms tussen backend-updates voor vloeiende beweging. De backend behoudt de gezaghebbende simulatieposities.
