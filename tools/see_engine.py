"""VEXORA 3.0 SEE engine: active window, screen capture, OCR and screen fingerprinting.
OCR is optional and fails closed when its backend is unavailable.
"""
from pathlib import Path
from datetime import datetime
import os, platform, hashlib, time


def _active_window_windows():
    if os.name != 'nt': return None
    try:
        import ctypes
        user32=ctypes.windll.user32; hwnd=user32.GetForegroundWindow()
        if not hwnd: return None
        length=user32.GetWindowTextLengthW(hwnd); buf=ctypes.create_unicode_buffer(length+1)
        user32.GetWindowTextW(hwnd,buf,length+1); pid=ctypes.c_ulong(); user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        return {'hwnd':int(hwnd),'title':buf.value.strip() or 'Untitled window','pid':int(pid.value)}
    except Exception: return None


def active_window():
    info=_active_window_windows()
    if info:
        try:
            import psutil; p=psutil.Process(info['pid']); info['process']=p.name(); info['exe']=p.exe()
        except Exception: info.update({'process':'Unavailable','exe':'Unavailable'})
        return info
    return {'hwnd':None,'title':'Active window unavailable','pid':None,'process':'Unavailable','exe':'Unavailable'}


def display_info():
    out={'screens':0,'primary':None,'total_geometry':None}
    try:
        from core.qt_compat import QApplication
        app=QApplication.instance()
        if app:
            screens=app.screens(); out['screens']=len(screens)
            if screens:
                s=app.primaryScreen(); g=s.geometry(); out['primary']={'width':g.width(),'height':g.height(),'dpi':round(s.logicalDotsPerInch(),1)}
                rect=screens[0].virtualGeometry(); out['total_geometry']={'width':rect.width(),'height':rect.height()}
    except Exception: pass
    return out


def screenshot(path=None):
    try: from PIL import ImageGrab
    except Exception: return {'ok':False,'error':'Pillow is not installed; screenshot capture is unavailable.'}
    try:
        target=Path(path) if path else Path.home()/'Pictures'/'VEXORA'; target.mkdir(parents=True,exist_ok=True)
        filename=target/f'see_{datetime.now():%Y%m%d_%H%M%S_%f}.png'; image=ImageGrab.grab(all_screens=True); image.save(filename,'PNG',optimize=True)
        return {'ok':True,'path':str(filename),'width':image.width,'height':image.height}
    except Exception as exc: return {'ok':False,'error':f'{type(exc).__name__}: {exc}'}


def ocr_image(path):
    try: import pytesseract
    except Exception: return {'ok':False,'available':False,'text':'','error':'pytesseract is not installed.'}
    try:
        from PIL import Image
        text=pytesseract.image_to_string(Image.open(path),timeout=5).strip()
        return {'ok':True,'available':True,'text':text[:6000],'characters':len(text)}
    except Exception as exc: return {'ok':False,'available':True,'text':'','error':f'{type(exc).__name__}: {exc}'}


def screen_fingerprint(path):
    try:
        import hashlib
        h=hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()[:16]
    except Exception: return None


def inspect_screen(include_screenshot=False, include_ocr=False):
    active=active_window(); display=display_info(); shot=None; ocr=None
    if include_screenshot:
        shot=screenshot()
        if shot.get('ok') and include_ocr: ocr=ocr_image(shot['path'])
    return {'timestamp':datetime.now().isoformat(timespec='seconds'),'platform':platform.platform(),'active_window':active,'display':display,
            'screenshot':shot,'ocr':ocr,'capabilities':{'active_window':active.get('title')!='Active window unavailable','screenshot':True,'ocr':bool(_ocr_available())}}


def _ocr_available():
    try: import pytesseract; return True
    except Exception: return False


def screen_summary():
    s=inspect_screen(False,False); a=s['active_window']; d=s['display']; p=d.get('primary'); display=f"{p['width']}×{p['height']} @ {p['dpi']} DPI" if p else 'unknown display'
    return f"Screen context\n• Active window: {a.get('title')}\n• Process: {a.get('process')}\n• PID: {a.get('pid') or '—'}\n• Display: {display}\n• Screens: {d.get('screens',0)}\n• OCR: {'Ready' if s['capabilities']['ocr'] else 'Optional backend not installed'}"
