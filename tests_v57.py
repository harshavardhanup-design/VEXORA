import ast, pathlib, re, zipfile
ROOT=pathlib.Path(__file__).resolve().parent
ui=(ROOT/'app/ui/main_window.py').read_text(encoding='utf-8')
chat=(ROOT/'ai/chatbot.py').read_text(encoding='utf-8')
store=(ROOT/'memory/store.py').read_text(encoding='utf-8')
assert 'def settings_page(self,p,l):' in ui
assert 'QScrollArea()' in ui and 'SettingsScroll' in ui and 'SettingsHost' in ui
assert "quick[:9]" in ui and "('What I can do','__capabilities__')" in ui
assert "if text=='__capabilities__':" in ui
for key in ['reduce_motion','start_page','feedback_enabled','require_action_confirmation','screen_context','ocr_enabled','online_knowledge','use_local_model']:
    assert key in ui and key in store, key
for phrase in ['Here is what I can do right now:','• Answer general questions','• Inspect PC health','• Show detailed system specifications','• Capture the screen','• Build permission-gated plans']:
    assert phrase in chat or phrase in ui, phrase
# compile every Python source
for p in ROOT.rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
# no accidental API secrets in source
for p in ROOT.rglob('*.py'):
    txt=p.read_text(encoding='utf-8',errors='ignore')
    assert not re.search(r'(AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,})',txt), p
print('ALL V5.7 STATIC TESTS PASSED')
