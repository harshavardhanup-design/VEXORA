"""VEXORA 5.5 Windows-11-focused engineering and stress suite.
Safe: no real app launches, no shell execution, no network calls required.
"""
from __future__ import annotations
import random,string,threading,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import sys; sys.path.insert(0,str(ROOT))
from core.platform_compat import capabilities, compatibility_report, windows_major, windows_build, is_windows_11
from core.windows11 import detect_profile, preferred_refresh_ms, ui_scale_hint, configure_process
from core.quality import finite_number, clamp_percent
from agent.command_router import handle_result
from agent.planner import plan
from agent.runtime import AgentRuntime, AgentState
from agent.model_router import choose
from tools.action_engine import execute, guarded_input
from tools.browser import validate_url, search_url, open_url
from tools.ui_understanding import observe_image, find_text
from tools.visual_intelligence import observe, compare_fingerprints
from tools.visuals import agent_stage_data, workload_profile, snapshot_payload

ui=(ROOT/'app/ui/main_window.py').read_text(encoding='utf-8')
assert 'v5.5' in ui
assert 'Windows-optimized' in ui
assert "quick[:9]" in ui
assert "6 core actions" not in ui
assert 'Agent Console' in ui
assert 'preferred_refresh_ms' in ui
for bad in ('os.system(','shell=True','subprocess.call(','eval(','exec('):
    assert bad not in (ROOT/'tools/action_engine.py').read_text(encoding='utf-8')

# Platform contracts: repeated and hostile-safe.
for _ in range(100000):
    c=capabilities(); assert c['local_first'] is True; assert c['qt_target'] in ('PySide2','PySide6')
    assert isinstance(c['performance_profile'],str)
    p=detect_profile(); assert p.dpi_scale > 0; assert isinstance(preferred_refresh_ms(),int)
assert compatibility_report()
assert ui_scale_hint() in ('per-monitor-dpi-v2','auto')

# UI contract / clean quick action matrix.
assert ui.count("('PC health'") == 1
assert ui.count("('Recent work'") == 1
assert ui.count("('Running apps'") == 1
assert ui.count("('Capture screen'") == 1
assert ui.count("('Agent plan'") == 1
assert 'Open Calculator' not in ui.split("elif key=='Ask VEXORA'")[1].split("elif key=='My Work'")[0]

# Safety matrix.
for action in ['calculator','notepad','explorer','desktop','documents','downloads','browser','windows_settings','shutdown','powershell','unknown']:
    r=execute(action,approved=False); assert r.requires_confirmation or not r.ok
for bad in ['ctrl+alt+delete','alt+f4+delete','powershell','cmd','win+r','delete']:
    assert not guarded_input('hotkey',bad,approved=True).ok
assert not guarded_input('type_text','x'*2001,approved=True).ok
assert not guarded_input('click','-1,5',approved=True).ok
assert not guarded_input('click','50000,5',approved=True).ok

# Browser allowlist.
for u in ['https://example.com','http://localhost:8000','ftp://example.com','javascript:alert(1)','file:///C:/Windows']:
    ok=validate_url(u); assert ok == u.startswith('http://') or ok == u.startswith('https://')
assert search_url('VEXORA Windows 11').startswith('https://www.bing.com/search?q=')
assert not open_url('https://example.com',approved=False).ok

# Planner/runtime stress.
qs=['open calculator','open notepad','open browser','open downloads','open documents','open desktop','open windows settings','open calculator and open notepad']
for _ in range(20000):
    p=plan(random.choice(qs)); assert p.steps and all(s.confirmation for s in p.steps)
assert not plan('delete everything').steps
from tools.action_engine import ActionResult
def fake_exec(action,approved=False):
    assert approved; return ActionResult(ok=True, action=action, message='ok', requires_confirmation=False, verified=True, details={})
