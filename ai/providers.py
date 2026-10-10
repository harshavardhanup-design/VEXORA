"""Thin, real provider adapters for VEXORA.

The selected provider/model is the actual backend. VEXORA only adds a minimal
system contract so the model cannot falsely claim that a local computer action
was completed. API keys are supplied by the user and are never bundled or logged.
"""
from __future__ import annotations
import os, urllib.parse
from ai.http import HttpError, request_json
from core.logging_setup import get_logger

log = get_logger('providers')

GEMINI_FREE_MODELS = ['gemini-3.8-flash', 'gemini-3.7-flash']
OPENAI_MODELS = ['gpt-5.6-luna', 'gpt-5.6-terra', 'gpt-5.6-sol']
HISTORY_TURNS = 12
DEFAULT_TIMEOUT = 30.0  # generation is slower than a ping; 12-15s caused false failures


def _post_json(url, payload, headers, timeout=DEFAULT_TIMEOUT):
    return request_json(url, payload=payload, headers=headers, timeout=timeout, retries=1)


def _system(context):
    name = context.get('assistant_name') or 'VEXORA'
    return (f'You are the selected AI model inside {name}. Respond using your own model capabilities and normal behavior. '
            f'Do not pretend to be a different model. {name} is a desktop shell around you. '
            'Never claim that a local computer action happened unless a VEXORA tool explicitly confirmed it. '
            'Otherwise answer the user directly; do not add unnecessary branding or meta-commentary.')


def _turns(history):
    """Yield (role, text) pairs from stored history, newest ``HISTORY_TURNS`` only."""
    for item in (history or [])[-HISTORY_TURNS:]:
        if item.get('user'):
            yield 'user', item['user']
        if item.get('assistant'):
            yield 'assistant', item['assistant']


def _key(context, ctx_field, env):
    return (context.get(ctx_field) or os.getenv(env) or '').strip()


def _timeout(context):
    try:
        return max(5.0, min(float(context.get('request_timeout', DEFAULT_TIMEOUT)), 180.0))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _gemini(question, history, context):
    key = _key(context, 'gemini_api_key', 'GEMINI_API_KEY')
    if not key:
        return None, 'Gemini API key is not configured.'
    model = (context.get('model_name') or GEMINI_FREE_MODELS[0]).strip()
    contents = [{'role': 'user' if r == 'user' else 'model', 'parts': [{'text': t}]} for r, t in _turns(history)]
    contents.append({'role': 'user', 'parts': [{'text': question}]})
    payload = {'system_instruction': {'parts': [{'text': _system(context)}]}, 'contents': contents}
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model, safe="")}:generateContent'
    try:
        data = _post_json(url, payload, {'x-goog-api-key': key}, _timeout(context))
    except HttpError as exc:
        return None, f'Gemini request failed — {exc}'
    chunks = [p['text'] for c in data.get('candidates', []) or []
              for p in (c.get('content') or {}).get('parts', []) or []
              if isinstance(p, dict) and p.get('text')]
    text = ''.join(chunks).strip()
    if text:
        return text, None
    reason = (data.get('promptFeedback') or {}).get('blockReason')
    return None, f'Gemini returned no text{f" (blocked: {reason})" if reason else ""}.'


def _openai(question, history, context):
    key = _key(context, 'openai_api_key', 'OPENAI_API_KEY')
    if not key:
        return None, 'OpenAI API key is not configured.'
    model = (context.get('model_name') or OPENAI_MODELS[0]).strip()
    items = [{'role': r, 'content': t} for r, t in _turns(history)]
    items.append({'role': 'user', 'content': question})
    payload = {'model': model, 'input': items, 'instructions': _system(context), 'max_output_tokens': 900}
    try:
        data = _post_json('https://api.openai.com/v1/responses', payload, {'Authorization': 'Bearer ' + key}, _timeout(context))
    except HttpError as exc:
        return None, f'OpenAI request failed — {exc}'
    text = (data.get('output_text') or '').strip()
    if not text:
        text = ''.join(p['text'] for item in data.get('output', []) or [] if isinstance(item, dict)
                       for p in item.get('content', []) or [] if isinstance(p, dict) and p.get('text')).strip()
    return (text, None) if text else (None, 'OpenAI returned no text.')


def remote_chat(provider, question, history, context):
    p = (provider or '').lower()
    if p == 'gemini':
        return _gemini(question, history, context)
    if p == 'openai':
        return _openai(question, history, context)
    return None, 'No remote provider selected.'
