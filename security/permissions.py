"""Central permission policy.

Single source of truth for "does this need the user's approval?" so the router,
runtime and UI cannot drift apart. Nothing here executes anything.
"""
from __future__ import annotations
import re
from enum import Enum


class Risk(str, Enum):
    READ = 'read'          # inspect only (health, recent files)
    LAUNCH = 'launch'      # opens an app/folder/URL
    INPUT = 'input'        # synthetic keyboard / mouse
    MODIFY = 'modify'      # changes files or system state


ACTION_RISK = {
    'calculator': Risk.LAUNCH, 'notepad': Risk.LAUNCH, 'explorer': Risk.LAUNCH,
    'downloads': Risk.LAUNCH, 'documents': Risk.LAUNCH, 'desktop': Risk.LAUNCH,
    'browser': Risk.LAUNCH, 'windows_settings': Risk.LAUNCH,
    'type_text': Risk.INPUT, 'press_key': Risk.INPUT, 'hotkey': Risk.INPUT, 'click': Risk.INPUT,
}

# Imperative requests to change the machine. Anchored to the *start* of the
# request so "how do I delete a file in Python?" is a normal question, while
# "please delete my downloads" is gated.
_PROTECTED = re.compile(
    r'^\s*(?:please\s+)?(?:(?:can|could|would|will)\s+you\s+)?(?:please\s+)?'
    r'(?:delete|remove|erase|shut\s?down|power\s?off|restart|reboot|log\s?off|sign\s?out|'
    r'move|rename|create\s+(?:a\s+)?(?:new\s+)?(?:folder|file|directory)|make\s+(?:a\s+)?(?:new\s+)?(?:folder|directory))\b',
    re.IGNORECASE)


def risk_of(action: str) -> Risk:
    """Unknown actions are treated as the most dangerous tier (fail closed)."""
    return ACTION_RISK.get((action or '').strip().lower(), Risk.MODIFY)


def is_protected_request(text: str) -> bool:
    return bool(_PROTECTED.search(text or ''))


def requires_approval(action: str, *, require_confirmation: bool = True) -> bool:
    """INPUT and MODIFY always need approval; LAUNCH follows the user setting."""
    r = risk_of(action)
    if r in (Risk.INPUT, Risk.MODIFY):
        return True
    return bool(require_confirmation) if r is Risk.LAUNCH else False