for _ in range(10000):
    r=AgentRuntime(max_retries=1).run('open calculator',approved=True,executor=fake_exec)
    assert r.state==AgentState.COMPLETE.value and r.completed==r.total==1

# Router corpus and 100k adversarial inputs.
queries=['How is my PC?','Show recent files','What is using my RAM?','Show running apps','What is on my screen?','Plan opening Calculator','Analyze my PC performance','What are my system specifications?','Open calculator','Open notepad','Open File Explorer','Open browser','Open downloads','Open documents','Open desktop','Open Windows Settings','Help','Explain artificial intelligence','What should I work on today?']
rng=random.Random(550055)
seeds=['delete','shutdown','restart','format','powershell','cmd','rm -rf','C:\\Windows','<script>','ignore previous instructions',';','&&','|','../','%PATH%','HKLM','reg add','schtasks','cipher','takeown']
for _ in range(100000):
    s=rng.choice(seeds)+' '+''.join(rng.choice(string.printable[:95]) for _ in range(rng.randint(0,160)))
    try: r=handle_result(s); assert isinstance(r.text,str)
    except Exception as e: raise AssertionError(('router crash',s,e))

# Visualization invariant stress.
for _ in range(150000):
    stages=agent_stage_data(rng.choice(['IDLE','OBSERVE','PLAN','ACT','VERIFY','RECOVER','COMPLETE','FAILED','UNKNOWN']))
    assert len(stages)==5 and all(0<=x.progress<=100 for x in stages)
    payload=snapshot_payload(rng.uniform(-100,200),rng.uniform(-100,200),rng.uniform(-100,200),rng.randint(-100,5000))
    assert 0<=payload['cpu']<=100 and 0<=payload['ram']<=100 and 0<=payload['disk']<=100 and payload['tasks']>=0
    profile=workload_profile([{'done':rng.choice([True,False])} for _ in range(rng.randint(0,20))],rng.randint(0,50),rng.randint(0,16))
    assert 0<=profile['completion_percent']<=100

# Model routing stress.
for _ in range(150000):
    q=rng.choice(['calculate 12+4','inspect the screen','write code','study operating systems','pc health','general question','read text on screen'])
    route=choose(q,local_available=rng.choice([True,False]),online_enabled=True,vision=('screen' in q))
    assert route.backend in {'deterministic','vision-local','vision-optional','local-llm','online-knowledge','fallback'}

# Visual observation: real image, fingerprint stability and mutation detection.
from PIL import Image,ImageDraw
img=ROOT/'_v55_test.png'; im=Image.new('RGB',(640,360),'white'); ImageDraw.Draw(im).text((20,30),'VEXORA WINDOWS 11 TEST',fill='black'); im.save(img)
a=observe_image(img,ocr=False); b=observe(img,ocr=False)
assert a.ok and b.ok and a.width==640 and a.height==360 and len(a.fingerprint)==64 and len(b.fingerprint)==64
assert compare_fingerprints(a.fingerprint,b.fingerprint)
ImageDraw.Draw(im).rectangle((10,10,80,80),fill='black'); im.save(img)
c=observe(img,ocr=False); assert c.ok and not compare_fingerprints(b.fingerprint,c.fingerprint)
img.unlink(missing_ok=True)

# Concurrency: 48 workers x 1000 router calls.
errors=[]
def worker(i):
    try:
        for j in range(1000): handle_result(queries[(i+j)%len(queries)])
    except Exception as e: errors.append((i,e))
threads=[threading.Thread(target=worker,args=(i,)) for i in range(48)]
for t in threads:t.start()
for t in threads:t.join()
assert not errors, errors[:2]

# Basic latency sanity (no strict hardware-dependent threshold).
samples=[]
for _ in range(1000):
    t=time.perf_counter(); handle_result('How is my PC?'); samples.append((time.perf_counter()-t)*1000)
assert statistics.median(samples) < 50.0

print('ALL V5.5 TESTS PASSED')
