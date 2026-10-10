"""Deterministic, inspectable planner for protected VEXORA workflows."""
from dataclasses import dataclass, asdict
from tools.action_engine import plan_for_goal

@dataclass
class PlanStep:
    action:str; risk:str='low'; confirmation:bool=True; status:str='pending'

@dataclass
class AgentPlan:
    goal:str; steps:list; rationale:str=''; status:str='planned'
    def as_dict(self): return {'goal':self.goal,'steps':[asdict(s) for s in self.steps],'rationale':self.rationale,'status':self.status}


def plan(goal):
    raw=plan_for_goal(goal)
    steps=[PlanStep(x['action'],x.get('risk','low'),bool(x.get('confirmation',True))) for x in raw]
    rationale=('Ordered allowlisted plan with protected actions.' if steps else 'No safe registered action matched this goal.')
    return AgentPlan(str(goal or ''),steps,rationale)
