# VEXORA 5.8.1 — Professional AI Agent

VEXORA 5.8 is a Windows desktop AI assistant with a clean, vertically scrollable settings experience and real model routing.

## 5.8 highlights
- Agent Console removed completely from the navigation and UI.
- Settings rebuilt as a professional single-column vertical scroll surface; long text and controls no longer share cramped horizontal rows.
- Direct Windows Settings shortcuts: Display, Network, Bluetooth & devices, Apps, Personalization, Accounts, Windows Update, Privacy & security, Gaming, Storage, Sound, Power & battery.
- Assistant name is limited to 6 letters and propagates across the visible UI.
- Selected model is the actual general-chat backend:
  - Ollama sends requests to the selected local model ID.
  - Gemini sends requests to the selected Gemini API model ID.
  - OpenAI sends requests to the selected OpenAI Responses API model ID.
  - Offline mode is explicitly a deterministic fallback, not a fake remote model.
- Model verification performs a real request for Gemini/OpenAI and a real connectivity/model-list check for Ollama.
- Ask VEXORA keeps the "What I can do" quick action with a complete capability list.
- Protected local computer actions remain outside remote model control and require the local permission gate.

## Run
```powershell
cd VEXORA_v5_8_PROFESSIONAL_AI_AGENT
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## AI provider setup
- Ollama: install/start Ollama and install the model shown in the selector.
- Gemini: provide `GEMINI_API_KEY` in VEXORA Settings or the Windows environment.
- OpenAI: provide `OPENAI_API_KEY` in VEXORA Settings or the Windows environment. API billing is separate from ChatGPT.

No API key is bundled in this project. Keys entered in VEXORA are not written into the workspace JSON.

## Development
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -t .   # behavioral suite, no extra deps
.\.venv\Scripts\python.exe tests_v57.py; .\.venv\Scripts\python.exe tests_v58.py   # static UI checks
.\.venv\Scripts\python.exe -m ruff check .
```
Logs: `%APPDATA%\VEXORA\logs\vexora.log` (rotating, secrets redacted). Action audit trail: `%APPDATA%\VEXORA\action_audit.jsonl`.

## Architecture
| Package | Responsibility |
|---|---|
| `agent/` | Intent router (table-driven), planner, closed-loop runtime, audit log |
| `security/` | Permission policy: risk tiers, fail-closed approval rules |
| `ai/` | Provider adapters, shared HTTP client (retry/backoff/safe errors), bounded calculator |
| `tools/` | Allowlisted actions, screen/SEE engine, performance, browser primitives |
| `memory/` | Atomic workspace store with corrupt-file quarantine |
| `app/ui/` | PySide6/PySide2 interface |
