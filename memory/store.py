import json, os, threading, time, tempfile
from pathlib import Path
from core.logging_setup import get_logger

log = get_logger('store')
APP_DIR = Path(os.getenv('APPDATA') or Path.home()) / 'VEXORA'
STORE = APP_DIR / 'workspace.json'
_lock = threading.RLock()
def _default():
    return {'tasks': [], 'memory': [], 'settings': {'assistant_name':'VEXORA','model_provider':'offline','model_name':'llama3.2','ollama_host':'http://127.0.0.1:11434','fast_replies':True,'animations':True,'auto_scroll':True,'local_only':True,'focus_mode':False,'online_knowledge':True,'use_local_model':True,'everyday_mode':True,'require_action_confirmation':True,'ocr_enabled':False,'screen_context':True,'gemini_api_key':'','openai_api_key':'','feedback_enabled':True,'reduce_motion':False,'start_page':'Overview'}, 'updated_at': time.time()}
def _normalize(data):
    base=_default()
    if not isinstance(data, dict):
        return base
    base.update({k:v for k,v in data.items() if k in {'tasks','memory','settings','updated_at'}})
    base['tasks']=data.get('tasks') if isinstance(data.get('tasks'),list) else []
    base['memory']=data.get('memory') if isinstance(data.get('memory'),list) else []
    base['settings']={**_default()['settings'], **(data.get('settings') if isinstance(data.get('settings'),dict) else {})}
    return base

def _quarantine():
    """Keep an unreadable workspace file instead of letting the next save overwrite it."""
    try:
        dest = STORE.with_name(f'workspace.corrupt-{int(time.time())}.json')
        os.replace(STORE, dest)
        log.error('workspace.json was unreadable; preserved as %s', dest.name)
    except OSError as exc:
        log.error('could not quarantine corrupt workspace: %s', exc)

def load():
    with _lock:
        if STORE.exists():
            try:
                return _normalize(json.loads(STORE.read_text(encoding='utf-8')))
            except (OSError, ValueError) as exc:
                log.error('failed to read workspace: %s', exc)
                _quarantine()
        return _default()
def save(data):
    with _lock:
        APP_DIR.mkdir(parents=True,exist_ok=True)
        payload=_normalize(dict(data)); payload['updated_at']=time.time()
        fd,tmp=tempfile.mkstemp(prefix='workspace_',suffix='.tmp',dir=str(APP_DIR))
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as fh:
                json.dump(payload,fh,ensure_ascii=False,indent=2)
                fh.flush(); os.fsync(fh.fileno())
            os.replace(tmp,STORE)
        finally:
            try:
                if os.path.exists(tmp): os.remove(tmp)
            except OSError:
                pass
def update_tasks(tasks): d=load(); d['tasks']=tasks; save(d)
def update_settings(settings): d=load(); d['settings']=dict(settings); save(d)
def remember(user,assistant):
    d=load(); d['memory']=(d.get('memory') or [])[-19:]+[{'user':user,'assistant':assistant,'time':time.time()}]; save(d)
