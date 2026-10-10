"""Post-action verification helpers for VEXORA 5.0."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from time import monotonic
from tools.ui_understanding import observe_image
from tools.see_engine import active_window

@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str
    changed: bool=False
    active_window_changed: bool=False
    before_fingerprint: str=''
    after_fingerprint: str=''
    elapsed_ms: float=0.0
    def as_dict(self): return asdict(self)

def verify_screen_change(before_path, after_path, before_window=None, after_window=None):
    started=monotonic()
    before=observe_image(before_path) if before_path else None
    after=observe_image(after_path) if after_path else None
    if not before or not before.ok or not after or not after.ok:
        return VerificationResult(False,'Screen observation unavailable.',elapsed_ms=(monotonic()-started)*1000)
    bw=before_window or {}
    aw=after_window or {}
    window_changed=(bw.get('title','')!=aw.get('title','') or bw.get('process','')!=aw.get('process',''))
    changed=before.fingerprint != after.fingerprint
    return VerificationResult(changed or window_changed,'Screen or active-window state changed.' if (changed or window_changed) else 'No observable screen change.',changed,window_changed,before.fingerprint,after.fingerprint,(monotonic()-started)*1000)

def verify_active_window(expected_process=None, expected_title=None):
    w=active_window()
    process=(w.get('process') or '').lower()
    title=(w.get('title') or '').lower()
    p=not expected_process or expected_process.lower() in process
    t=not expected_title or expected_title.lower() in title
    return VerificationResult(bool(p and t),'Active window matches requested context.' if p and t else 'Active window does not match requested context.')
