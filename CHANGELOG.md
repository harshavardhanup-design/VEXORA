# Changelog

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
