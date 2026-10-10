"""Dependency-light visual UI understanding for VEXORA 5.0.

The module is deliberately fail-closed: screenshot analysis never performs an
input action. OCR is optional and only returns observations. Coordinates are
metadata until a separately approved action consumes them.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class TextRegion:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float

@dataclass(frozen=True)
class ScreenObservation:
    ok: bool
    width: int = 0
    height: int = 0
    fingerprint: str = ""
    text_regions: tuple = ()
    ocr_available: bool = False
    error: str = ""
    def as_dict(self):
        d=asdict(self); d['text_regions']=[asdict(x) for x in self.text_regions]; return d

def _fingerprint(path: Path) -> str:
    h=sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def observe_image(path, *, ocr=False, max_regions=200) -> ScreenObservation:
    p=Path(path)
    if not p.exists(): return ScreenObservation(False,error='Image does not exist.')
    try:
        from PIL import Image
        with Image.open(p) as im:
            width,height=im.size
        regions=[]; available=False
        if ocr:
            try:
                import pytesseract
                from pytesseract import Output
                available=True
                with Image.open(p) as im:
                    data=pytesseract.image_to_data(im,output_type=Output.DICT,config='--psm 6')
                n=min(len(data.get('text',[])),max_regions)
                for i in range(n):
                    text=(data['text'][i] or '').strip()
                    if not text: continue
                    try: conf=float(data['conf'][i])
                    except Exception: conf=-1.0
                    if conf < 0: continue
                    regions.append(TextRegion(text,int(data['left'][i]),int(data['top'][i]),int(data['width'][i]),int(data['height'][i]),conf/100.0))
            except Exception:
                # Optional OCR must never turn screen observation into a crash.
                available=False
        return ScreenObservation(True,width,height,_fingerprint(p),tuple(regions),available)
    except Exception as e:
        return ScreenObservation(False,error=f'{type(e).__name__}: {e}')

def find_text(observation: ScreenObservation, query: str):
    q=' '.join(str(query).lower().split())
    if not q: return []
    return [r for r in observation.text_regions if q in ' '.join(r.text.lower().split())]
