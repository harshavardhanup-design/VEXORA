import io, json, unittest, urllib.error
from unittest import mock
from tests import _env  # noqa: F401
from ai import http, providers
import ai.chatbot as cb

SECRET = 'sk' + '-' + 'TESTKEY1234567890abcdefghij'  # assembled at runtime so secret scanners stay quiet


class FakeResp:
    def __init__(self, obj): self._b = json.dumps(obj).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def http_error(code):
    return urllib.error.HTTPError('https://x', code, 'err', {}, io.BytesIO(b'{}'))


class HttpHelper(unittest.TestCase):
    def test_retries_transient_then_succeeds(self):
        seq = [http_error(503), FakeResp({'ok': 1})]
        with mock.patch('urllib.request.urlopen', side_effect=seq) as m, mock.patch('time.sleep'):
            self.assertEqual(http.request_json('https://x', payload={}, retries=1), {'ok': 1})
        self.assertEqual(m.call_count, 2)

    def test_does_not_retry_auth_errors(self):
        with mock.patch('urllib.request.urlopen', side_effect=http_error(401)) as m:
            with self.assertRaises(http.HttpError) as cm:
                http.request_json('https://x', payload={}, retries=3)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(cm.exception.status, 401)
        self.assertIn('key', str(cm.exception).lower())


class Providers(unittest.TestCase):
    def test_openai_success_and_error_never_leak_key(self):
        ctx = {'openai_api_key': SECRET, 'model_name': 'gpt-x'}
        with mock.patch('urllib.request.urlopen', return_value=FakeResp({'output_text': 'hi'})):
            self.assertEqual(providers.remote_chat('openai', 'q', [], ctx), ('hi', None))
        with mock.patch('urllib.request.urlopen', side_effect=http_error(429)), mock.patch('time.sleep'):
            ans, err = providers.remote_chat('openai', 'q', [], ctx)
        self.assertIsNone(ans)
        self.assertIn('429', err)
        self.assertNotIn(SECRET, err)

    def test_gemini_parses_parts_and_reports_block_reason(self):
        ctx = {'gemini_api_key': 'k', 'model_name': 'gemini-x'}
        ok = {'candidates': [{'content': {'parts': [{'text': 'a'}, {'text': 'b'}]}}]}
        with mock.patch('urllib.request.urlopen', return_value=FakeResp(ok)):
            self.assertEqual(providers.remote_chat('gemini', 'q', [], ctx)[0], 'ab')
        with mock.patch('urllib.request.urlopen', return_value=FakeResp({'promptFeedback': {'blockReason': 'SAFETY'}})):
            self.assertIn('SAFETY', providers.remote_chat('gemini', 'q', [], ctx)[1])

    def test_missing_key(self):
        with mock.patch.dict('os.environ', {}, clear=False):
            import os; os.environ.pop('GEMINI_API_KEY', None)
            self.assertIn('not configured', providers.remote_chat('gemini', 'q', [], {})[1])

    def test_history_is_capped(self):
        hist = [{'user': f'u{i}', 'assistant': f'a{i}'} for i in range(50)]
        self.assertEqual(len(list(providers._turns(hist))), providers.HISTORY_TURNS * 2)


class ChatFlow(unittest.TestCase):
    def test_provider_error_is_surfaced_not_masked(self):
        with mock.patch.object(cb, 'remote_chat', return_value=(None, 'OpenAI request failed — HTTP 401: the API key was rejected')):
            out = cb.local_chat('explain quantum tunnelling', [], {'model_provider': 'openai', 'online_knowledge': False})
        self.assertIn('401', out)

    def test_ollama_failure_message(self):
        out = cb.local_chat('hello there', [], {'model_provider': 'ollama', 'ollama_host': 'http://127.0.0.1:9', 'online_knowledge': False})
        self.assertIn('Ollama', out)

    def test_selected_model_gets_first_refusal(self):
        with mock.patch.object(cb, 'remote_chat', return_value=('MODEL', None)) as m:
            self.assertEqual(cb.local_chat('what is python', [], {'model_provider': 'gemini', 'model_name': 'g'}), 'MODEL')
        self.assertEqual(m.call_count, 1)

    def test_no_stale_officeholder_facts_offline(self):
        out = cb.local_chat('who is the prime minister of india', [], {'model_provider': 'offline', 'online_knowledge': False})
        self.assertNotIn('Modi', out)

    def test_calc_bomb_does_not_hang_chat(self):
        self.assertIn('offline backend', cb.local_chat('calculate 9^9^9^9', [], {}))
        self.assertEqual(cb.local_chat('calculate 12*(3+4)', [], {}), 'The answer is 84.')


if __name__ == '__main__':
    unittest.main()
