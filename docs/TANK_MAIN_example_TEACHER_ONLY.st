(* v1.0.1 reference: automatic 25%-80% cycles; DEMO defaults to hold mode. *)
(* TEACHER REFERENCE ONLY — do not hand to students with the exercise. *)
(* Paste declarations from twincat/TANK_MAIN_declarations.txt separately. *)

rStart(CLK := bTankStart);
IF bTankStop THEN
    bEnabled := FALSE;
ELSIF rStart.Q THEN
    bEnabled := NOT bEnabled;
END_IF;

IF bTankLevelLow THEN
    bFillPhase := TRUE;
ELSIF bTankLevelHigh OR bTankPressureHigh THEN
    bFillPhase := FALSE;
END_IF;

bPumpIn := bEnabled AND bFillPhase AND NOT bTankPressureHigh;
bPumpOut := bEnabled AND NOT bFillPhase;
