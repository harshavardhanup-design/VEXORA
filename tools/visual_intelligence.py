"""Lightweight visual intelligence primitives.

No action is taken here. The module extracts observations that a future agent
can safely pass to a planner. It works with PIL and optionally pytesseract.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from hashlib import sha256
from typing import Iterable

@dataclass(frozen=True)
class VisualRegion:
    kind: str
    left: int
    top: int
    width: int
    height: int
    confidence: float
    label: str = ''

@dataclass(frozen=True)
class VisualReport:
    ok: bool
    width: int=0
    height: int=0
    fingerprint: str=''
    regions: tuple=()
    error: str=''
    def as_dict(self):
        d=asdict(self); d['regions']=[asdict(x) for x in self.regions]; return d

def _hash(path: Path):
    h=sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def compare_fingerprints(a: str, b: str) -> bool:
    return bool(a and b and a == b)

def text_regions(path, *, max_regions=120):
    try:
        import pytesseract
        from pytesseract import Output
        from PIL import Image
        with Image.open(path) as im:
            d=pytesseract.image_to_data(im, output_type=Output.DICT, config='--psm 6')
        out=[]
        n=min(len(d.get('text',[])),max_regions)
        for i in range(n):
            txt=(d['text'][i] or '').strip()
            if not txt: continue
            try: conf=float(d['conf'][i])/100.0
            except Exception: conf=0.0
            if conf < 0: continue
            out.append(VisualRegion('text',int(d['left'][i]),int(d['top'][i]),int(d['width'][i]),int(d['height'][i]),max(0.0,min(1.0,conf)),txt))
        return tuple(out)
    except Exception:
        return ()

def observe(path, *, ocr=False, max_regions=120) -> VisualReport:
    p=Path(path)
    if not p.exists(): return VisualReport(False,error='Image does not exist.')
    try:
        from PIL import Image
        with Image.open(p) as im: size=im.size
        regs=text_regions(p,max_regions=max_regions) if ocr else ()
        return VisualReport(True,size[0],size[1],_hash(p),regs)
    except Exception as e:
        return VisualReport(False,error=f'{type(e).__name__}: {e}')
