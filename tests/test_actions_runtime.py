import sys, types, unittest
from dataclasses import replace
from unittest import mock
from tests import _env  # noqa: F401
from agent.runtime import AgentRuntime
from tools import action_engine as ae


class Engine(unittest.TestCase):
    def test_unknown_action_rejected(self):
        r = ae.execute('rm -rf /', approved=True)
        self.assertFalse(r.ok)
        self.assertIn('allowlist', r.message)

    def test_approval_required(self):
        for a in ['calculator', 'downloads', 'browser', 'windows_settings']:
            r = ae.execute(a, approved=False)
            self.assertTrue(r.requires_confirmation and not r.ok, a)

    def test_shell_is_never_used(self):
        with mock.patch('subprocess.Popen') as p:
            ae.execute('notepad', approved=True)
        self.assertIs(p.call_args.kwargs.get('shell'), False)

    def test_windows_stub_aliases(self):
        self.assertIn('calculatorapp.exe', ae.PROCESS_ALIASES['calc.exe'])

    def test_input_allowlists(self):
        fake = types.SimpleNamespace(write=mock.Mock(), press=mock.Mock(), hotkey=mock.Mock(), click=mock.Mock())
        with mock.patch.dict(sys.modules, {'pyautogui': fake}):
            self.assertFalse(ae.guarded_input('hotkey', 'alt+f4', approved=True).ok)   # destructive: removed
            self.assertFalse(ae.guarded_input('press_key', 'delete', approved=True).ok)
            self.assertFalse(ae.guarded_input('click', '-1,5', approved=True).ok)
            self.assertFalse(ae.guarded_input('type_text', 'x' * 2001, approved=True).ok)
            self.assertTrue(ae.guarded_input('hotkey', 'ctrl+c', approved=True).ok)
            self.assertFalse(ae.guarded_input('hotkey', 'ctrl+c', approved=False).ok)
        fake.hotkey.assert_called_once_with('ctrl', 'c')

    def test_plan_order_and_dedupe(self):
        acts = [s['action'] for s in ae.plan_for_goal('open notepad, open calculator and open notepad')]
        self.assertEqual(sorted(acts), ['calculator', 'notepad'])


def result(**kw):
    return ae.ActionResult(**{'ok': True, 'action': 'calculator', 'message': 'm', 'verified': False, **kw})


class Runtime(unittest.TestCase):
    def test_requires_approval(self):
        ex = mock.Mock()
        r = AgentRuntime().run('open calculator', approved=False, executor=ex)
        self.assertEqual(r.state, 'ASK_PERMISSION')
        ex.assert_not_called()

    def test_recovery_reverifies_and_does_not_relaunch(self):
        ex = mock.Mock(return_value=result(verified=False))
        r = AgentRuntime(max_retries=2).run('open calculator', approved=True, executor=ex, verifier=lambda res: True)
        self.assertEqual(r.state, 'COMPLETE')
        self.assertEqual(ex.call_count, 1, 'a retry must never launch a second window')
        self.assertEqual(r.recovery_count, 1)

    def test_fails_when_never_verified(self):
        ex = mock.Mock(return_value=result(verified=False))
        r = AgentRuntime(max_retries=1).run('open calculator', approved=True, executor=ex, verifier=lambda res: False)
        self.assertEqual(r.state, 'FAILED')
        self.assertEqual(ex.call_count, 1)

    def test_no_matching_action(self):
        self.assertEqual(AgentRuntime().run('tell me a joke', approved=True, executor=mock.Mock()).state, 'FAILED')


if __name__ == '__main__':
    unittest.main()
