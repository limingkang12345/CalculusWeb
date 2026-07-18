from sympy import diff, idiff, solve, Eq, radsimp
from core.sympify import sympify


def derivative(f, v, n, x, fs):
    if x is None:
        return radsimp(diff(sympify(f, fs), sympify(v, fs), int(n)))
    else:
        return radsimp(diff(sympify(f, fs), sympify(v, fs), int(n)).subs(sympify(v, fs), sympify(x, fs)))


def yinhanshu_derivative(f, v1, v2, n, x, fs):
    if x is None:
        return radsimp(idiff(sympify(f, fs), sympify(v2, fs), sympify(v1, fs), int(n)))
    else:
        return radsimp(idiff(sympify(f, fs), sympify(v2, fs), sympify(v1, fs), int(n)).subs(sympify(v1, fs), sympify(x, fs)).subs(sympify(v2, fs),
            solve(Eq(sympify(f, fs).subs(sympify(v1, fs), sympify(x, fs)), 0), sympify(v2, fs))[0]))
