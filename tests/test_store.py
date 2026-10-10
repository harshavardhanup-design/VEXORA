import json, unittest
from tests import _env
from memory import store


class Store(unittest.TestCase):
    def setUp(self):
        for f in store.APP_DIR.glob('workspace*'):
            f.unlink()

    def test_roundtrip_is_atomic(self):
        store.update_tasks([{'title': 'ship', 'done': False}])
        self.assertEqual(store.load()['tasks'][0]['title'], 'ship')
        self.assertEqual(list(store.APP_DIR.glob('workspace_*.tmp')), [])

    def test_corrupt_file_is_preserved_not_overwritten(self):
        store.APP_DIR.mkdir(parents=True, exist_ok=True)
        store.STORE.write_text('{"tasks": [ {"title": "precious"', encoding='utf-8')  # truncated JSON
        data = store.load()
        self.assertEqual(data['tasks'], [])
        kept = list(store.APP_DIR.glob('workspace.corrupt-*.json'))
        self.assertEqual(len(kept), 1)
        self.assertIn('precious', kept[0].read_text(encoding='utf-8'))
        store.update_tasks([{'title': 'new'}])           # subsequent save must not destroy the backup
        self.assertEqual(len(list(store.APP_DIR.glob('workspace.corrupt-*.json'))), 1)

    def test_bad_shapes_normalised(self):
        store.APP_DIR.mkdir(parents=True, exist_ok=True)
        store.STORE.write_text(json.dumps({'tasks': 'x', 'memory': None, 'settings': 5}), encoding='utf-8')
        d = store.load()
        self.assertEqual((d['tasks'], d['memory']), ([], []))
        self.assertEqual(d['settings']['assistant_name'], 'VEXORA')

    def test_memory_capped_at_20(self):
        for i in range(30):
            store.remember(f'u{i}', f'a{i}')
        self.assertEqual(len(store.load()['memory']), 20)


if __name__ == '__main__':
    unittest.main()
