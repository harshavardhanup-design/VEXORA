import datetime, os, re, urllib.parse
from ai.http import HttpError, request_json
from ai.providers import remote_chat
from ai.safe_math import safe_calc
from core.logging_setup import get_logger

log = get_logger('chat')
OLLAMA_TIMEOUT = 90.0  # local generation routinely exceeds the old 4s limit


def _clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()

def _contains(text, words):
    value=' '.join(str(text or '').lower().split())
    return any(re.search(r'\b'+re.escape(w.lower())+r'\b', value) for w in words)

_safe_calc = safe_calc  # backwards-compatible alias

def _http_json(url, timeout=2):
    return request_json(url, timeout=timeout, retries=0)

def _wikipedia_answer(question):
    try:
        q=urllib.parse.quote(question[:180])
        data=_http_json('https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch='+q+'&srlimit=1&format=json&utf8=1',1.8)
        hits=data.get('query',{}).get('search',[])
        if not hits:return None
        title=hits[0].get('title','')
        summary=_http_json('https://en.wikipedia.org/api/rest_v1/page/summary/'+urllib.parse.quote(title.replace(' ','_')),1.8)
        extract=(summary.get('extract') or '').strip()
        if not extract:return None
        return (extract[:1197].rsplit(' ',1)[0]+'…' if len(extract)>1200 else extract)+f'\n\nSource: Wikipedia — {title}'
    except (HttpError, KeyError, TypeError, ValueError) as exc:
        log.info('wikipedia lookup failed: %s', exc); return None

def _ollama_answer(question,history,context):
    """Return ``(answer, error)``. Uses the selected model; never simulates another."""
    host=(context.get('ollama_host') or os.getenv('OLLAMA_HOST','http://127.0.0.1:11434')).strip()
    if not host.startswith(('http://','https://')): host='http://'+host
    model=context.get('model_name') or os.getenv('VEXORA_MODEL','llama3.2')
    name=context.get('assistant_name') or 'VEXORA'
    system=(f'You are the local Ollama model selected by the user inside {name}. '
            'Generate the answer with the selected model itself; do not simulate another model. '
            'Preserve your normal model behavior and capabilities. '
            'Never claim a computer action happened unless a local tool confirmed it. '
            'Do not invent current facts. If uncertain, say so.')
    messages=[{'role':'system','content':system}]
    for item in (history or [])[-10:]:
        if item.get('user'): messages.append({'role':'user','content':item['user']})
        if item.get('assistant'): messages.append({'role':'assistant','content':item['assistant']})
    messages.append({'role':'user','content':question})
    payload={'model':model,'messages':messages,'stream':False,'options':{'temperature':0.2,'num_predict':650}}
    try:
        timeout=max(5.0,min(float(context.get('request_timeout',OLLAMA_TIMEOUT)),300.0))
    except (TypeError,ValueError):
        timeout=OLLAMA_TIMEOUT
    try:
        data=request_json(host.rstrip('/')+'/api/chat',payload=payload,timeout=timeout,retries=0)
    except HttpError as exc:
        hint=f' Is "{model}" installed? Try: ollama pull {model}' if exc.status==404 else ' Check that Ollama is running.'
        return None,f'Ollama request failed — {exc}.{hint}'
    ans=((data.get('message') or {}).get('content') or '').strip()
    return (ans,None) if ans else (None,'Ollama returned an empty response.')

def _local_facts(l):
    # Time-sensitive facts (officeholders etc.) are deliberately NOT hard-coded: they go stale.
    facts=[
      (r'\bcapital\b',['india'], 'The capital of India is New Delhi.'),
    ]
    for pattern,words,answer in facts:
        if re.search(pattern,l) and _contains(l,words): return answer
    exact={
      'what is python':'Python is a high-level, general-purpose programming language known for readable syntax and a large ecosystem. It is widely used in automation, web development, data science, AI/ML and scripting.',
      'what is artificial intelligence':'Artificial intelligence (AI) is the field of building systems that perform tasks that normally require capabilities such as perception, language understanding, reasoning, learning or decision-making.',
      'what is machine learning':'Machine learning is a branch of AI in which models learn patterns from data to make predictions, classifications or decisions instead of being explicitly programmed for every case.',
      'what is cpu':'The CPU is the central processor that executes instructions and coordinates computation. Performance depends on architecture, cores, cache, clock behavior and workload.',
      'what is gpu':'A GPU is a processor optimized for highly parallel workloads. Modern GPUs are used for graphics, AI, simulation, video and other compute tasks.',
      'what is ram':'RAM is volatile working memory used by the operating system and applications while they run. More RAM can help when many memory-heavy programs are open at once.',
      'who is albert einstein':'Albert Einstein was a German-born theoretical physicist known for relativity and major contributions to quantum theory. He received the 1921 Nobel Prize in Physics for his explanation of the photoelectric effect.',
      'who was apj abdul kalam':'A. P. J. Abdul Kalam was an Indian aerospace scientist and the 11th President of India, serving from 2002 to 2007.',
      'who is apj abdul kalam':'A. P. J. Abdul Kalam was an Indian aerospace scientist and the 11th President of India, serving from 2002 to 2007.',
    }
    return exact.get(l)

