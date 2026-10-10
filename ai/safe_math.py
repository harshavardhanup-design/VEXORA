"""Bounded arithmetic evaluator.

The previous evaluator whitelisted AST node types but still evaluated
``9**9**9`` -- Python happily tries to compute it, hanging the worker thread
(and eventually exhausting memory) *before* any result check runs. This version
validates operand magnitude and exponent size while walking the tree, so
nothing expensive is ever executed.
"""
from __future__ import annotations
import ast, math, operator

MAX_EXPR_LEN = 200
MAX_NODES = 60
MAX_ABS = 1e100
MAX_EXPONENT = 1000

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class CalcError(ValueError):
    pass


def _check(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalcError('unsupported value')
    if isinstance(value, float) and not math.isfinite(value):
        raise CalcError('non-finite result')
    if abs(value) > MAX_ABS:
        raise CalcError('result too large')
    return value


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        return _check(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _check(_UNARY[type(node.op)](_eval(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise CalcError('exponent too large')
            if isinstance(left, int) and isinstance(right, int) and right > 0 \
                    and abs(left) > 1 and right * math.log10(abs(left)) > 100:
                raise CalcError('result too large')
        try:
            return _check(_BIN[type(node.op)](left, right))
        except ZeroDivisionError:
            raise CalcError('division by zero')
        except OverflowError:
            raise CalcError('overflow')
    raise CalcError('unsupported expression')


def safe_calc(expr: str):
    """Return a number, or ``None`` if the expression is invalid or unsafe."""
    expr = str(expr or '').replace('×', '*').replace('÷', '/').replace('^', '**').strip()
    if not expr or len(expr) > MAX_EXPR_LEN:
        return None
    try:
        tree = ast.parse(expr, mode='eval')
        if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
            return None
        return _eval(tree)
    except (CalcError, SyntaxError, ValueError, RecursionError, MemoryError):
        return None
