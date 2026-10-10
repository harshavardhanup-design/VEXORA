"""Deterministic intent router for local tools.

Design notes
------------
* Table-driven: each ``Intent`` is a compiled, word-boundary regex + handler.
  The previous implementation used raw substring checks (``'ram' in q``), which
  hijacked ordinary chat -- "write a *program*" produced a RAM report and
  "*help* me write a poem" produced the capabilities list.
* Order is significant (first match wins) and is covered by tests.
* Anything unmatched returns an empty ``Result`` so the caller falls through to
  the selected chat model.
* The public API (``Result``, ``Agent``, ``get_agent``, ``handle_result``,
  ``approve``, ``cancel``) and the plan-dict keys are unchanged.
"""
from __future__ import annotations
import re, threading, time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from ai.model import LocalModel
from agent.planner import plan as build_agent_plan
from monitoring.pc_health import PcHealth
from security.permissions import is_protected_request
from tools.everyday import recent_files
from tools.performance import diagnose
from tools.see_engine import screen_summary


@dataclass
class Result:
    text: str
    plan: dict | None = None
    task: dict | None = None
    requires_confirmation: bool = False


class Agent:
    def __init__(self):
        self.model = LocalModel()
        self.health = PcHealth()
        self._cache: dict = {}
        self._cache_lock = threading.RLock()

    def _cached(self, key, fn, ttl=0.35):
        now = time.monotonic()
        with self._cache_lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
        value = fn()  # compute outside the lock so a slow probe never blocks other callers
        with self._cache_lock:
            self._cache[key] = (now, value)
        return value

    def status(self):
        return {'model': self.model.status()}


_agent = Agent()


def get_agent() -> Agent:
    return _agent


def _recent_files(limit=8):
    return _agent._cached(f'recent:{limit}', lambda: recent_files(limit), 0.35)


# ── handlers ────────────────────────────────────────────────────────────────
def _h_recent(text, m):
    rows = _recent_files()
    if not rows:
        return 'No recent files were found in Desktop, Documents or Downloads.'
    return 'Recent files:\n' + '\n'.join(
        f'• {p.name} — {datetime.fromtimestamp(ts):%d %b %H:%M} ({p.parent.name})' for ts, p in rows)


def _h_ram(text, m):
    rows = _agent._cached('top_memory', _agent.health.top_memory)
    if not rows:
        return 'No process telemetry is available.'
    return 'Top memory consumers:\n' + '\n'.join(f'• {n} (PID {pid}) — {mem:.1f}%' for n, pid, mem in rows)


def _h_processes(text, m):
    rows = _agent._cached('running', _agent.health.running)
    if not rows:
        return 'No process telemetry is available.'
    return 'Running processes:\n' + '\n'.join(f'• {n} (PID {pid})' for n, pid in rows)


def _h_health(text, m):
    s = _agent._cached('snapshot', _agent.health.snapshot)
    power = 'Charging' if s.charging else 'On battery' if s.battery is not None else 'Unavailable'
    return f'PC health snapshot:\n• CPU: {s.cpu:.0f}%\n• RAM: {s.ram:.0f}%\n• Storage: {s.disk:.0f}%\n• Power: {power}'


def _h_performance(text, m):
    s, findings = _agent._cached('diagnose', diagnose)
    return (f'Performance report:\n• CPU: {s.cpu:.0f}%\n• RAM: {s.ram:.0f}%\n• Storage: {s.disk:.0f}%\n'
            f'• Processes: {s.processes}\n\n' + '\n'.join('• ' + x for x in findings))


def _h_screen(text, m):
    return screen_summary()


def _static(msg):
    return lambda text, m: msg


@dataclass(frozen=True)
class Intent:
    name: str
    tool: str | None
    confidence: float
    pattern: re.Pattern
    handler: Callable
    action: str | None = None
    extra: Callable | None = None


def _rx(p):
    return re.compile(p, re.IGNORECASE)


_OPEN = r'\b(?:open|launch|start)\s+(?:the\s+|my\s+)?'


def _launcher(action, label, pattern, msg):
    return Intent(f'Open {label}', 'safe_app_launcher', .99, _rx(_OPEN + pattern), _static(msg), action)


