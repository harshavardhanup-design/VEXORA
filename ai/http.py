"""Small HTTP helper shared by all AI providers.

* one place for timeouts, retries and error translation
* retries only transient failures (429 / 5xx / network) with capped backoff
* error text never contains request headers, so API keys cannot leak into the UI
"""
from __future__ import annotations
import json, time, urllib.error, urllib.request
from core.logging_setup import get_logger

log = get_logger('http')
_RETRY_STATUS = {429, 500, 502, 503, 504}
_HINTS = {
    400: 'the request was rejected (check the model ID)',
    401: 'the API key was rejected',
    403: 'access was denied (check key permissions or region)',
    404: 'the model or endpoint was not found (check the model ID)',
    429: 'rate limit or quota reached',
}


class HttpError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _describe(exc: Exception) -> tuple[str, int | None, bool]:
    if isinstance(exc, urllib.error.HTTPError):
        hint = _HINTS.get(exc.code) or ('the service had a temporary problem' if exc.code >= 500 else 'unexpected response')
        return f'HTTP {exc.code}: {hint}', exc.code, exc.code in _RETRY_STATUS
    if isinstance(exc, urllib.error.URLError):
        return 'network unreachable or timed out', None, True
    if isinstance(exc, TimeoutError):
        return 'request timed out', None, True
    if isinstance(exc, json.JSONDecodeError):
        return 'the service returned invalid JSON', None, False
    return type(exc).__name__, None, False


def request_json(url: str, *, payload: dict | None = None, headers: dict | None = None,
                 timeout: float = 15.0, retries: int = 1, backoff: float = 0.6) -> dict:
    """GET (no payload) or POST JSON. Raises ``HttpError`` with a safe message."""
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    hdrs = {'User-Agent': 'VEXORA', **(headers or {})}
    if body is not None:
        hdrs.setdefault('Content-Type', 'application/json')
    last: HttpError | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, headers=hdrs, method='POST' if body is not None else 'GET')
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode('utf-8', 'replace'))
        except Exception as exc:  # translated below; never re-raise raw (may embed URL/headers)
            msg, status, transient = _describe(exc)
            last = HttpError(msg, status)
            log.warning('request failed (attempt %d/%d): %s', attempt + 1, retries + 1, msg)
            if not transient or attempt >= retries:
                break
            time.sleep(min(backoff * (2 ** attempt), 3.0))
    raise last or HttpError('request failed')
