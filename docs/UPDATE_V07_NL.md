# v0.7 — tolerant PLC-symbolen en symbolenoverzicht

Deze ZIP is een **patch bovenop v0.6**. Maak een back-up van je project, sluit de applicatie en kopieer de inhoud van `PLC_Simulation_Lab_v0.7_Update` over de projectroot. README.md, License.md, config/settings.json, alle profielen en TwinCAT-code worden niet overschreven.

Start met `start_live.cmd`. Als een PLC-project minder symbolen declareert dan de geselecteerde module verwacht, blijft de ADS-verbinding bestaan. De GUI toont **Ontbrekend** voor symbolen die niet gevonden werden. Motoruitgangen zonder PLC-symbool worden veilig als UIT beschouwd; invoersignalen zonder symbool worden niet geschreven. De simulator creëert of forceert **geen** ontbrekende symbolen. Een oefening kan dan bewust onvolledig blijven werken.

Onder `LIVE I/O` toont het nieuwe diagnostiekpaneel extra onbekende variabelen onder `MAIN.*` wanneer de ADS-server het symbolenoverzicht beschikbaar stelt. Extra symbolen worden nooit aangestuurd, slechts getoond. Indien het overzicht niet beschikbaar is, meldt de GUI dit uitdrukkelijk. Bekende symbolen worden gecontroleerd op de verwachte PLC-types (BOOL, cycluscounter UDINT). Verkeerde datatypes en andere ADS-fouten blijven echte fouten; een onbereikbare runtime is niet hetzelfde als een ontbrekend symbool.

De oude `start_live_compat.cmd` blijft een **strikte precheck** en kan ontbrekende symbolen nog blokkeren. Gebruik vanaf v0.7 `start_live.cmd` om de tolerante symbolencontrole te gebruiken.

Test de offline code met:

```cmd
py -3 -m unittest discover -s tests -p test_symbol_diagnostics.py -v
```

**Let op:** de patch is lokaal met gesimuleerde ADS-antwoorden getest. Een echte integratietest met jouw Windows/UMRT is nog nodig. Alleen de nieuwe test wordt door het commando hierboven uitgevoerd; oudere tests in de originele repository zijn mogelijk achterhaald.
