"""Windows compatibility and capability detection for VEXORA Universal."""
from __future__ import annotations
import os, platform, sys

SUPPORTED_MAJOR = {8, 10, 11}
WINDOWS_11_MIN_BUILD = 22000
WINDOWS_11_RECOMMENDED_BUILD = 22621

def windows_version():
    if os.name != 'nt':
        return None
    try:
        v = sys.getwindowsversion()
        return (v.major, v.minor, v.build)
    except Exception:
        return None

def windows_major() -> int | None:
    v = windows_version()
    if not v: return None
    major, minor, _ = v
    if major == 6 and minor in (2, 3): return 8
    if major >= 10: return 11 if getattr(sys.getwindowsversion(), 'build', 0) >= 22000 else 10
    return major

def windows_label() -> str:
    if os.name != 'nt': return platform.system()
    try:
        raw = windows_version()
        if raw == (6, 2, raw[2]): return f"Windows 8 (build {raw[2]})"
        if raw and raw[0] == 6 and raw[1] == 3: return f"Windows 8.1 (build {raw[2]})"
        v = platform.win32_ver()
        return f"Windows {v[0] or 'unknown'} ({v[1] or platform.version()})"
    except Exception:
        return "Windows (version unavailable)"

def is_windows_11() -> bool:
    return windows_major() == 11

def windows_build() -> int | None:
    v = windows_version()
    return v[2] if v else None

def capabilities() -> dict:
    major = windows_major()
    return {
        'windows': major,
        'windows_supported': major in SUPPORTED_MAJOR if major else os.name != 'nt',
        'legacy_windows': major == 8,
        'python': sys.version_info[:3],
        'qt_target': 'PySide2' if major == 8 else 'PySide6',
        'screen_capture': True,
        'ocr_optional': True,
        'automation_optional': True,
        'local_first': True,
        'windows_11': major == 11,
        'windows_build': windows_build(),
        'dpi_aware_target': major in (10, 11),
        'native_settings': major in (10, 11),
        'modern_paths': major in (10, 11),
        'performance_profile': 'windows-11' if major == 11 else ('legacy' if major == 8 else 'portable'),
    }

def compatibility_report() -> str:
    c = capabilities()
    if os.name != 'nt':
        return 'Development platform • Windows compatibility layer enabled'
    return f"{windows_label()} • {c['qt_target']} compatibility target"
