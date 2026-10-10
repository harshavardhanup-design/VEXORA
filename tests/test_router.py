import unittest
from tests import _env  # noqa: F401
from agent.command_router import handle_result
from security.permissions import Risk, is_protected_request, requires_approval, risk_of


def intent(q):
    return handle_result(q).plan['intent']


class Routing(unittest.TestCase):
    def test_regression_substring_hijacking(self):
        # These were routed to RAM / process / capabilities handlers by substring matching.
        for q in ['write a program to sort a list', 'what is a framework', 'help me write a poem',
                  'my processor is fast, explain caching', 'what is ram', 'tell me about desktop publishing',
                  'how do I delete a file in python']:
            self.assertEqual(intent(q), 'General request', q)
            self.assertEqual(handle_result(q).text, '')

    def test_tool_intents(self):
        table = {
            'recent files': 'Inspect recent work',
            'which app is using my ram': 'Inspect RAM usage',
            'show running apps': 'Inspect running processes',
            'how is my pc': 'Diagnose PC health',
            'my pc is slow': 'Diagnose PC health',
            'what is on my screen': 'Inspect current screen context',
            'pc specs': 'Inspect system specifications',
            'open windows settings': 'Open Windows Settings',
            'help': 'Explain capabilities',
        }
        for q, want in table.items():
            self.assertEqual(intent(q), want, q)

    def test_diagnose_performance_reaches_performance_handler(self):
        # Previously shadowed by the broader health rule ('diagnos' substring).
        self.assertEqual(intent('diagnose performance'), 'Analyze PC performance')

    def test_launchers(self):
        for q, action in [('open calculator', 'calculator'), ('please open the downloads folder', 'downloads'),
                          ('launch notepad', 'notepad'), ('start my browser', 'browser')]:
            r = handle_result(q)
            self.assertEqual((r.plan['tool'], r.plan['action']), ('safe_app_launcher', action), q)

    def test_plan_carries_steps(self):
        r = handle_result('plan opening calculator and notepad, do this for me')
        self.assertEqual([s['action'] for s in r.plan['steps']], ['calculator', 'notepad'])

    def test_protected_requests_require_confirmation(self):
        for q in ['please delete my downloads', 'shutdown', 'could you restart the pc', 'rename file report.docx']:
            self.assertTrue(handle_result(q).requires_confirmation, q)
        self.assertFalse(handle_result('how do i restart my router').requires_confirmation)


class Permissions(unittest.TestCase):
    def test_fail_closed_for_unknown_actions(self):
        self.assertIs(risk_of('format_disk'), Risk.MODIFY)
        self.assertTrue(requires_approval('format_disk', require_confirmation=False))

    def test_input_always_needs_approval(self):
        self.assertTrue(requires_approval('click', require_confirmation=False))

    def test_launch_follows_setting(self):
        self.assertFalse(requires_approval('calculator', require_confirmation=False))
        self.assertTrue(requires_approval('calculator', require_confirmation=True))

    def test_protected_pattern_is_anchored(self):
        self.assertFalse(is_protected_request('what happens if I delete system32'))


if __name__ == '__main__':
    unittest.main()
