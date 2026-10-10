import os
from ai.http import HttpError, request_json

DEFAULT_MODELS = ['llama3.2', 'llama3.1', 'qwen2.5', 'mistral', 'phi3.5', 'gemma2']


class ModelStatus:
    def __init__(self, provider='offline-fallback', model='local', available=True, models=None):
        self.provider = provider
        self.model = model
        self.available = available
        self.models = models or []


class LocalModel:
    def __init__(self, provider='offline', model='llama3.2', host=None):
        self.provider = provider or 'offline'
        self.model = model or 'llama3.2'
        self.host = (host or os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')).strip()
        if not self.host.startswith(('http://', 'https://')):
            self.host = 'http://' + self.host

    def _tags(self, timeout=1.5):
        return request_json(self.host.rstrip('/') + '/api/tags', timeout=timeout, retries=0)

    def status(self):
        if self.provider == 'ollama':
            models = self.list_models()
            return ModelStatus('ollama', self.model, bool(models) or self._reachable(), models)
        return ModelStatus('offline-fallback', 'local', True, ['offline-fallback'])

    def _reachable(self):
        try:
            self._tags(1.2)
            return True
        except HttpError:
            return False

    def test_connection(self):
        if self.provider != 'ollama':
            return {'ok': True, 'message': 'Offline fallback is ready.'}
        try:
            models = [m.get('name') for m in self._tags().get('models', []) if m.get('name')]
        except HttpError as exc:
            return {'ok': False, 'message': f'Ollama connection failed: {exc}'}
        if self.model and self.model not in models and models:
            return {'ok': False, 'message': f'Ollama connected, but model "{self.model}" is not installed. Run: ollama pull {self.model}', 'models': models}
        return {'ok': True, 'message': f'Ollama connected • {len(models)} model(s) available.', 'models': models}

    def list_models(self):
        try:
            return [m.get('name') for m in self._tags().get('models', []) if m.get('name')]
        except HttpError:
            return []
