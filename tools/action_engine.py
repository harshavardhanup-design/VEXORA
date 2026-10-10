"""Permission-gated computer actions for VEXORA 3.5.

The engine is intentionally allowlisted. It never accepts an arbitrary shell command.
Callers should request approval before passing approved=True.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import os, subprocess, webbrowser, time, re
from core.logging_setup import get_logger

log = get_logger('actions')

@dataclass(frozen=True)
class ActionResult:
    ok: bool
    action: str
    message: str
    requires_confirmation: bool = False
    verified: bool = False
    details: dict | None = None

ALLOWED_APPS = {
    'calculator': ('Calculator', ['calc.exe']),
    'notepad': ('Notepad', ['notepad.exe']),
    'explorer': ('File Explorer', ['explorer.exe']),
}
# Modern Windows launches packaged apps via a short-lived stub, so the process
# we spawn is not the one that stays running. Verification must accept aliases.
PROCESS_ALIASES = {
    'calc.exe': {'calc.exe', 'calculatorapp.exe', 'calculator.exe', 'win32calc.exe'},
    'notepad.exe': {'notepad.exe'},
    'explorer.exe': {'explorer.exe'},
}
FOLDERS = {'desktop': Path.home()/'Desktop', 'documents': Path.home()/'Documents', 'downloads': Path.home()/'Downloads'}


def _launch(cmd):
    return subprocess.Popen(cmd, shell=False, close_fds=True)


def _process_seen(exe_name, pid=None, *, timeout=1.5, interval=0.1):
    """Poll for the launched process. A fixed 120 ms sleep produced false negatives."""
    try:
        import psutil
    except Exception:
        return False
    targets = PROCESS_ALIASES.get(exe_name.lower(), {exe_name.lower()})
    deadline = time.monotonic() + timeout
    while True:
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if (pid is not None and p.info.get('pid') == pid) or (p.info.get('name') or '').lower() in targets:
                    return True
            except Exception:
                continue
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def reverify(result: 'ActionResult') -> bool:
    """Re-check a previous launch WITHOUT launching again (used for recovery)."""
    if result.action in ALLOWED_APPS:
        return _process_seen(ALLOWED_APPS[result.action][1][0], (result.details or {}).get('pid'), timeout=1.0)
    if result.action in FOLDERS:
        return FOLDERS[result.action].exists()
    return bool(result.ok)


def execute(action: str, *, approved=False) -> ActionResult:
    action=(action or '').strip().lower()
    if action in ALLOWED_APPS:
        if not approved: return ActionResult(False,action,'Approval required before launching an application.',True)
        label,cmd=ALLOWED_APPS[action]
        try:
            proc=_launch(cmd)
            verified=_process_seen(cmd[0],getattr(proc,'pid',None))
            return ActionResult(True,action,f'{label} launch requested.',False,verified,{'label':label,'pid':getattr(proc,'pid',None)})
        except Exception as exc:
            log.warning('launch failed for %s: %s', action, exc)
            return ActionResult(False,action,f'Could not launch {label}: {type(exc).__name__}: {exc}')
    if action in FOLDERS:
        if not approved: return ActionResult(False,action,'Approval required before opening a folder.',True)
        path=FOLDERS[action]
        try:
            path.mkdir(parents=True,exist_ok=True)
            if os.name=='nt': os.startfile(str(path))
            else: webbrowser.open(path.as_uri())
            return ActionResult(True,action,f'Opened {path}.',False,path.exists(),{'path':str(path)})
        except Exception as exc: return ActionResult(False,action,f'Could not open {path}: {type(exc).__name__}: {exc}')
    if action=='browser':
        if not approved: return ActionResult(False,action,'Approval required before opening the browser.',True)
        try:
            ok=webbrowser.open('about:blank'); return ActionResult(bool(ok),action,'Default browser launch requested.' if ok else 'Browser launch was requested but could not be confirmed.',False,bool(ok))
        except Exception as exc: return ActionResult(False,action,f'Browser launch failed: {exc}')
    if action=='windows_settings':
        if not approved: return ActionResult(False,action,'Approval required before opening Windows Settings.',True)
        if os.name!='nt': return ActionResult(False,action,'Windows Settings is only available on Windows.')
        try:
            subprocess.Popen(['cmd.exe','/c','start','','ms-settings:'],shell=False); return ActionResult(True,action,'Windows Settings launch requested.',False,True)
        except Exception as exc: return ActionResult(False,action,f'Windows Settings failed: {exc}')
    return ActionResult(False,action,'Action is not in the VEXORA allowlist.')


def guarded_input(action,text,*,approved=False):
    if not approved: return ActionResult(False,action,'Input automation requires explicit approval.',True)
    try: import pyautogui
    except Exception: return ActionResult(False,action,'Input automation is unavailable; install pyautogui support.')
    if action=='type_text':
        value=str(text)
        if len(value)>2000: return ActionResult(False,action,'Input exceeds the 2000-character safety limit.')
        pyautogui.write(value,interval=0.005); return ActionResult(True,action,'Text input completed.',False,True,{'characters':len(value)})
    if action=='press_key':
        key=str(text).lower(); safe={'enter','esc','escape','tab','space','backspace','up','down','left','right','home','end'}
        if key not in safe: return ActionResult(False,action,'Key is not in the safe input allowlist.')
        pyautogui.press('esc' if key=='escape' else key); return ActionResult(True,action,f'Pressed {key}.',False,True)
    if action=='hotkey':
        combo='+'.join(x.strip().lower() for x in str(text).split('+') if x.strip())
        safe_combos={'ctrl+c','ctrl+v','ctrl+x','ctrl+a','ctrl+l','ctrl+f','alt+tab','win+d'}  # alt+f4 removed: closes the focused window (destructive)
        if combo not in safe_combos: return ActionResult(False,action,'Hotkey is not in the safe combination allowlist.')
        pyautogui.hotkey(*combo.split('+')); return ActionResult(True,action,f'Pressed {combo}.',False,True)
    if action=='click':
        try: x,y=(int(v.strip()) for v in str(text).split(',',1))
        except Exception: return ActionResult(False,action,'Click coordinates must be provided as x,y.')
        if x<0 or y<0 or x>20000 or y>20000: return ActionResult(False,action,'Click coordinates exceed the safety bounds.')
        pyautogui.click(x=x,y=y); return ActionResult(True,action,f'Clicked ({x},{y}).',False,True,{'x':x,'y':y})
    return ActionResult(False,action,'Unknown input action.')


_OPEN_VERB = re.compile(r'\b(?:open(?:ing)?|launch(?:ing)?|start(?:ing)?)\b')
_TARGETS = (
    (re.compile(r'\b(?:calculator|calc)\b'), 'calculator'),
    (re.compile(r'\bnotepad\b'), 'notepad'),
    (re.compile(r'\b(?:file\s+)?explorer\b'), 'explorer'),
    (re.compile(r'\bdownloads?\b'), 'downloads'),
    (re.compile(r'\bdocuments?\b'), 'documents'),
    (re.compile(r'\bdesktop\b'), 'desktop'),
    (re.compile(r'\b(?:web\s+)?browser\b'), 'browser'),
    (re.compile(r'\b(?:windows\s+)?settings\b'), 'windows_settings'),
)


def plan_for_goal(goal: str) -> list[dict]:
    """Map a natural-language goal to allowlisted actions, in the order mentioned.

    Requires an explicit open/launch/start verb, and understands lists such as
    "open calculator and notepad" or "opening notepad, then downloads".
    """
    q = ' '.join((goal or '').lower().split())
    if not _OPEN_VERB.search(q):
        return []
    hits = []
    for pattern, action in _TARGETS:
        m = pattern.search(q)
        if m:
            hits.append((m.start(), action))
    out = []
    for _, action in sorted(hits):
        if action not in [x['action'] for x in out]:
            out.append({'action': action, 'risk': 'low', 'confirmation': True})
    return out


def action_schema():
    return {'apps':sorted(ALLOWED_APPS),'folders':sorted(FOLDERS),'system':['browser','windows_settings'],'input':['type_text','press_key','hotkey','click']}
