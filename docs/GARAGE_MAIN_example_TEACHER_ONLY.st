// TEACHER-ONLY example for MAIN implementation; do NOT ship solutions to students.
// First press opens, another press while travelling stops; next press opens again;
// at upper limit next press closes. Two motor directions are mutually exclusive.
// Requires: bGateWasPressed : BOOL := FALSE; declared in MAIN VAR.
nGateCycleCounter := nGateCycleCounter + UDINT#1;
IF bGateButton AND NOT bGateWasPressed THEN
    IF bGateMotorOpen OR bGateMotorClose THEN
        bGateMotorOpen := FALSE;
        bGateMotorClose := FALSE;
    ELSIF bGateLimitOpen THEN
        bGateMotorOpen := FALSE;
        bGateMotorClose := TRUE;
    ELSE
        bGateMotorClose := FALSE;
        bGateMotorOpen := TRUE;
    END_IF;
END_IF;
bGateWasPressed := bGateButton;
IF bGateLimitOpen THEN bGateMotorOpen := FALSE; END_IF;
IF bGateLimitClosed THEN bGateMotorClose := FALSE; END_IF;
IF bGateMotorOpen THEN bGateMotorClose := FALSE; END_IF;
