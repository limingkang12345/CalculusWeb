from flask import Flask, render_template, request, jsonify
from derivative import derivative, yinhanshu_derivative
from integral import integral
from simplification import simplifies
from solvers import solve_fangcheng, solve_budengshi
from functions import get_function_attr
from sympy import sympify, latex, Eq, Rel, symbols

app = Flask(__name__)

# ---------- 首页 ----------
@app.route('/')
def index():
    return render_template('index.html')

# ---------- 求导 API (同前) ----------
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

    try:
        if is_implicit:
            if is_specific and x_val:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, x_val)
                result_value = yinhanshu_derivative(expr, var, y_var, order, x_val)
            else:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, None)
                result_value = None
        else:
            if is_specific and x_val:
                result_deriv = derivative(expr, var, order, None)
                result_value = derivative(expr, var, order, x_val)
            else:
                result_deriv = derivative(expr, var, order, None)
                result_value = None

        original_latex = latex(sympify(expr))
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

# ---------- 积分 API (同前) ----------
@app.route('/api/integral', methods=['POST'])
def api_integral():
    data = request.get_json()
    expr = data.get('expr', '')
    var = data.get('var', 'x')
    is_definite = data.get('is_definite', False)
    lower = data.get('lower', None)
    upper = data.get('upper', None)

    try:
        if is_definite and lower and upper:
            result_integral = integral(expr, var, lower, upper)
            result_antiderivative = integral(expr, var)
        else:
            result_integral = None
            result_antiderivative = integral(expr, var)

        original_latex = latex(sympify(expr))
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

# ---------- 变形 API (同前) ----------
@app.route('/api/simplify', methods=['POST'])
def api_simplify():
    data = request.get_json()
    expr = data.get('expr', '')
    method_index = data.get('method_index', 0)
    zhuyuan = data.get('zhuyuan', None)
    huanyuan = data.get('huanyuan', None)
    huanyuanshi = data.get('huanyuanshi', None)

    try:
        result_expr = simplifies(expr, method_index, zhuyuan, huanyuan, huanyuanshi)
        original_latex = latex(sympify(expr))
        return jsonify({
            'success': True,
            'original': original_latex,
            'simplified': latex(result_expr) if result_expr is not None else '',
            'simplified_str': str(result_expr) if result_expr is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 方程求解 API (同前) ----------
@app.route('/api/equation', methods=['POST'])
def api_equation():
    data = request.get_json()
    lhs = data.get('lhs', '')
    rhs = data.get('rhs', '0')
    var = data.get('var', 'x')
    domain = data.get('domain', 'Reals')

    try:
        eq = Eq(sympify(lhs), sympify(rhs))
        solution = solve_fangcheng(eq, var, domain)
        original_latex = latex(eq) + f'\\quad (x\\in {latex(sympify(domain))})'
        return jsonify({
            'success': True,
            'original': original_latex,
            'solution': latex(solution) if solution is not None else '',
            'solution_str': str(solution) if solution is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 不等式求解 API (同前) ----------
@app.route('/api/inequality', methods=['POST'])
def api_inequality():
    data = request.get_json()
    lhs = data.get('lhs', '')
    rhs = data.get('rhs', '0')
    rel = data.get('rel', '!=')
    var = data.get('var', 'x')
    domain = data.get('domain', 'Reals')

    try:
        relation = Rel(sympify(lhs), sympify(rhs), rel)
        solution = solve_budengshi(relation, var, domain)
        original_latex = latex(relation) + f'\\quad (x\\in {latex(sympify(domain))})'
        return jsonify({
            'success': True,
            'original': original_latex,
            'solution': latex(solution) if solution is not None else '',
            'solution_str': str(solution) if solution is not None else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========== 新增：函数属性 & 求值 API ==========
@app.route('/api/function', methods=['POST'])
def api_function():
    data = request.get_json()
    action = data.get('action')  # 'get_attr' 或 'evaluate'

    if action == 'get_attr':
        # 获取函数属性
        expr = data.get('expr', '')
        var = data.get('var', 'x')
        domain = data.get('domain', 'Reals')
        attr_index = data.get('attr_index', 0)  # 0~7

        try:
            # get_function_attr 返回 sympy 对象
            result = get_function_attr(expr, var, domain, attr_index)
            if attr_index == 0:
                # 特殊处理：返回 (函数表达式, 定义域) 的元组
                # result 是 (expr_sym, domain_sym)
                expr_sym, domain_sym = result
                result_latex = latex(expr_sym) + f'\\quad ({var}\\in {latex(domain_sym)})'
                result_str = str(expr_sym)
            else:
                result_latex = latex(result)
                result_str = str(result)
            return jsonify({
                'success': True,
                'latex': result_latex,
                'str': result_str
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    elif action == 'evaluate':
        # 求函数值
        expr = data.get('expr', '')
        var = data.get('var', 'x')
        val = data.get('val', '0')
        try:
            f = sympify(expr)
            value = f.subs(symbols(var), sympify(val))
            return jsonify({
                'success': True,
                'latex': latex(value),
                'str': str(value)
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    else:
        return jsonify({'success': False, 'error': '未知动作'})

if __name__ == '__main__':
    app.run(debug=False)   # 生产环境务必关闭debug