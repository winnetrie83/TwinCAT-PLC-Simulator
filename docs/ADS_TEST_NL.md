# TwinCAT 2024 / 2026+ — eerste verbindingstest

Deze extra bestanden zijn geschikt om **bovenop fase 2 of fase 3** te plaatsen. Ze **overschrijven je README.md, disclaimer, bestaande settings.json, app.py en TwinCAT-code niet**.

## Wat doe je op de pc met TwinCAT 2024?

1. Start eerst je afzonderlijke **Usermode Runtime (UMRT)** met de methode die je normaal gebruikt (`start.bat` of TwinCAT-systeemvak). Laat die draaien.
2. Kijk in het UMRT-venster naar de regel **`AmsNetId:`**. Schrijf de zes getallen exact over. Gebruik niet automatisch `127.0.0.1.1.1`: dat is slechts een voorbeeld uit de oorspronkelijke simulatorconfiguratie.
3. Start TwinCAT XAE, selecteer **die UMRT als Target System**, activeer je configuratie, log in op de PLC en zet de PLC in **RUN**.
4. Controleer of de variabelen uit het project (`MAIN.bStartButton`, `MAIN.bConveyorMotor`, enz.) echt bestaan. Bij gebruik van de uitgebreide fase-3-oefening kies je de uitgebreide instellingenconfiguratie.
5. Dubbelklik op **`start_live_compat.cmd`** in de hoofdmap van de simulator.
6. Vul de AMS Net ID in die UMRT toont en controleer dat de ADS-poort overeenkomt met je PLC-runtime (meestal **851**).
7. De tool toont de runtime-status en test de geconfigureerde symbolen. Hierbij worden **geen PLC-waarden geschreven**.
8. Pas nadat alles slaagt, kan je de echte LIVE-simulator starten. De simulator schrijft dan uitsluitend zijn virtuele ingangssignalen; jouw PLC-programma stuurt de motor en diverter.

**Aparte diagnostiek, zonder de simulator te starten:**

```cmd
py -3 tools\twincat_compat.py --net-id 199.4.42.250.1.1 --port 851 --check-only
```

Vervang deze **voorbeeld-AMS Net ID** door de waarde die jouw UMRT werkelijk toont. Voor fase 3 met de extra sensor kan je een aangepaste configuratie meegeven:

```cmd
py -3 tools\twincat_compat.py --config config\settings.phase3-advanced.json
```

## Waar moet je op letten?

- **2024 versus 2026** is niet het belangrijkste verschil. De tool praat met de **PLC-runtime via ADS**, niet rechtstreeks met de editor.
- **UMRT** is een apart programma; afhankelijk van de TwinCAT-versie moet je het afzonderlijk starten. Ook een nieuwe installatie kan een aparte runtime gebruiken.
- De **AMS Net ID** van UMRT kan afwijken van de standaard TwinCAT Net ID. De simulator moet de Net ID van het *werkelijke target* gebruiken.
- De **ADS-poort 851** hoort doorgaans bij PLC-runtime 1 en is niet gelijk aan de ADS/TCP-poort 48898.
- Als de software geen PLC-symbolen vindt, betekent dat niet automatisch dat je ADS-verbinding mislukt is. Controleer de namen, types en of je PLC-programma gedownload is.

De installatie op jouw Windows/TwinCAT-combinatie is nog niet werkelijk getest. De meegeleverde unit tests gebruiken een gesimuleerde ADS-verbinding.
