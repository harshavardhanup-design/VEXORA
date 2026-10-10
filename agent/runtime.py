"""VEXORA 3.8 closed-loop agent runtime.

Deterministic state machine for inspectable SEE -> THINK -> ACT -> VERIFY ->
RECOVER workflows. It never bypasses the action engine's approval gate.
"""
from dataclasses import dataclass, field, asdict, replace
from enum import Enum
import time
from agent.planner import plan
from tools.action_engine import execute, reverify
from tools.see_engine import active_window

class AgentState(str, Enum):
    IDLE='IDLE'; UNDERSTAND='UNDERSTAND'; PLAN='PLAN'; ASK_PERMISSION='ASK_PERMISSION'; ACT='ACT'; OBSERVE='OBSERVE'; VERIFY='VERIFY'; RECOVER='RECOVER'; COMPLETE='COMPLETE'; FAILED='FAILED'

@dataclass
class RuntimeEvent:
    state:str
    message:str
    timestamp:float=field(default_factory=time.time)
    data:dict=field(default_factory=dict)

@dataclass
class RuntimeResult:
    goal:str
    state:str
    completed:int
    total:int
    events:list
    results:list
    recovery_count:int=0
    def as_dict(self): return {'goal':self.goal,'state':self.state,'completed':self.completed,'total':self.total,'events':[asdict(e) for e in self.events],'results':self.results,'recovery_count':self.recovery_count}

class AgentRuntime:
    def __init__(self, max_retries=1):
        self.max_retries=max(0,int(max_retries)); self.state=AgentState.IDLE; self.events=[]; self.recovery_count=0
    def _emit(self,state,message,**data):
        self.state=state; self.events.append(RuntimeEvent(state.value,message,data=data))
    def inspect(self):
        w=active_window(); self._emit(AgentState.OBSERVE,'Observed active computer context.',title=w.get('title'),process=w.get('process')); return w
    def prepare(self,goal):
        self._emit(AgentState.UNDERSTAND,'Interpreting goal.',goal=goal)
        p=plan(goal); self._emit(AgentState.PLAN,'Built protected action plan.',steps=len(p.steps)); return p
    def run(self,goal,approved=False, executor=execute, verifier=reverify):
        self.events=[]; self.recovery_count=0; p=self.prepare(goal); results=[]
        if not p.steps:
            self._emit(AgentState.FAILED,'No safe registered action matched the goal.'); return RuntimeResult(goal,self.state.value,0,0,self.events,results,0)
        if not approved:
            self._emit(AgentState.ASK_PERMISSION,'Protected actions require explicit approval.',steps=len(p.steps)); return RuntimeResult(goal,self.state.value,0,len(p.steps),self.events,results,0)
        for idx,step in enumerate(p.steps):
            self._emit(AgentState.ACT,f'Executing step {idx+1} of {len(p.steps)}.',action=step.action)
            attempt=0
            r=executor(step.action,approved=True)   # executed exactly once: launches are not idempotent
            while True:
                payload=asdict(r); results.append(payload)
                self._emit(AgentState.OBSERVE,'Re-observed after action.',action=step.action,verified=r.verified)
                if r.ok and r.verified:
                    self._emit(AgentState.VERIFY,'Action verified.',action=step.action); break
                if not r.ok or attempt>=self.max_retries:
                    self._emit(AgentState.FAILED,'Action could not be verified.',action=step.action); return RuntimeResult(goal,self.state.value,idx,len(p.steps),self.events,results,self.recovery_count)
                attempt+=1; self.recovery_count+=1; self._emit(AgentState.RECOVER,'Verification failed; re-checking without repeating the action.',action=step.action,attempt=attempt)
                # Recovery re-verifies; it never relaunches (a retry used to open a duplicate window).
                r=replace(r,verified=bool(verifier(r)))
        self._emit(AgentState.COMPLETE,'All planned actions completed and verified.',steps=len(p.steps)); return RuntimeResult(goal,self.state.value,len(p.steps),len(p.steps),self.events,results,self.recovery_count)
