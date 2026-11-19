(* Voorbeeldprogramma voor demo/instructeur — niet de oplossing voor een studentopdracht. *)
PROGRAM MAIN
VAR
    bCustomButton : BOOL;  (* Input door simulator *)
    bCustomSensor : BOOL;  (* Input door simulator *)
    bCustomMotor : BOOL;   (* Output door PLC *)
    bCustomLamp : BOOL;    (* Output door PLC *)
    bLastButton : BOOL;
END_VAR

(* Puls op drukknop toggelt motor. Detectie doet lamp branden. *)
IF bCustomButton AND NOT bLastButton THEN
    bCustomMotor := NOT bCustomMotor;
END_IF;
bLastButton := bCustomButton;
bCustomLamp := bCustomSensor;
