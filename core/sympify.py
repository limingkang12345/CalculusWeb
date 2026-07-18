import re
from sympy import sympify as sympify_sympy
from sympy import Symbol, simplify, radsimp
from sympy.core.sympify import SympifyError
from latex2sympy2 import latex2sympy


def _preprocess_func_calls(expr_str, fs):
    """预处理函数调用表达式，将 f(arg) 形式替换为函数体表达式"""
    if not fs:
        return expr_str

    func_names = sorted(fs.keys(), key=len, reverse=True)
    result = expr_str

    while True:
        best_pos = len(result)
        best_func = None
        for func_name in func_names:
            match = re.search(r'\b' + re.escape(func_name) + r'\(', result)
            pos = match.start() if match else -1
            if pos != -1 and pos < best_pos:
                best_pos = pos
                best_func = func_name

        if best_func is None:
            break

        start_arg = best_pos + len(best_func) + 1
        depth = 1
        end_arg = start_arg
        while depth > 0 and end_arg < len(result):
            if result[end_arg] == '(':
                depth += 1
            elif result[end_arg] == ')':
                depth -= 1
            end_arg += 1

        if depth != 0:
            break

        arg_str = result[start_arg:end_arg - 1]
        var_name = fs[best_func][3]
        body_str = fs[best_func][1]

        expanded_body = re.sub(r'\b' + re.escape(var_name) + r'\b', f'({arg_str})', body_str)
        replacement = f'({expanded_body})'
        result = result[:best_pos] + replacement + result[end_arg:]

    return result


def sympify(expr, fs, locals=None, is_simplify=False, is_rationalize=False):
    """处理输入的表达式，返回 SymPy 表达式对象或错误字符串"""
    if expr == "":
        return Symbol("", latex="")
    if expr[0] == "$":
        try:
            expr = latex2sympy(expr[1:])
        except Exception:
            try:
                expr = _preprocess_func_calls(expr, fs)
                expr = sympify_sympy(expr)
            except Exception:
                return "不规范的表达式输入"
    else:
        expr = _preprocess_func_calls(expr, fs)
    try:
        origin_expr = sympify_sympy(expr, locals=locals)
    except SympifyError:
        return "不规范的表达式输入"
    for f in fs.keys():
        if Symbol(f) in origin_expr.free_symbols:
            try:
                origin_expr = origin_expr.subs(f, sympify_sympy(fs[f][1], locals=locals))
            except SympifyError:
                return "错误的函数定义"
    result = sympify_sympy(simplify(origin_expr), locals=locals) if is_simplify else sympify_sympy(origin_expr, locals=locals)
    if is_rationalize:
        result = radsimp(result)
    return result
