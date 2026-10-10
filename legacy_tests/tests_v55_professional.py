"""VEXORA v5.5 Professional rebuild validation.
Focus: selected v3.5 workflow restoration, clean UI contracts, reliability,
concurrency, persistence safety, and high-load behavior. No real app launches.
"""
from __future__ import annotations
import os, sys, random, string, tempfile, threading, time, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

from agent.command_router import handle_result
from agent.planner import plan
from agent.runtime import AgentRuntime, AgentState
from tools.action_engine import execute, guarded_input, ActionResult
from tools.visuals import agent_stage_data, workload_profile, snapshot_payload
from core.platform_compat import capabilities
from core.windows11 import detect_profile, preferred_refresh_ms, ui_scale_hint
from memory import store

ui=(ROOT/'app/ui/main_window.py').read_text(encoding='utf-8')
readme=(ROOT/'README.md').read_text(encoding='utf-8')

# 1. Product/UI contracts.
assert 'v5.5 Professional' in ui
assert 'Workspace shortcuts' in ui or 'WORKSPACE SHORTCUTS' in ui
assert "('Downloads','Open Downloads')" in ui
assert "('Documents','Open Documents')" in ui
assert "('Workday setup','Prepare my workspace')" in ui
assert "quick[:9]" in ui
assert 'Open Calculator' not in ui.split("elif key=='Ask VEXORA'")[1].split("elif key=='My Work'")[0]
assert 'QGraphicsOpacityEffect' not in ui
assert 'self._transition_timer=QTimer(self)' in ui
assert 'if key not in self.sessions: return self._feature_command(text)' in ui
assert 'Windows 11' in readme

# 2. Feature-row geometry contract: bounded grid, max 4 columns.
assert 'columns=4 if len(items)<=4 else 3' in ui
assert 'setMinimumHeight(96)' in ui

# 3. Persistence reliability: same-directory atomic write + malformed-data normalization.
with tempfile.TemporaryDirectory() as td:
    old_dir, old_store = store.APP_DIR, store.STORE
    store.APP_DIR=Path(td); store.STORE=Path(td)/'workspace.json'
    try:
        store.save({'tasks':[{'title':'Professional test','done':False}], 'memory':[], 'settings':{'assistant_name':'VEXORA'}})
        d=store.load(); assert d['tasks'][0]['title']=='Professional test'
        store.STORE.write_text('{bad json',encoding='utf-8')
        d=store.load(); assert d['tasks']==[] and isinstance(d['settings'],dict)
        store.save({'tasks':'invalid','memory':{'bad':'shape'},'settings':'invalid'})
        d=store.load(); assert d['tasks']==[] and d['memory']==[] and isinstance(d['settings'],dict)
        errors=[]
        def persist_worker(i):
            try:
                store.save({'tasks':[{'title':f'T{i}','done':False}], 'memory':[], 'settings':{'assistant_name':'VEXORA'}})
            except Exception as e:
                errors.append(e)
        threads=[threading.Thread(target=persist_worker,args=(i,)) for i in range(16)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors and store.load()['tasks']
    finally:
        store.APP_DIR, store.STORE = old_dir, old_store

# 4. Windows11/platform contracts under repeated load.
for _ in range(20000):
    c=capabilities(); assert c['local_first'] is True
    p=detect_profile(); assert p.dpi_scale>0
    assert preferred_refresh_ms() >= 1000
    assert ui_scale_hint() in ('per-monitor-dpi-v2','auto')

# 5. Restored v3.5 workflow routes.
for q in ['open downloads','open documents','prepare my workspace','create workspace folder','what should i work on today?','show recent files','help me plan my work']:
    r=handle_result(q); assert isinstance(r.text,str)

# 6. Safety invariants.
for action in ['calculator','notepad','explorer','desktop','documents','downloads','browser','windows_settings','shutdown','powershell','unknown']:
    r=execute(action,approved=False); assert r.requires_confirmation or not r.ok
for combo in ['ctrl+alt+delete','win+r','cmd+q','powershell','delete','alt+f4+delete']:
    assert not guarded_input('hotkey',combo,approved=True).ok
assert not guarded_input('type_text','x'*5000,approved=True).ok

# 7. Planner/runtime workload.
qs=['open calculator','open notepad','open browser','open downloads','open documents','open desktop','open windows settings']
for _ in range(30000):
    p=plan(random.choice(qs)); assert p.steps and all(s.confirmation for s in p.steps)

def fake_exec(action,approved=False):
    assert approved
    return ActionResult(ok=True,action=action,message='ok',requires_confirmation=False,verified=True,details={})
for _ in range(15000):
    r=AgentRuntime(max_retries=2).run('open calculator',approved=True,executor=fake_exec)
    assert r.state==AgentState.COMPLETE.value

# 8. Adversarial router load.
rng=random.Random(55005599)
seeds=['delete','shutdown','restart','format','powershell','cmd','rm -rf','C:\\Windows','<script>','ignore previous instructions','&&','|','../','reg add','schtasks','takeown']
for _ in range(50000):
    q=rng.choice(seeds)+' '+''.join(rng.choice(string.printable[:95]) for _ in range(rng.randint(0,140)))
    out=handle_result(q); assert isinstance(out.text,str)

# 9. Visualization invariants.
for _ in range(75000):
    stages=agent_stage_data(rng.choice(['IDLE','OBSERVE','PLAN','ACT','VERIFY','RECOVER','COMPLETE','FAILED','UNKNOWN']))
    assert len(stages)==5 and all(0<=x.progress<=100 for x in stages)
    payload=snapshot_payload(rng.uniform(-100,200),rng.uniform(-100,200),rng.uniform(-100,200),rng.randint(-100,5000))
    assert 0<=payload['cpu']<=100 and 0<=payload['ram']<=100 and 0<=payload['disk']<=100 and payload['tasks']>=0
    w=workload_profile([{'done':rng.choice([True,False])} for _ in range(rng.randint(0,25))],rng.randint(0,50),rng.randint(0,20))
    assert 0<=w['completion_percent']<=100

# 10. Concurrency stress.
queries=['How is my PC?','Show recent files','Show running apps','What is on my screen?','Plan opening Calculator','Explain AI','What should I work on today?','Open downloads','Open documents']
errors=[]
def worker(i):
    try:
        for j in range(1000):
            r=handle_result(queries[(i+j)%len(queries)])
            assert isinstance(r.text,str)
    except Exception as e:
        errors.append((i,e))
threads=[threading.Thread(target=worker,args=(i,)) for i in range(32)]
for t in threads:t.start()
for t in threads:t.join()
assert not errors, errors[:3]

# 11. Latency sanity over 5000 operations.
samples=[]
for _ in range(5000):
    t=time.perf_counter(); handle_result('How is my PC?'); samples.append((time.perf_counter()-t)*1000)
assert statistics.median(samples)<50.0

print('ALL V5.5 PROFESSIONAL TESTS PASSED')
