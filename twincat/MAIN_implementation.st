// DOCENTENVOORBEELD: niet meeleveren aan studenten als oefenoplossing.
// Werkende basislogica uit fase 2, ongewijzigd in werking.
// LS-03 is een nieuwe sensorinput, nog niet nodig voor de basisbesturing.
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
