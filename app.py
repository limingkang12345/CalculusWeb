from flask import Flask, render_template, request, jsonify, session
from derivative import derivative, yinhanshu_derivative
from integral import integral
from simplification import simplifies
from solvers import solve_fangcheng, solve_weifenfangcheng, solve_fangchengzu, solve_budengshi, solve_budengshizu
from functions import get_function_attr
from sympy import latex, Eq, Rel, symbols, Symbol
from sympify import sympify

app = Flask(__name__)
# app.secret_key = 'your-secret-key-here'  # 用于session，可选

@app.route('/api/latex', methods=['POST'])
def api_latex():
    data = request.get_json()
    expr = data.get('expr', '')
    fs = extract_fs(data)
    try:
        result_latex = latex(sympify(expr, fs))
        return jsonify({'success': True, 'latex': result_latex})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 首页 ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- 通用函数：从请求中提取 fs ----------
def extract_fs(data):
    """从JSON中提取函数字典 fs，格式与Qt一致"""
    fs_raw = data.get('fs', {})
    fs = {}
    for name, info in fs_raw.items():
        # info 预期为 [名称, 表达式, 定义域, 自变量]
        fs[name] = info
    return fs

# ---------- 求导 API ----------
@app.route('/api/derivative', methods=['POST'])
def api_derivative():
    data = request.get_json()
    expr = data.get('expr', '')
    var = data.get('var', 'x')
    order = data.get('order', '1')
    is_implicit = data.get('is_implicit', False)
    y_var = data.get('y_var', 'y')
    is_specific = data.get('is_specific', False)
    x_val = data.get('x_val', None)
    fs = extract_fs(data)

    try:
        if is_implicit:
            if is_specific and x_val:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, x_val, fs)
                result_value = yinhanshu_derivative(expr, var, y_var, order, x_val, fs)
            else:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, None, fs)
                result_value = None
        else:
            if is_specific and x_val:
                result_deriv = derivative(expr, var, order, None, fs)
                result_value = derivative(expr, var, order, x_val, fs)
            else:
                result_deriv = derivative(expr, var, order, None, fs)
                result_value = None

        original_latex = latex(sympify(expr, fs))
        return jsonify({
            'success': True,
            'original': original_latex,
            'derivative': latex(result_deriv) if result_deriv is not None else '',
            'derivative_value': latex(result_value) if result_value is not None else '',
            'derivative_str': str(result_deriv) if result_deriv is not None else '',
            'derivative_value_str': str(result_value) if result_value is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 积分 API ----------
@app.route('/api/integral', methods=['POST'])
def api_integral():
    data = request.get_json()
    expr = data.get('expr', '')
    var = data.get('var', 'x')
    is_definite = data.get('is_definite', False)
    lower = data.get('lower', None)
    upper = data.get('upper', None)
    fs = extract_fs(data)

    try:
        if is_definite and lower and upper:
            result_integral = integral(expr, var, fs, lower, upper)
            result_antiderivative = integral(expr, var, fs)
        else:
            result_integral = None
            result_antiderivative = integral(expr, var, fs)

        original_latex = latex(sympify(expr, fs))
        return jsonify({
            'success': True,
            'original': original_latex,
            'antiderivative': latex(result_antiderivative) if result_antiderivative is not None else '',
            'definite_value': latex(result_integral) if result_integral is not None else '',
            'antiderivative_str': str(result_antiderivative) if result_antiderivative is not None else '',
            'definite_value_str': str(result_integral) if result_integral is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 变形 API ----------
@app.route('/api/simplify', methods=['POST'])
def api_simplify():
    data = request.get_json()
    expr = data.get('expr', '')
    method_index = data.get('method_index', 0)
    zhuyuan = data.get('zhuyuan', None)
    huanyuan = data.get('huanyuan', None)
    huanyuanshi = data.get('huanyuanshi', None)
    fs = extract_fs(data)

    try:
        result_expr = simplifies(expr, method_index, zhuyuan, huanyuan, huanyuanshi, fs)
        original_latex = latex(sympify(expr, fs))
        return jsonify({
            'success': True,
            'original': original_latex,
            'simplified': latex(result_expr) if result_expr is not None else '',
            'simplified_str': str(result_expr) if result_expr is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 方程求解 API（含微分方程）----------
@app.route('/api/equation', methods=['POST'])
def api_equation():
    data = request.get_json()
    lhs = data.get('lhs', '')
    rhs = data.get('rhs', '0')
    var = data.get('var', 'x')
    domain = data.get('domain', 'Reals')
    is_ode = data.get('is_ode', False)  # 是否微分方程
    fs = extract_fs(data)

    try:
        if is_ode:
            # 微分方程：不使用fs，变量为 f(x)
            eq = Eq(sympify(lhs, {}), sympify(rhs, {}))
            solution = solve_weifenfangcheng(eq, var, {})
            original_latex = latex(eq)
        else:
            eq = Eq(sympify(lhs, fs), sympify(rhs, fs))
            solution = solve_fangcheng(eq, var, domain, fs)
            original_latex = latex(eq) + f'\\quad (x\\in {latex(sympify(domain, fs))})'

        return jsonify({
            'success': True,
            'original': original_latex,
            'solution': latex(solution) if solution is not None else '',
            'solution_str': str(solution) if solution is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 方程组求解 API ----------
@app.route('/api/equationsystem', methods=['POST'])
def api_equationsystem():
    data = request.get_json()
    eqs_raw = data.get('equations', [])  # 列表，每个元素为 [lhs, rhs] 字符串
    vars_raw = data.get('variables', 'x,y')  # 逗号分隔的变量字符串
    fs = extract_fs(data)

    try:
        # 构造方程列表
        eqs = []
        for lhs, rhs in eqs_raw:
            eqs.append(Eq(sympify(lhs, fs), sympify(rhs, fs)))
        # 变量列表
        vars_list = [Symbol(v.strip()) for v in vars_raw.split(',') if v.strip()]
        solution = solve_fangchengzu(eqs, vars_list, fs)
        # 处理无解情况
        if solution == []:
            solution = "无解"
        elif isinstance(solution, dict):
            # 转换为LaTeX格式，如 {x: 1, y: 2}
            sol_latex = ', '.join([f'{latex(k)} = {latex(v)}' for k, v in solution.items()])
            solution = sol_latex
        else:
            solution = latex(solution)
        return jsonify({'success': True, 'solution': solution})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 不等式求解 API ----------
@app.route('/api/inequality', methods=['POST'])
def api_inequality():
    data = request.get_json()
    lhs = data.get('lhs', '')
    rhs = data.get('rhs', '0')
    rel = data.get('rel', '!=')
    var = data.get('var', 'x')
    domain = data.get('domain', 'Reals')
    fs = extract_fs(data)

    try:
        relation = Rel(sympify(lhs, fs), sympify(rhs, fs), rel)
        solution = solve_budengshi(relation, var, domain, fs)
        original_latex = latex(relation) + f'\\quad (x\\in {latex(sympify(domain, fs))})'
        return jsonify({
            'success': True,
            'original': original_latex,
            'solution': latex(solution) if solution is not None else '',
            'solution_str': str(solution) if solution is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 不等式组求解 API ----------
@app.route('/api/inequalitysystem', methods=['POST'])
def api_inequalitysystem():
    data = request.get_json()
    ineqs_raw = data.get('inequalities', [])  # 列表，每个元素为 [lhs, rhs, rel]
    var = data.get('variable', 'x')
    fs = extract_fs(data)

    try:
        rels = []
        for lhs, rhs, rel in ineqs_raw:
            rels.append(Rel(sympify(lhs, fs), sympify(rhs, fs), rel))
        solution = solve_budengshizu(rels, Symbol(var), fs)
        if solution is False or solution is None:
            solution = "无解"
        else:
            solution = latex(solution)
        return jsonify({'success': True, 'solution': solution})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 函数属性 API（定义页）----------
@app.route('/api/function', methods=['POST'])
def api_function():
    data = request.get_json()
    action = data.get('action')

    if action == 'get_attr':
        expr = data.get('expr', '')
        var = data.get('var', 'x')
        domain = data.get('domain', 'Reals')
        attr_index = data.get('attr_index', 0)
        fs = extract_fs(data)

        try:
            result = get_function_attr(expr, var, domain, attr_index, fs)
            if attr_index == 0:
                expr_sym, domain_sym = result
                result_latex = latex(expr_sym) + f'\\quad ({var}\\in {latex(domain_sym)})'
                result_str = str(expr_sym)
            else:
                result_latex = latex(result)
                result_str = str(result)
            return jsonify({'success': True, 'latex': result_latex, 'str': result_str})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    elif action == 'evaluate':
        expr = data.get('expr', '')
        var = data.get('var', 'x')
        val = data.get('val', '0')
        fs = extract_fs(data)

        try:
            f = sympify(expr, fs)
            value = f.subs(symbols(var), sympify(val, fs))
            return jsonify({'success': True, 'latex': latex(value), 'str': str(value)})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    else:
        return jsonify({'success': False, 'error': '未知动作'})

if __name__ == '__main__':
    app.run(debug=False)