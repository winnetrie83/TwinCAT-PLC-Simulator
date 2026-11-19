# PLC Simulation Lab — changelog

## v1.1 — I/O-mapping, oefeningtests en stabiliteit (19 november 2026)

### Added
- Instelbare PLC-symbolen voor de drie vaste oefeningen via een centrale interface; permanente opslag per gebruiker buiten de projectroot.
- Geautomatiseerde gedragscontroles voor de aangesloten transportband-, garagepoort- en drukvat-PLC; asynchrone uitvoering met afzonderlijk resultatenpaneel.
- Componenten dupliceren (Ctrl+D) en transportband 90° roteren (R) in de Custom Simulator.
- Documentatie van installatie, risico's en tests in `docs/V11_GEBRUIK_NL.md`.

### Fixed
- Voorspelling van pakketbeweging bij omgekeerde of verticaal omhoog draaiende transportbanden.
- Spaties rond Custom Simulator PLC-symbolen worden consistent getrimd.
- I/O-mapping en ADS-profielwijzigingen worden geweigerd tijdens nog draaiende simulatorworkers.
- Configuratiefouten van het nieuwe mappingbestand worden met een duidelijke melding opgevangen.

### Limitations
- Overlay op de v1.0.1-installatie; geen zelfstandig pakket of Windows `.exe`.
- Nieuwe tests zijn observaties van PLC-gedrag, geen formele beoordeling of veiligheidstest.
- Echte TwinCAT-UMRT en volledige Windows-GUI blijven nog handmatig te testen.


## v1.0.1 — Tank 80%-grens en demomodi (19 november 2026)

### Fixed
- Drukalarm grijpt niet langer bij 75% in; grens verhoogd van 160 kPa naar 185 kPa.
- In DEMO stopt P1 exact op 80% (zonder afrondingsovershoot).
- Tegenstrijdige pompcommando’s blokkeren de gesimuleerde vloeistofbeweging en tonen een waarschuwing.
- Onbereikbaar statement na Custom Simulator disconnect verwijderd.

### Added
- Demo-optie voor automatisch pendelen tussen 25% en 80%; standaard wordt op 80% vastgehouden.
- Nieuwe regressietests voor de 80%-grens, modi, drukalarm en pompconflict.

### Important
- LIVE blijft onder volledige PLC-besturing. De demoniveau-clamp is uitgeschakeld in LIVE.


## v1.0 — Derde vaste oefening: Drukvat en twee pompen (19 november 2026)

### Added
- Nieuwe drukvatsimulator als **derde vaste oefening** in het bestaande hoofdmenu.
- Twee virtuele pompen: vullen (P1) en afvoeren (P2), niveau- en drukweergave.
- Virtuele laag/hoog-niveausensoren, hogedruksensor, REAL-drukwaarde en start/stop-pulsen.
- ADS-uitwisseling met symbolendiagnostiek voor ontbrekende symbolen en afzonderlijke demologica.
- Docentvoorbeeld Structured Text en studentgerichte PLC-declaraties.
- Automatische tests voor fysica, drempelwaarden, controllers en ontbrekende ADS-symbolen.

### Changed
- De Custom Simulator toont bij een invoerbak alleen de kleurinstellingen die bij de actieve aanvoermodus horen.
- Verbindingen en ADS-profielwissel respecteren nu ook de nieuwe drukvatsimulator.
- Verhoogde weergegeven versie naar v1.0; bestaande README en disclaimer worden niet overschreven.

### Known limitations
- De drukberekening is didactisch en nadrukkelijk niet bedoeld voor veiligheids- of industrieel drukvatontwerp.
- De Windows/PyWebView-weergave en echte TwinCAT 2024/UMRT-verbinding dienen op de doelcomputer te worden getest.
- Uitgifte is een **overlay-ZIP** op de bestaande werkende versie v0.9.1, geen zelfstandig installatiepakket of `.exe`.


## v0.9.1 — Vloeiendere animaties en camerabediening (19 november 2026)

### Fixed
- Bewegende bandstrepen blijven zichtbaar **binnen** de transportband dankzij een afzonderlijk SVG clipPath per band.
- PLC-statusupdates bouwen niet langer de volledige scène opnieuw op; de visuele pakkettoestand blijft behouden.
- Pakketanimatie voorspelt kort tussen ontvangen simulatiesnapshots en corrigeert vloeiend op de echte backend-positie.
- Bandstrepen bewegen frame-onafhankelijk op basis van delta time; bij stilstand stoppen ze.

### Added
- Zoomen met muiswiel op de cursorpositie, plus knoppen + / − en zoomreset.
- Panning door een lege plek te slepen, via Shift+slepen of middelste/rechtermuisknop.
- Zichtbare zoomindicator en korte muisbedieningshints in de editor.

### Limitations
- 2D-editor is nog geen geavanceerd CAD-pakket; echte ADS/UMRT en GUI-weergave dienen op Windows getest te worden.
- Project- en simulatielogica blijven ongewijzigd; deze versie focust op rendering en navigatie.

## v0.9 — Advanced 2D (19 november 2026)

### Added
- Invoerbakken met vast, willekeurig of herhalend kleurpatroon en instelbaar interval.
- Opvangbak met capaciteit en vol-signaal, automatische pakketoverdracht en meerdere gekoppelde transportbanden.
- Lichtsluis naast de band met detectiestraal, roteerbare banden en plaatsings-snapping.
- Pakketbeweging en aanvullende Python-tests voor het procesmodel en gesimuleerde ADS-communicatie.


