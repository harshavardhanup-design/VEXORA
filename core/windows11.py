"""Windows 11 focused runtime helpers.

All helpers are safe no-ops outside Windows. They avoid registry writes and
avoid requiring administrator privileges. The GUI can use these helpers to
select sensible defaults without making unsupported assumptions.
"""
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Windows11Profile:
    is_windows_11: bool
    build: int | None
    recommended: bool
    dark_mode: bool
    dpi_scale: float
    notes: tuple[str, ...]

def _build():
    if os.name != 'nt': return None
    try:
        import sys
        return int(sys.getwindowsversion().build)
    except Exception:
        return None

def detect_profile() -> Windows11Profile:
    if os.name != 'nt':
        return Windows11Profile(False, None, False, True, 1.0, ('non-Windows runtime',))
    b=_build(); is11=bool(b and b>=22000)
    notes=[]
    if is11:
        notes.append('Windows 11 compatibility profile active')
        if b and b>=22621: notes.append('modern Windows 11 build')
    else:
        notes.append('portable Windows profile')
    return Windows11Profile(is11,b,bool(b and b>=22621),True,1.0,tuple(notes))

def configure_process():
    """Apply low-risk process settings; never fails startup."""
    if os.name != 'nt': return False
    try:
        import ctypes
        # Per-monitor DPI awareness v2 when available; harmless fallback.
        user32=ctypes.windll.user32
        try: user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try: user32.SetProcessDPIAware()
            except Exception: pass
        return True
    except Exception:
        return False

def preferred_refresh_ms() -> int:
    p=detect_profile()
    return 2500 if p.is_windows_11 else 3000

def ui_scale_hint() -> str:
    p=detect_profile()
    return 'per-monitor-dpi-v2' if p.is_windows_11 else 'auto'
