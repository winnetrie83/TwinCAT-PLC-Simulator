// Alleen in het implementatiegedeelte van MAIN plakken.
// Demonstratie: motor houdt zichzelf vast na een START-puls.
// STOP of sensor heeft altijd voorrang op START.

nCycleCounter := nCycleCounter + UDINT#1;

IF bStopButton OR bSensor THEN
    bMotor := FALSE;
ELSIF bStartButton THEN
    bMotor := TRUE;
END_IF;
