import time, unittest
from tests import _env  # noqa: F401
from ai.safe_math import safe_calc


class SafeCalc(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(safe_calc('2+2'), 4)
        self.assertEqual(safe_calc('(1+2)*3'), 9)
        self.assertEqual(safe_calc('2^10'), 1024)
        self.assertEqual(safe_calc('7 % 3'), 1)
        self.assertEqual(safe_calc('6 ÷ 3 × 2'), 4)

    def test_rejects_non_arithmetic(self):
        for bad in ['__import__("os")', 'abs(-1)', '[1]', 'a+1', '"x"*5', 'True+1', '', None]:
            self.assertIsNone(safe_calc(bad), bad)

    def test_pow_bombs_return_instantly(self):
        # Previously hung the worker thread indefinitely.
        for bomb in ['9**9**9', '9^9^9^9', '10**100000', '2**(10**9)', '99999999999**99999']:
            t = time.perf_counter()
            self.assertIsNone(safe_calc(bomb), bomb)
            self.assertLess(time.perf_counter() - t, 0.5, bomb)

    def test_errors_are_none_not_exceptions(self):
        self.assertIsNone(safe_calc('1/0'))
        self.assertIsNone(safe_calc('1e308*10'))
        self.assertIsNone(safe_calc('1+' * 200 + '1'))


if __name__ == '__main__':
    unittest.main()
