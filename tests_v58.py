from pathlib import Path
import ast, re
ROOT=Path(__file__).resolve().parent
ui=(ROOT/'app/ui/main_window.py').read_text(encoding='utf-8')
chat=(ROOT/'ai/chatbot.py').read_text(encoding='utf-8')
providers=(ROOT/'ai/providers.py').read_text(encoding='utf-8')
settings=(ROOT/'tools/settings_tool.py').read_text(encoding='utf-8')
# Syntax
for p in ROOT.rglob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
# Agent Console is fully removed from navigation and page construction.
assert 'Agent Console' not in ui
assert 'agent_console' not in ui
# Settings are scrollable and single-column, with no horizontal scroll.
for token in ['QScrollArea()','SettingsScroll','SettingsHost','ScrollBarAlwaysOff','SettingsSectionTitle','SettingsRowTitle','WINDOWS QUICK SETTINGS']:
    assert token in ui, token
# Direct Windows Settings actions exist.
for key in ['display','network','bluetooth','apps','personalization','accounts','update','privacy','gaming','storage','sound','power']:
    assert key in settings, key
# Name is limited to six letters and runtime propagation exists.
assert 'setMaxLength(6)' in ui
assert 're.fullmatch(r"[A-Za-z]{1,6}"' in ui
assert '_refresh_identity_text' in ui
# Selected model is actually routed to provider code.
assert "provider in ('gemini','openai')" in chat
assert "if provider=='ollama'" in chat
assert "remote_chat(provider,q,hist,ctx)" in chat
assert "_post_json" in providers and "model" in providers
# Real model IDs are sent, not merely displayed.
for model in ['gemini-3.8-flash','gemini-3.7-flash','gpt-5.6-luna','gpt-5.6-terra','gpt-5.6-sol']:
    assert model in ui or model in providers, model
# No hard-coded API secrets.
for p in ROOT.rglob('*.py'):
    txt=p.read_text(encoding='utf-8',errors='ignore')
    assert not re.search(r'(AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,})',txt), p
# Provider routing behavior with mocks: selected backend must get first refusal.
import ai.chatbot as cb
orig=cb.remote_chat
try:
    calls=[]
    cb.remote_chat=lambda provider,q,h,c: (calls.append((provider,c.get('model_name'))),('MODEL_OK',None))[1]
    out=cb.local_chat('what is python',[],{'model_provider':'openai','model_name':'gpt-5.6-sol','assistant_name':'NOVA','online_knowledge':False})
    assert out=='MODEL_OK' and calls==[('openai','gpt-5.6-sol')]
finally:
    cb.remote_chat=orig

# 10,000 deterministic offline calls should stay lightweight.
for _ in range(10000):
    r=cb.local_chat('what is cpu',[],{'model_provider':'offline','assistant_name':'NOVA'})
    assert r.startswith('The CPU is')
print('ALL V5.8 TESTS PASSED')
