// Voorbeeldoplossing voor de DOCENT / demo, GEEN oplossing afdwingen bij studenten.
// Dit is Structured Text voor het implementatiegedeelte van MAIN.
// Start/stop met houdfunctie: stop heeft prioriteit.
// Bij LS-01 onthouden we of het pakket naar de zijtak moet.
// Bij LS-02 resetten we de diverter voor het volgende pakket.
// De simulator biedt in fase 2 bewust slechts EEN actief pakket tegelijk.

nCycleCounter := nCycleCounter + UDINT#1;

IF bStopButton THEN
    bConveyorMotor := FALSE;
ELSIF bStartButton THEN
    bConveyorMotor := TRUE;
END_IF;

IF bSensorEntry THEN
    bDiverter := bRejectType;
ELSIF bSensorExit THEN
    bDiverter := FALSE;
END_IF;
