"""Dependency-free visualization data for VEXORA dashboards."""
from dataclasses import dataclass, asdict
from time import monotonic

@dataclass(frozen=True)
class Stage:
    name:str
    state:str
    progress:int

STAGES=('SEE','THINK','ACT','VERIFY','RECOVER')

def agent_stage_data(active='IDLE'):
    a=str(active or 'IDLE').upper()
    mapping={'OBSERVE':'SEE','UNDERSTAND':'THINK','PLAN':'THINK','ASK_PERMISSION':'THINK','ACT':'ACT','VERIFY':'VERIFY','RECOVER':'RECOVER','COMPLETE':'VERIFY','FAILED':'RECOVER'}
    current=mapping.get(a,'SEE' if a!='IDLE' else 'THINK')
    idx=STAGES.index(current) if current in STAGES else 0
    return [Stage(name, 'active' if i==idx else ('done' if i<idx else 'idle'), int(100 if i<idx else 55 if i==idx else 0)) for i,name in enumerate(STAGES)]

def workload_profile(tasks, recent_count=0, active_requests=0):
    total=max(0,len(tasks or [])); done=sum(1 for t in (tasks or []) if t.get('done'))
    pending=max(0,total-done)
    return {'tasks_total':total,'tasks_done':done,'tasks_pending':pending,'recent_items':max(0,int(recent_count)),'active_requests':max(0,int(active_requests)),'completion_percent':round(done/total*100,1) if total else 0.0}

def snapshot_payload(cpu=0,ram=0,disk=0,tasks=0):
    return {'cpu':max(0,min(100,round(float(cpu),1))),'ram':max(0,min(100,round(float(ram),1))),'disk':max(0,min(100,round(float(disk),1))),'tasks':max(0,int(tasks))}
