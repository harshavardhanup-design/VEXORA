"""Safe browser navigation primitives. No DOM automation or arbitrary shell use."""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse
import webbrowser

@dataclass(frozen=True)
class BrowserResult:
    ok: bool
    url: str
    message: str
    requires_confirmation: bool=True

def validate_url(url: str) -> bool:
    try:
        p=urlparse(str(url).strip())
        return p.scheme in {'http','https'} and bool(p.netloc) and '\\' not in p.netloc
    except Exception:
        return False

def open_url(url: str, *, approved=False) -> BrowserResult:
    url=str(url).strip()
    if not validate_url(url): return BrowserResult(False,url,'Only valid http(s) URLs are allowed.')
    if not approved: return BrowserResult(False,url,'Browser navigation requires explicit approval.')
    try:
        ok=bool(webbrowser.open(url))
        return BrowserResult(ok,url,'Browser navigation requested.' if ok else 'Browser navigation could not be confirmed.')
    except Exception as e: return BrowserResult(False,url,f'Browser navigation failed: {type(e).__name__}: {e}')

def search_url(query: str, engine='bing') -> str:
    q=quote_plus(' '.join(str(query).split()))
    if engine=='google': return f'https://www.google.com/search?q={q}'
    return f'https://www.bing.com/search?q={q}'
