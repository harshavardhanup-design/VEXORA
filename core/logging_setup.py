"""Central logging configuration.

Replaces the silent ``except Exception: pass`` pattern with real diagnostics.
Logs go to ``%APPDATA%/VEXORA/logs/vexora.log`` (rotating). Secrets are never
logged: callers must not pass API keys, and ``redact`` is applied defensively.
"""
from __future__ import annotations
import logging, os, re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False
_SECRET = re.compile(r'(AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9_\-]{20,}|Bearer\s+\S+)')


def redact(text: object) -> str:
    return _SECRET.sub('[REDACTED]', str(text))


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def log_dir() -> Path:
    return Path(os.getenv('APPDATA') or Path.home()) / 'VEXORA' / 'logs'


def configure(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    root = logging.getLogger('vexora')
    root.setLevel(level)
    root.propagate = False
    try:
        d = log_dir(); d.mkdir(parents=True, exist_ok=True)
        h = RotatingFileHandler(d / 'vexora.log', maxBytes=512_000, backupCount=3, encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
        h.addFilter(_RedactingFilter())
        root.addHandler(h)
    except OSError:
        root.addHandler(logging.NullHandler())  # logging must never break startup
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure()
    return logging.getLogger(f'vexora.{name}')
