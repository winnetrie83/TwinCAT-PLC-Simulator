# PLC Simulation Lab — Home Screen v0.4

Deze update bouwt voort op **reject conveyor v0.3**.

## Installatie
1. Zorg dat je eerst de v0.3 reject-band hebt geïnstalleerd.
2. Maak een back-up van je projectmap.
3. Kopieer alleen de map `frontend` uit deze ZIP over de bestaande `frontend` (bestanden `index.html` en `app.js` vervangen; `home.css` toevoegen).
4. Start met je bestaande `start_live_compat.cmd` of `start_demo.cmd`.
5. Het startscherm toont drie kaarten. Alleen de transportband is actief.
6. Klik op **Open simulatie**. Vanuit de transportband ga je terug met **Alle simulaties**.

## Belangrijk
- **Geen wijzigingen** aan je `README.md`, `License.md`, `config/settings.json`, TwinCAT-code, ADS-bridge of `style.css`.
- De hoofdpagina is een laag binnen hetzelfde PyWebView-scherm, dus er is geen tweede browser of nieuwe verbinding nodig.
- Teruggaan naar het menu **stopt de PLC niet**. Druk STOP vóór je het scherm verlaat. Als de motor nog loopt, toont het menu een waarschuwing.
- Garagepoort en drukvat zijn zichtbare, bewust **uitgeschakelde** kaarten. Er is nog geen werkende simulator of externe API voor die modules.
- Voor een toekomstige docent-API stellen we een modulemanifest, validatie, vaste I/O-contracten en een gecontroleerde importworkflow voor. Laad zeker geen willekeurige Python/JS-code uit onbeveiligde bestanden.

## Versie
Gebaseerd op GitHub commit `c3d85c8` met de v0.3 reject-bandupdate erbovenop. Alleen de UI wordt gewijzigd.
