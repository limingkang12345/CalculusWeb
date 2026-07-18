from sympy import integrate, radsimp
from core.sympify import sympify


def integral(f, v, fs, a=None, b=None):
    if a is None and b is None:
        return radsimp(integrate(sympify(f, fs), sympify(v, fs)))
    else:
        return radsimp(integrate(sympify(f, fs), (sympify(v, fs), sympify(a, fs), sympify(b, fs))))
