from pathlib import Path
from datetime import datetime
import os

def vision_status(): return {'screenshot':True}
def capture_screen():
    out=Path.home()/"Pictures"/"VEXORA"; out.mkdir(parents=True,exist_ok=True)
    path=out/f"screen_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        from core.qt_compat import QGuiApplication
        pix=QGuiApplication.primaryScreen().grabWindow(0); pix.save(str(path))
        return {'ok':True,'path':str(path)}
    except Exception as e: return {'ok':False,'error':str(e)}