## v0.8 — Modular Custom Simulator (19 november 2026)

### Added
- Modulaire Python-engine met componentdefinities, basisfysica, virtuele ingangen/uitgangen en uniforme projectvalidatie.
- Eerste Custom Simulator 2D-editor: componenten toevoegen, verslepen, verwijderen en eigenschappen configureren.
- Ondersteuning voor transportband, lichtsluis, drukknop, signaallamp en pakket.
- Dynamische BOOL-koppelingen per component naar TwinCAT ADS en feedback over ontbrekende symbolen.
- Projecten opslaan/laden als JSON buiten de installatie (LocalAppData).
- Eigen offline demo waarin de drukknop de motor schakelt (géén PLC-test).
- Unit tests voor componentvalidatie, beweging, sensoren, opslag en demomodus.

### Changed
- Bestaand hoofdmenu wordt met een extra Custom Simulator-kaart uitgebreid.
- ADS-profielwissel is ook verboden zolang een Custom Simulator actief is.
- Geen nieuwe afzonderlijke UPDATE_Vxx-bestanden meer.

### Limitations
- Dit is de eerste **functionele 2D-editor**, niet een volledige machine-CAD-editor. Vrije geometrische koppelingen, kabels, meerdere transportsystemen, geavanceerde botsingen en 3D zijn vervolgwerk.
- De custom-componenten gebruiken momenteel uitsluitend BOOL-I/O.
- Er is geen echte UMRT/ADS-integratietest uitgevoerd in de ontwikkelomgeving.
- De bestaande garage- en transportbandservices blijven intact voor backwards compatibility; de gezamenlijke engine voor *alle* oefeningen is nog niet afgerond.

## v0.7 — Tolerante PLC-symbolen en symbolenoverzicht
- Ontbrekende symbolen verhinderen niet automatisch de verbinding; veilige fallback voor outputs.
- Dynamisch symbolenoverzicht onder `MAIN.*` waar beschikbaar; onbekende symbolen worden niet geschreven.
- Typefouten en andere ADS-problemen blijven echte fouten.

## v0.6 — ADS Connection Manager
- Meerdere persistente ADS-profielen; instelbare AMS Net ID en ADS-poort; laatst gebruikte profiel.
- Beveiliging tegen profielwissel gedurende een actieve verbinding.

## v0.5 — Hoofdmenu en garagepoort
- Hoofdmenu voor oefeningen en garagepoortsimulator met eindeloopcontacten en motorcommando's.
- Voorbeeld ST-code voor docent.

## Eerdere wijzigingen
- Transportband met meerdere pakketten, sortering, reject-diverter en tweede afvoerband.
- ADS-diagnostiek, compatibiliteitsverbeteringen en offline demomodus.

Dit overzicht is een samengevoegde **samenvatting** van de historische updatebestanden. Technische testinstructies en oefenbestanden blijven apart behouden.

## v0.8.1 — Hotfix Custom Editor
- Fix SVG-componentlabels: `append()` returns undefined; create and label SVG text nodes before appending.

## v0.9 — Advanced 2D Custom Simulator (19 november 2026)

### Added
- Invoerbakken met vaste kleur, willekeurige kleur of herhalend CSV-kleurenpatroon; configureerbaar productie-interval en optionele BOOL-PLC-enable.
- Opvangbakken met instelbare capaciteit, realtime tellers, vol-signaal en knop om een opvangbak tijdens de simulatie leeg te maken.
- Meerdere transportbanden, rotatie in stappen van 90 graden, afstandsgebaseerde automatische verbindingen en transportoverdracht.
- Lichtsluizen naast de transportband met zichtbare straal over de band en pakketdetectie op basis van de positie langs de band.
- Automatische plaatsing/snapping van aanvoer, opvang, sensor en volgende band tijdens het slepen; optioneel raster van 10.
- Losse runtime-pakketten die automatisch worden geproduceerd/verzameld zonder het opgeslagen ontwerp te wijzigen.
- Botsingsafstand tussen pakketten, volgelopen opvangbakken en een begrensde pakketbuffer (250 runtime-pakketten).
- Kleur- en patrooninstellingen, counters en verbeterde configuratievelden in de editor.
- Vloeiendere pakketweergave met `requestAnimationFrame`; de simulatielus loopt onafhankelijk op 20 ms en ADS-uitwisseling op 50 ms.
- 15 nieuwe Python-regressietests (inclusief gesimuleerde ADS-test).

### Changed
- Basisproject gebruikt standaard één invoerbak, één transportband, één lichtsluis, één opvangbak, één knop en één lamp.
- Projectformaat blijft versie 1: bestaande opgeslagen v0.8-projecten blijven laadbaar; ontbrekende instellingen krijgen defaults.
- Nieuw optioneel JS API-commando `custom_empty_sink`.

### Limitations
- Auto-koppelingen worden momenteel afgeleid uit geometrische nabijheid; vrije visuele bedradingslijnen, diverters en complexe vertakkingen volgen later.
- Sensoren detecteren aanwezigheid; een afzonderlijke kleurensensor komt later.
- De grafische bediening en fysieke TwinCAT/UMRT-integratie zijn niet getest in Windows. Python- en JavaScript-syntax zijn wel gecontroleerd.
- Eerdere `UPDATE_*.md` bestanden worden niet automatisch uit een bestaande projectmap verwijderd door het ZIP-pakket. Gebruik voortaan alleen dit centrale bestand voor nieuwe wijzigingen.

