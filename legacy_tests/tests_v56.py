"""VEXORA v5.6 regression + provider/UI safety tests."""
from pathlib import Path
import random, string, time, threading, sys
ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT))
from ai.providers import GEMINI_FREE_MODELS, OPENAI_MODELS
from ai.chatbot import local_chat
from agent.command_router import handle_result
ui=(ROOT/'app/ui/main_window.py').read_text(encoding='utf-8')
chat=(ROOT/'ai/chatbot.py').read_text(encoding='utf-8')
providers=(ROOT/'ai/providers.py').read_text(encoding='utf-8')
assert 'Gemini API' in ui and 'OpenAI API' in ui
assert "quick[:9]" in ui
assert 'ComposerModel' in ui
assert 'feedback_enabled' in ui
assert 'remote_chat' in chat
assert 'GEMINI_API_KEY' in providers and 'OPENAI_API_KEY' in providers
assert '_safe_persist_settings' in ui
assert len(GEMINI_FREE_MODELS)>=2 and len(OPENAI_MODELS)>=3
# No bundled secrets.
for text in (ui,chat,providers):
    assert 'AIza' not in text and 'sk-' not in text
# Offline fallback should be actionable and not claim remote access.
r=local_chat('How do I change model?',context={'model_provider':'offline','online_knowledge':False,'use_local_model':False})
assert 'Select Gemini, OpenAI API, Ollama' in r
# Provider without key must fail closed.
for provider in ('gemini','openai'):
    r=local_chat('How do I change the AI model backend?',context={'model_provider':provider,'online_knowledge':False,'use_local_model':False,'gemini_api_key':'','openai_api_key':''})
    assert 'api' in r.lower() and ('key' in r.lower() or 'unavailable' in r.lower())

# Provider response parsing without network: deterministic mocked transport.
import ai.providers as providers
old_post=providers._post_json
providers._post_json=lambda *args,**kwargs:{'candidates':[{'content':{'parts':[{'text':'Gemini OK'}]}}]}
text,err=providers._gemini('hello',[],{'gemini_api_key':'TEST_KEY','model_name':'gemini-3.8-flash'})
assert text=='Gemini OK' and err is None
providers._post_json=lambda *args,**kwargs:{'output_text':'OpenAI OK'}
text,err=providers._openai('hello',[],{'openai_api_key':'TEST_KEY','model_name':'gpt-5.6-luna'})
assert text=='OpenAI OK' and err is None
providers._post_json=old_post

# Router robustness.
rng=random.Random(560056)
for _ in range(50000):
    q=''.join(rng.choice(string.printable[:95]) for _ in range(rng.randint(0,180)))
    out=handle_result(q); assert isinstance(out.text,str)
# Parallel router load.
errs=[]
def worker(seed):
    try:
        for i in range(1500): handle_result(['How is my PC?','show recent files','what is on my screen?','open downloads','explain AI'][i%5])
    except Exception as e: errs.append((seed,e))
ts=[threading.Thread(target=worker,args=(i,)) for i in range(24)]
for t in ts:t.start()
for t in ts:t.join()
assert not errs, errs[:2]
# Provider microbench should stay cheap when no network is attempted.
t0=time.perf_counter()
for _ in range(10000):
    local_chat('What is Python?',context={'model_provider':'offline','online_knowledge':False,'use_local_model':False})
assert time.perf_counter()-t0 < 3.0
print('ALL V5.6 TESTS PASSED')
