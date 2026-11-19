# PLC Simulation Lab — v0.6: verbindingsprofielen

Deze update is **bedoeld voor de installatie waarop je v0.5 al hebt gezet** (transportband + garagepoort). Kopieer de inhoud van de ZIP-map `PLC_Simulation_Lab_v0.6_Update` naar de **hoofdmap** van het bestaande project. Maak eerst een back-up.

## Wat is nieuw?

- Een uitklaplijst **Verbindingsprofiel** op het startscherm, de transportband en de garagepoort.
- **Edit** voor nieuwe, bestaande en te verwijderen profielen.
- Per profiel: **naam**, **AMS Net ID** en **PLC ADS-poort**.
- Het laatst geselecteerde profiel wordt automatisch gebruikt na het opnieuw starten.
- Je kunt tussen profielen wisselen, **nadat de actieve verbinding verbroken is**. Er wordt nooit tijdens een lopende ADS-sessie geruisloos naar een andere runtime overgeschakeld.
- De transportband en garagepoort gebruiken dezelfde geselecteerde verbindingsinstellingen, maar hun PLC-symbolen blijven verschillend.

## Installatie

1. Stop de simulator en maak een back-up van je projectmap.
2. Kopieer uit deze ZIP de bestanden `app.py`, `backend/profiles.py`, `frontend/index.html`, `frontend/app.js`, `frontend/connection-profiles.css` naar dezelfde relatieve paden in je bestaande project.
3. Voeg `tests/test_connection_profiles.py` en dit document toe als je de tests/documentatie wenst.
4. **Laat `config/settings.json`, `README.md`, `License.md`, je TwinCAT-programma en de andere bestaande bestanden onaangeroerd.**
5. Start met `start_live.cmd` of `start_demo.cmd`, kies een profiel en druk op Verbinden.

## Eerste opstart en opslaglocatie

Bij de eerste start maakt de applicatie één profiel `Standaard` aan uit je bestaande `config/settings.json` (AMS Net ID en ADS-poort). Daarmee gaan bestaande werkende waarden niet verloren. Daarna staan de profielen in:

`%LOCALAPPDATA%\PLC-Simulation-Lab\connections.json`

Bij opeenvolgende starts wordt deze profielenlijst gebruikt en overschrijft die **alleen het gekozen ADS-doel**; de bestaande `settings.json` blijft de bron voor pulsduur en transportband-PLC-symbolen.

Zo blijft de lijst ook behouden na een update van de projectmap. Verwijder `connections.json` niet als je je profielen wilt bewaren. Je kunt hiervan een back-up maken.

## Starten

- **Aanbevolen:** `start_live.cmd`. Hiermee opent het programma meteen en kun je het gewenste profiel via de interface kiezen.
- `start_demo.cmd`: zelfde profielinterface, maar zonder echte TwinCAT-besturing.
- **Let op met `start_live_compat.cmd`:** deze oudere launcher vraagt zelf een AMS Net ID, maar de applicatie heeft vanaf nu haar eigen opgeslagen profielen. De in de compat-launcher gekozen waarde kan daarom afwijken van de waarde die de GUI uit de profielen kiest. Gebruik bij voorkeur `start_live.cmd`. De oudere compatibiliteitscontrole is nog niet in de GUI geïntegreerd.

## Veilig wisselen

1. Stop bij een actieve machine eerst de beweging via de PLC en druk daarna op **Verbreken**.
2. Kies een andere verbinding in de uitklaplijst.
3. Druk op **Verbinden**. Het nieuwe profiel is ook meteen het laatst gebruikte.

De simulator stuurt bij het wisselen **geen STOP naar een fysieke PLC**. Gebruik de app uitsluitend met virtuele onderwijsinstallaties. Een profiel wijzigen tijdens een actieve verbinding wordt geweigerd.

## Tests

Vanaf de projecthoofdmap:

```cmd
py -3 -m unittest discover -s tests -p test_connection_profiles.py -v
```

De tests controleren het bewaren/herladen van profielen, wijzigen/verwijderen en invoervalidatie. De echte GUI en ADS-verbinding moeten op de Windows/TwinCAT-computer worden getest.
