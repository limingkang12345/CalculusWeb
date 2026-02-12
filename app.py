from flask import Flask, render_template, request, jsonify
from derivative import derivative, yinhanshu_derivative
from integral import integral
from simplification import simplifies
from sympy import sympify, latex

app = Flask(__name__)

# ---------- 首页 ----------
@app.route('/')
def index():
    return render_template('index.html')

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

    try:
        if is_implicit:
            # 隐函数求导
            if is_specific and x_val:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, x_val)
                result_value = yinhanshu_derivative(expr, var, y_var, order, x_val)  # 隐函数具体值
            else:
                result_deriv = yinhanshu_derivative(expr, var, y_var, order, None)
                result_value = None
        else:
            # 显函数求导
            if is_specific and x_val:
                result_deriv = derivative(expr, var, order, None)
                result_value = derivative(expr, var, order, x_val)
            else:
                result_deriv = derivative(expr, var, order, None)
                result_value = None

        # 原函数LaTeX（用于输入框实时显示）
        original_latex = latex(sympify(expr))

        return jsonify({
            'success': True,
            'original': original_latex,
            'derivative': result_deriv,
            'derivative_value': result_value
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

    try:
        if is_definite and lower and upper:
            result_integral = integral(expr, var, lower, upper)
            result_antiderivative = integral(expr, var)  # 原函数（不定积分）
        else:
            result_integral = None
            result_antiderivative = integral(expr, var)

        original_latex = latex(sympify(expr))

        return jsonify({
            'success': True,
            'original': original_latex,
            'antiderivative': result_antiderivative,
            'definite_value': result_integral
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------- 变形 API ----------
@app.route('/api/simplify', methods=['POST'])
def api_simplify():
    data = request.get_json()
    expr = data.get('expr', '')
    method_index = data.get('method_index', 0)  # 对应原Qt ComboBox的currentIndex

    try:
        result_expr = simplifies(expr, method_index)
        result_latex = latex(result_expr)
        result_str = str(result_expr)
        original_latex = latex(sympify(expr))

        return jsonify({
            'success': True,
            'original': original_latex,
            'simplified': result_latex,
            'simplified_str': result_str
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)