def _fresh(l): return bool(re.search(r'\b(current|currently|today|latest|now|recent|prime minister|president|chief minister|ceo of|leader of)\b',l))
def _fact(l): return bool(re.search(r'\b(who|what|where|when|which|capital|define|explain|how does|why does)\b',l))

def _capabilities_text(name='VEXORA'):
    return (f'Here is what I can do right now:\n\n'
            '• Answer general questions and explain technical concepts.\n'
            '• Use the selected Gemini, OpenAI or Ollama model for general chat.\n'
            '• Calculate expressions and handle quick factual requests.\n'
            '• Create, review and complete My Work tasks.\n'
            '• Prepare a practical workday/workspace.\n'
            '• Inspect CPU, RAM, storage, battery and running processes.\n'
            '• Show detailed hardware, Windows, BIOS and runtime specifications.\n'
            '• Capture the screen and optionally read visible text with OCR.\n'
            '• Read recent files and help with recent computer activity.\n'
            '• Open Windows Settings and selected safe applications through protected tools.\n'
            '• Build approval-gated plans for supported computer actions.\n'
            '• Keep contextual task/chat memory locally in the workspace.\n'
            '• Provide study, productivity and focused next-action guidance.\n\n'
            'Protected computer actions require approval; unrestricted shell control is not provided.')

def local_chat(text,history=None,context=None):
    q=_clean(text); l=re.sub(r'[?!.,]+$','',q.lower()).strip(); hist=history or []; ctx=context or {}
    if not q:return 'Tell me what you want to accomplish.'
    provider=(ctx.get('model_provider') or 'offline').lower(); provider_error=None

    # For a selected AI provider, the provider gets first refusal on general chat.
    # The app must actually use the chosen model instead of answering with a local
    # canned response while merely displaying its name.
    if provider in ('gemini','openai'):
        ans,err=remote_chat(provider,q,hist,ctx)
        if ans:return ans
        provider_error=err
        if not ctx.get('online_knowledge',True):return err or f'{provider.title()} did not return a response.'
    if provider=='ollama' and ctx.get('use_local_model',True):
        ans,err=_ollama_answer(q,hist,ctx)
        if ans:return ans
        provider_error=err
        if not ctx.get('online_knowledge',True):return err

    # Offline fallback retains deterministic built-in behavior.
    fact=_local_facts(l)
    if fact:return fact
    calc=re.sub(r'^(calculate|compute|what is)\s+','',l).strip().rstrip('?!.,')
    if re.fullmatch(r'[0-9+\-*/().%\s**×÷^]+',calc or '') and any(c.isdigit() for c in calc):
        v=_safe_calc(calc)
        if v is not None:return f'The answer is {v:g}.' if isinstance(v,(int,float)) else f'The answer is {v}.'
    name=ctx.get('assistant_name') or 'VEXORA'
    if _contains(l,['hello','hi','hey','namaste']): return f'Hello! I’m {name}. Ask a question, inspect your PC, manage work, or give me a goal and I’ll help turn it into actions.'
    if l in ('help','help me','what can you do','what do you do','capabilities'):
        return _capabilities_text(name)
    if 'who are you' in l or 'what are you' in l:return f'I’m {name} — a desktop AI assistant designed to combine conversation, computer context, workspace memory and controlled actions.'
    now=datetime.datetime.now()
    if re.search(r'\b(time|current time)\b',l):return now.strftime('The local time is %I:%M %p.')
    if re.search(r'\b(date|today|what day)\b',l):return now.strftime('Today is %A, %d %B %Y.')
    if _contains(l,['study','exam','revision','revise']):return 'Study mode: give me the subject, exam date and available time. I can structure learn → recall → practice → review and generate a short quiz.'
    if _contains(l,['productivity','focus','concentrate']):return 'Productivity mode: pick one measurable outcome, define the first action, work in a focused block, then review. I can also inspect active processes and help plan your next task.'
    if 'my work' in l or 'task' in l:
        tasks=ctx.get('tasks',[]); a=sum(not t.get('done') for t in tasks); d=sum(t.get('done') for t in tasks); return f'My Work has {a} active task(s) and {d} completed task(s). You can create or complete tasks directly from chat.'
    if 'system specification' in l or 'pc specs' in l or 'computer specs' in l:return f'Open System Specifications for live CPU, GPU, RAM, storage, Windows, BIOS, motherboard, Python and {name} environment details.'
    if _fresh(l) and ctx.get('online_knowledge',True):
        ans=_wikipedia_answer(q)
        if ans:return ans
    if provider_error: return provider_error
    return f'I can help with “{q}”, but the offline backend does not have enough verified context. Select a live AI model or enable Online Knowledge.'

