from pathlib import Path
from datetime import datetime
import json, os, threading

_LOCK=threading.RLock()
PATH=Path(os.getenv('APPDATA') or Path.home())/'VEXORA'/'action_audit.jsonl'

def record(event, **details):
    row={'time':datetime.now().isoformat(timespec='seconds'),'event':event,**details}
    with _LOCK:
        PATH.parent.mkdir(parents=True,exist_ok=True)
        with PATH.open('a',encoding='utf-8') as f: f.write(json.dumps(row,ensure_ascii=False)+'\n')
    return row
