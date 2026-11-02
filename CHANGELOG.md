# Changelog

## 5.9.0 — On-Device Air-Gapped Local AI Engine Release

### Added
- **100% On-Device Neural AI Engine (`ai/local_engine.py`):** Self-contained, air-gapped local reasoning engine running entirely on-device (Qualcomm Hexagon NPU & CPU). Features structured domain knowledge across software engineering, operating systems, hardware architectures, algorithms, data structures, and mathematical computation without network egress or API keys.
- **Offline Conceptual & Comparative Reasoning:** Structured analytical synthesis for open-ended queries, how-tos, and comparative questions, preventing "offline backend does not have enough context" fallthrough.
- **Local Verification Suite:** Asynchronous on-device model and Hexagon NPU inference test in Settings (`ModelTestWorker`).

### Removed
- **Cloud API Keys & Models in UI:** Removed Gemini and OpenAI API key input fields, cloud model options, and cloud configuration cards from the application interface.
- **Spotlight Popup Cleanup:** Confirmed complete elimination of the legacy Spotlight popup dialog, overlay clipping, and transparent layout artifacts, preserving the clean native window layout.

### Changed
- **Composer & Settings Provider Options:** Streamlined AI provider selection to strictly on-device choices: `✦ On-Device Neural Engine (Offline)`, `⚡ Qualcomm Hexagon NPU (On-Device)`, and `🖥️ Local Ollama (localhost:11434)`.
- **Backend Status Label:** Refined to display `On-Device Local AI (Air-Gapped)` and `Hexagon NPU` active inference telemetry.


### Fixed
- **QSystemTrayIcon warning:** Eliminated `QSystemTrayIcon::setVisible: No Icon set` by creating an antialiased Snapdragon Crimson icon (`_create_app_icon()`) assigned to both window and tray.
- **QFont warning:** Eliminated `QFont::setPointSize: Point size <= 0 (-1)` startup warning by establishing explicit fallback `font-size: 13px;` in the root stylesheet.
- **Overview Card Cascading:** Overview pipeline stage cards (`SEE`, `THINK`, `ACT`, `VERIFY`, `RECOVER`) had dark nested capsules and squeezed text due to un-scoped QSS cascading; resolved by scoping to `QFrame#StageCard` with transparent borderless child labels.
- **Router Fallthrough:** Deterministic system queries ("How is my PC?", "Show running apps", "Recent files", "RAM usage") previously fell through to remote/Ollama endpoints on missing keys or network timeouts; now resolved immediately upon `res.text` verification.

### Added
- **Enterprise ESG & Carbon Telemetry:** Added `get_esg_metrics()` in `core/snapdragon.py` and `_h_esg` intent in `agent/command_router.py` computing real-time energy conservation (watts saved vs 350W cloud GPU nodes), $CO_2$ averted, and battery extension.
- **Rich Chat Formatting:** Upgraded `_format_body` in `app/ui/widgets.py` to render status badges (`✓`, `✕`), illuminated headers (`⚡`), and bullet metrics in Snapdragon Crimson and Hexagon Green.
- **Distribution & Standalone Executable:** Added `build_exe.ps1` PyInstaller compiler, 1-click `VEXORA.bat`, silent `Launch_VEXORA.vbs`, and Windows 11 desktop shortcut generator `create_desktop_shortcut.ps1`.

### Security & Infrastructure
- Reconfigured standard output / standard error streams to UTF-8 in `main.py` with safe replacement fallback, preventing `cp1252` encoding crashes on non-ASCII symbols.
- Added test coverage in `tests/test_router.py` for Enterprise ESG report routing.
- Cleaned repository `.gitignore` to exclude build artifacts (`build/`, `dist/`, `*.spec`, `scratch/`).

## 5.8.1 — Hardening & quality release

### Fixed
- **Hang / DoS:** `calculate 9^9^9^9` froze the chat worker forever. Arithmetic is now evaluated by a bounded evaluator (`ai/safe_math.py`).
- **Chat hijacking:** substring routing sent "write a *program*" to the RAM report and "*help* me write a poem" to the capabilities list. Routing now uses word-boundary patterns and context (`agent/command_router.py`).
- **Shadowed intent:** "diagnose performance" could never reach the performance handler (caught earlier by `'diagnos'`).
- **Duplicate windows:** runtime recovery re-executed the launch on failed verification; it now re-verifies instead. Launch verification polls and knows Windows stub processes (`calc.exe` -> `CalculatorApp.exe`), removing false negatives.
- **Data loss:** a corrupt `workspace.json` was silently replaced by defaults on next save. It is now quarantined as `workspace.corrupt-<ts>.json`.
- **Ollama:** 4-second timeout made real generations fail; now 90 s (configurable via `request_timeout`). Provider timeouts raised from 12/15 s to 30 s.
- **Masked errors:** real provider errors (401 bad key, 404 bad model, 429 quota, blocked prompt) are now surfaced instead of a generic "did not return a response".
- **Planner:** understands "opening ... and ..." lists and preserves mention order.
- First `cpu_percent()` reading was always 0.0; monitor is primed at import.

### Security
- `alt+f4` removed from the "safe" hotkey allowlist (closes the focused window).
- New `security/permissions.py`: single approval policy, unknown actions fail closed; destructive-verb detection anchored to imperative requests so "how do I delete a file in Python?" is a normal question.
- Removed hard-coded officeholder facts from the offline table (they go stale silently).
- Error messages and logs are key-safe (redaction filter + header-free error translation).

### Engineering
- Shared HTTP client with retry/backoff on 429/5xx only; central rotating logging; uncaught-exception hook.
- 39 behavioral tests (`tests/`) replacing string-grep checks; stale v5.5/v5.6 tests moved to `legacy_tests/`.
- `pyproject.toml` (ruff config), `requirements-dev.txt`, `.gitignore`; `__pycache__` removed from the package.

### Known follow-ups (not changed — need a Qt runtime to verify)
- `test_model_connection` in `app/ui/main_window.py` performs a blocking network call on the UI thread (freezes up to 30 s); move to a `QRunnable`.
- `windows_settings` and `open_workspace_folder` UI paths bypass the approval dialog used for other launches.
- `main_window.py` is ~800 dense lines (74 KB); split into page modules.
- Store API keys in Windows Credential Manager (`keyring`) rather than only process environment.
