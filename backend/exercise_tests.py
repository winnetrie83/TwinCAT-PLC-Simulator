"""Observable behavioural tests for PLC exercises, demo or a local educational runtime.

Only uses existing virtual pushbuttons/sensors and reads simulator snapshots.
Runs asynchronously so the desktop UI remains responsive. Never modifies PLC logic.
"""
from __future__ import annotations
import threading
import time

class ExerciseTestRunner:
    def __init__(self, services):
        self.services=services
        self.lock=threading.RLock()
        self.worker=None
        self.state={'running':False,'module':None,'results':[],'message':'Nog geen test uitgevoerd.'}

    def snapshot(self):
        with self.lock:
            return {'running':self.state['running'],'module':self.state['module'],
                    'results':[dict(x) for x in self.state['results']], 'message':self.state['message']}

    def start(self,module):
        if module not in self.services:
            raise ValueError('Geen testscenario voor deze simulatie.')
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise ValueError('Er is al een oefeningtest actief.')
            service=self.services[module]
            if not service.get_state()['connected']:
                raise ValueError('Verbind de oefening eerst met DEMO of TwinCAT ADS.')
            self.state={'running':True,'module':module,'results':[],
                        'message':'Test gestart. Tijdens de test worden virtuele drukknoppen bediend.'}
            self.worker=threading.Thread(target=self._run,args=(module,),daemon=True,name='exercise-test-'+module)
            self.worker.start()
            return self.snapshot()

    def _record(self,name,passed,details):
        with self.lock:
            self.state['results'].append({'name':name,'passed':bool(passed),'details':details})

    @staticmethod
    def _wait(predicate,timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if predicate():return True
            time.sleep(.05)
        return bool(predicate())

    def _run(self,module):
        svc=self.services[module]
        try:
            def state():
                s=svc.get_state()
                if not s['connected']:
                    raise RuntimeError('PLC-verbinding onderbroken tijdens test.')
                return s
            if module=='conveyor':
                svc.pulse('stop');time.sleep(.35)
                svc.pulse('start')
                started=self._wait(lambda:bool(state()['outputs'].get('motor')),3)
                self._record('START activeert de transportmotor',started,'PLC-motoruitgang wordt binnen 3 s TRUE.' if started else 'Motoruitgang niet geactiveerd.')
                svc.pulse('stop')
                stopped=self._wait(lambda:not bool(state()['outputs'].get('motor')),3)
                self._record('STOP schakelt de motor uit',stopped,'Motoruitgang wordt binnen 3 s FALSE.' if stopped else 'Motor blijft actief.')
            elif module=='garage':
                s=state(); pos=s.get('position',0)
                if pos>0.05:
                    self._record('Startpositie gesloten',False,'Begin met volledig gesloten poort om deze test uit te voeren.')
                else:
                    svc.press_button()
                    moving=self._wait(lambda:bool(state()['outputs'].get('motor_open')),3)
                    self._record('Druktoets opent de poort',moving,'Openmotor binnen 3 s actief.' if moving else 'Openmotor reageert niet.')
                    conflict=self._wait(lambda:bool(state().get('conflict')),1)
                    self._record('Geen tegengestelde motorcommando’s',not conflict,'Geen gelijktijdige open- en sluitmotor.' if not conflict else 'Motorconflict vastgesteld.')
                    if moving:
                        reached=self._wait(lambda:state().get('position',0)>=.999,7)
                        stopped=reached and self._wait(lambda:not state()['outputs'].get('motor_open'),2)
                        self._record('Open-eindschakelaar stopt motor',stopped,'Poort bereikt 100% en motor stopt.' if stopped else 'Poort bereikt eindstand niet of motor blijft actief.')
            elif module=='tank':
                s=state(); level=s['world']['level']
                if level>78:
                    self._record('Startniveau geschikt',False,'Verbreek en verbind opnieuw om de tank op 35% te resetten.')
                else:
                    if s['demo'] and s.get('demo_cycle'):
                        svc.set_demo_cycle(False)
                    svc.pulse('start')
                    filling=self._wait(lambda:bool(state()['signals'].get('pump_in')),3)
                    self._record('START activeert vulpomp',filling,'P1 wordt binnen 3 s actief.' if filling else 'Vulpomp start niet.')
                    if filling:
                        reached=self._wait(lambda:state()['world']['level']>=79.99,9)
                        stopped=reached and self._wait(lambda:not bool(state()['signals'].get('pump_in')),2)
                        self._record('Bovenniveau stopt P1',stopped,'Niveausensor op 80% stopt vulpomp.' if stopped else 'P1 stopt niet op de bovengrens.')
                    conflict=bool(state().get('pump_conflict'))
                    self._record('Geen gelijktijdige pompen',not conflict,'Pompen conflictvrij.' if not conflict else 'P1 en P2 gelijktijdig actief.')
        except Exception as exc:
            self._record('Testonderbreking',False,str(exc))
        finally:
            # Best-effort STOP. Never manually force any PLC output.
            try:
                if svc.get_state()['connected']:
                    if module=='conveyor':svc.pulse('stop')
                    elif module=='tank':svc.pulse('stop')
                    # Garage has no guaranteed stop-only command: do not toggle unknown PLC state.
            except Exception:
                pass
            with self.lock:
                self.state['running']=False
                passed=sum(x['passed'] for x in self.state['results'])
                self.state['message']=f'Test voltooid: {passed}/{len(self.state["results"])} controles geslaagd.'