# Order matters: more specific intents first.
INTENTS: tuple[Intent, ...] = (
    Intent('Inspect recent work', 'recent_files', .96, _rx(r'\b(?:recent|latest)\s+(?:files?|work)\b'), _h_recent),
    Intent('Inspect RAM usage', 'top_memory', .98,
           _rx(r'\b(?:(?:ram|memory)\s+(?:usage|hogs?|consumers?|use)|(?:using|eating|hogging|consuming)\s+(?:my\s+|the\s+)?(?:ram|memory)|'
               r'(?:my|pc|computer|system)\s+(?:ram|memory)|(?:top|most)\s+(?:ram|memory))\b'), _h_ram),
    Intent('Inspect running processes', 'running_processes', .97,
           _rx(r'\b(?:running\s+(?:apps?|processes|programs)|(?:list|show)\s+(?:the\s+)?processes)\b'), _h_processes),
    Intent('Analyze PC performance', 'performance_diagnosis', .98,
           _rx(r'\b(?:diagnose\s+performance|performance\s+(?:report|issues?)|analy[sz]e\s+(?:my\s+pc\s+)?performance|optimi[sz]e\s+my\s+pc)\b'), _h_performance),
    Intent('Diagnose PC health', 'system_status', .99,
           _rx(r'\b(?:how\s+is\s+my\s+(?:pc|computer|laptop)|(?:pc|computer|system)\s+health|diagnose\s+(?:my\s+)?(?:pc|computer|laptop)|'
               r'(?:my\s+)?(?:pc|computer|laptop)\s+(?:is\s+|feels\s+|running\s+)?(?:slow|laggy|lagging|freezing))\b'), _h_health),
    Intent('Check vision capability', 'vision_status', .99, _rx(r'\bvision\s+status\b'),
           _static('Vision capability: screenshot capture is available through the controlled SEE tool.')),
    Intent('Inspect current screen context', 'screen_inspect', .98,
           _rx(r'\b(?:what(?:\'?s|\s+is)\s+on\s+my\s+screen|inspect\s+my\s+screen|screen\s+summary|active\s+window|what\s+app\s+am\s+i\s+using|what\s+window\s+is\s+open)\b'), _h_screen),
    Intent('Plan computer action', 'agent_plan', .93, _rx(r'\b(?:plan\s+this|make\s+a\s+plan|plan\s+and\s+execute|execute\s+this|do\s+this\s+for\s+me)\b'),
           _static('Agent plan prepared. Protected computer actions still require approval.')),
    Intent('Build everyday workflow', 'everyday_workflow', .97, _rx(r'\b(?:today\s+workflow|build\s+my\s+workflow|work\s+workflow|organi[sz]e\s+my\s+work)\b'),
           _static('I can build a task-aware workflow from your active tasks and recent work.')),
    Intent('Inspect system specifications', 'system_specs', .98, _rx(r'\b(?:system\s+specifications?|pc\s+specs?|computer\s+specs?)\b'),
           _static('System Specifications can display live CPU, GPU, RAM, storage, Windows, BIOS, motherboard, Python and VEXORA environment information.')),
    Intent('Open Windows Settings', 'windows_settings', .98, _rx(r'^\s*(?:open\s+settings|windows\s+settings)\s*$|\bopen\s+windows\s+settings\b'),
           _static('Windows Settings is available through the controlled system tool.'), 'windows_settings'),
    _launcher('calculator', 'Calculator', r'(?:calculator|calc)\b', 'Opening Calculator through the safe application launcher.'),
    _launcher('notepad', 'Notepad', r'(?:notepad|text\s+editor)\b', 'Opening Notepad through the safe application launcher.'),
    _launcher('explorer', 'File Explorer', r'(?:file\s+explorer|explorer|files)\b', 'Opening File Explorer through the safe application launcher.'),
    _launcher('browser', 'web browser', r'(?:web\s+browser|browser|chrome)\b', 'Opening the default web browser through the safe launcher.'),
    _launcher('downloads', 'Downloads', r'(?:downloads?(?:\s+folder)?)\b', 'Opening your Downloads folder.'),
    _launcher('documents', 'Documents', r'(?:documents?(?:\s+folder)?)\b', 'Opening your Documents folder.'),
    _launcher('desktop', 'Desktop', r'desktop\b', 'Opening your Desktop folder.'),
    Intent('Prepare workday', 'workday_setup', .96, _rx(r'\b(?:prepare\s+my\s+workspace|set\s+up\s+my\s+workspace|start\s+my\s+workday|workday\s+setup)\b'),
           _static('A focused workday setup can open your workspace and surface your highest-priority unfinished tasks.')),
    Intent('Build workday plan', 'workday_plan', .96, _rx(r'\b(?:what\s+should\s+i\s+(?:work\s+on|do\s+today)|today\s+plan|plan\s+my\s+work)\b'),
           _static('Use My Work → Today for a task-aware work sequence.')),
)

_HELP = _rx(r'^\s*(?:please\s+)?(?:help(?:\s+me)?|what\s+can\s+you\s+do|capabilities)\s*[?!.]*\s*$')
_HELP_TEXT = ('Supported tools: PC health, RAM consumers, running processes, recent files, screenshot capture, system '
              'specifications, persistent tasks and controlled Windows settings. General questions use the VEXORA knowledge layer.')


def handle_result(text) -> Result:
    q = ' '.join(str(text or '').lower().split())
    for it in INTENTS:
        m = it.pattern.search(q)
        if m:
            plan = {'intent': it.name, 'tool': it.tool, 'confidence': it.confidence}
            if it.action:
                plan['action'] = it.action
            if it.tool == 'agent_plan':
                plan['steps'] = build_agent_plan(str(text)).as_dict()['steps']
            return Result(it.handler(str(text), m), plan)
    if _HELP.match(q):
        return Result(_HELP_TEXT, {'intent': 'Explain capabilities', 'tool': None, 'confidence': .99})
    if is_protected_request(q):
        return Result('This protected action needs your approval before execution. No system change has been made.',
                      {'intent': 'Controlled system action', 'tool': 'permission_gate', 'confidence': .95},
                      requires_confirmation=True)
    return Result('', {'intent': 'General request', 'tool': None, 'confidence': .60})


def approve():
    return Result('Approval recorded. Only actions on the VEXORA allowlist can run; nothing else was executed.')


def cancel():
    return Result('Action cancelled. No protected system change was performed.')
