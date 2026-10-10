import os
import subprocess
import webbrowser
from pathlib import Path

HOME=Path.home()
SAFE_APPS={
    "calculator": ("Calculator", lambda: os.startfile("calc.exe") if os.name=="nt" else subprocess.Popen(["gnome-calculator"])),
    "notepad": ("Notepad", lambda: os.startfile("notepad.exe") if os.name=="nt" else subprocess.Popen(["gedit"])),
    "explorer": ("File Explorer", lambda: os.startfile(str(HOME)) if os.name=="nt" else subprocess.Popen(["xdg-open",str(HOME)])),
    "downloads": ("Downloads", lambda: os.startfile(str(HOME/"Downloads")) if os.name=="nt" else subprocess.Popen(["xdg-open",str(HOME/"Downloads")])),
    "documents": ("Documents", lambda: os.startfile(str(HOME/"Documents")) if os.name=="nt" else subprocess.Popen(["xdg-open",str(HOME/"Documents")])),
    "desktop": ("Desktop", lambda: os.startfile(str(HOME/"Desktop")) if os.name=="nt" else subprocess.Popen(["xdg-open",str(HOME/"Desktop")])),
    "browser": ("Web browser", lambda: webbrowser.open("https://www.google.com")),
}

def open_safe_app(app):
    key=(app or "").strip().lower()
    if key not in SAFE_APPS: return {"ok":False,"error":"Application/location is not in the safe allowlist."}
    label,fn=SAFE_APPS[key]
    try:
        fn(); return {"ok":True,"label":label}
    except Exception as exc:
        return {"ok":False,"error":f"{type(exc).__name__}: {exc}"}

def open_workspace_folder(name="VEXORA_Workspace"):
    target=HOME/"Desktop"/name
    try:
        target.mkdir(parents=True,exist_ok=True)
        if os.name=="nt": os.startfile(str(target))
        else: subprocess.Popen(["xdg-open",str(target)])
        return {"ok":True,"path":str(target)}
    except Exception as exc: return {"ok":False,"error":f"{type(exc).__name__}: {exc}"}
