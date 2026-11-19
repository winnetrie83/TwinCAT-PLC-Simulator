# Drukvat en twee pompen — docenten- en testinformatie

## Doel
Studenten implementeren in TwinCAT de besturing van een virtuele tank met vulpomp P1 en afvoerpomp P2. De PLC **bepaalt de commando's**; Python levert sensoren aan en rekent het niveau / de demonstratieve druk uit. Er zijn **geen** fysieke I/O-klemmen nodig.

## Variabelen voor PROGRAM MAIN

| Symbool | PLC datatype | Schrijver | Betekenis |
|---|---|---|---|
| `MAIN.bTankStart` | BOOL | simulator | START-puls van ca. 250 ms |
| `MAIN.bTankStop` | BOOL | simulator | STOP-puls van ca. 250 ms |
| `MAIN.bTankLevelLow` | BOOL | simulator | TRUE bij niveau <= 25% |
| `MAIN.bTankLevelHigh` | BOOL | simulator | TRUE bij niveau >= 80% |
| `MAIN.bTankPressureHigh` | BOOL | simulator | TRUE bij druk >= 185 kPa |
| `MAIN.fTankPressure` | REAL | simulator | modeldruk in kPa |
| `MAIN.bPumpIn` | BOOL | TwinCAT | vulpomp P1 |
| `MAIN.bPumpOut` | BOOL | TwinCAT | afvoerpomp P2 |

De voorbeelddeclaraties staan in `twincat/TANK_MAIN_declarations.txt`. Alleen de docent mag het voorbeeld in `docs/TANK_MAIN_example_TEACHER_ONLY.st` gebruiken. In de studentenopgave horen enkel I/O-specificaties en gewenste werking te staan.

## Werkingsmodel
- Startniveau: 35%; bij P1 = TRUE stijgt het niveau met 10 procentpunten per seconde; P2 = TRUE verlaagt het met 7 procentpunten per seconde.
- Berekeningsformule: `druk_kPa = 25 + 1.8 * niveau_procent`. Dit is **uitdrukkelijk een didactische benadering**, geen fysiek accurate drukvatberekening.
- Bij 100% wordt het niveau begrensd; de status kan aangeven dat overloop zou zijn opgetreden.
- Hoog en laag zijn afzonderlijke niveausensoren; op het exacte overgangspunt kan een PLC deze bits direct uitlezen.
- Een ontbrekend PLC-symbool leidt tot een diagnostische melding, maar de ADS-verbinding mag blijven bestaan. Bij een ontbrekende pompmapping blijft die pomp uit.
- In demomodus gebruikt de simulator een eenvoudige ingebouwde voorbeeldbesturing; in LIVE komen de pompcommando's **uitsluitend** uit TwinCAT.

## Zelf testen (Windows)
1. Start TwinCAT XAE en selecteer de juiste runtime (inclusief eventuele aparte UMRT).
2. Voeg declaraties toe aan `PROGRAM MAIN` en schrijf eigen besturingslogica in ST, of gebruik uitsluitend als docent de voorbeeldimplementatie.
3. Build, activate, login, RUN.
4. Selecteer in het hoofdmenu het juiste verbindingsprofiel (AMS Net ID en PLC1-poort, meestal 851).
5. Open **Drukvat & pompen**, klik **Verbinden** en vervolgens **START**. Test de LOW/HIGH- en druksignalen plus de pompopdrachten.
6. Controleer STOP, ontbrekende symbolen, verbreken/herverbinden, en de demomodus apart.

## Waarschuwingen
- Gebruik uitsluitend een test-runtime of offline demonstratie: **niet aansluiten op een fysieke productie-installatie**.
- Voor reële drukvaten zijn gecertificeerde veiligheidsvoorzieningen, onafhankelijke limieten en andere dynamische modellen noodzakelijk. Deze simulatie is niet geschikt voor veiligheidsanalyse.
- Testen met echte TwinCAT/UMRT en volledige Windows GUI moeten nog op de doelcomputer uitgevoerd worden.

## v1.0.1 correctie: gedrag bij 80%
- Drukalarm staat nu op **185 kPa**. Bij 80% bedraagt de demonstratieve druk 169 kPa; het alarm grijpt dus niet meer voortijdig in bij 75%.
- **DEMO standaard:** P1 vult tot exact 80% en blijft daarna uit; P2 blijft uit.
- **DEMO optioneel:** vink 'automatisch leegpompen' aan om automatisch tussen 25% en 80% te pendelen. De fysieke demo begrenst het niveau precies op de drempels.
- **LIVE:** geen automatische grensbegrenzing op 25% of 80%; de **studenten-PLC** moet de pompen zelf stoppen en sturen. De simulator blokkeert wel tegenstrijdige gelijktijdige pompbeweging en toont een waarschuwing.
- Het docent-ST-bestand blijft een voorbeeld van **automatisch pendelen**, niet van 'vasthouden op 80%'.
