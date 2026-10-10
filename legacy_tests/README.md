Stale string-assertion tests from v5.5/v5.6. They assert UI text that was intentionally
changed in later releases (e.g. `'v5.5' in ui`) and failed before this cleanup. Kept for
reference only; superseded by `tests/` (behavioral) and `tests_v57.py` / `tests_v58.py` (static UI checks).
