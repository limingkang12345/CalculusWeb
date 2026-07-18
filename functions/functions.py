from sympy import diff, solveset, Rel, symbols, maximum, minimum, Interval, Intersection, oo, imageset, Lambda, periodicity, simplify, radsimp
from sympy.calculus.util import function_range
from core.sympify import sympify


def frange(f, s, d, is_increase, fs):
    return function_range(sympify(f, fs), symbols(s), domain=sympify(d, fs))


def monotonic_interval(f, s, d, is_increase, fs):
    return solveset(Rel(diff(sympify(f, fs)), 0, ">"), symbols(s), domain=sympify(d, fs)) if is_increase \
        else solveset(Rel(diff(sympify(f, fs)), 0, "<"), symbols(s), domain=sympify(d, fs))


def odd_or_even(f, s, d, arg, fs):
    if Intersection(Interval.open(-oo, 0), sympify(d, fs)).symmetric_difference(
        imageset(Lambda(sympify(s, fs), -sympify(s, fs)), Intersection(Interval.open(0, oo), sympify(d, fs)))).is_empty:
        if sympify(f, fs).equals(0):
            return "既奇又偶函数"
        elif sympify(f, fs).equals(-(sympify(f, fs).subs(symbols(s), -symbols(s)))):
            return "奇函数"
        elif sympify(f, fs).equals(sympify(f, fs).subs(symbols(s), -symbols(s))):
            return "偶函数"
        else:
            return "非奇非偶函数"
    else:
        return "非奇非偶函数"


def period(f, s, d, arg, fs):
    p = periodicity(sympify(f, fs), symbols(s))
    try:
        if sympify(d, fs).sup == oo:
            return p if p is not None else "该函数无周期"
        elif sympify(d, fs).sup != oo and sympify(d, fs) == -oo:
            return -p if p is not None else "该函数无周期"
        else:
            return "该函数无周期"
    except Exception:
        return "该函数无周期"


def mvalues(f, s, d, is_max, fs):
    return maximum(sympify(f, fs), symbols(s), domain=sympify(d, fs)) if is_max \
        else minimum(sympify(f, fs), symbols(s), domain=sympify(d, fs))


def get_function_attr(f, s, d, attr, fs):
    attrs = [[frange, None], [monotonic_interval, True], [monotonic_interval, False], [odd_or_even, None],
        [period, None], [mvalues, True], [mvalues, False]]

    return simplify(attrs[attr - 1][0](f, s, d, attrs[attr - 1][1], fs)) if attr != 0 else (radsimp(sympify(f, fs)), sympify(d, fs))
