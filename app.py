import os
import json
import secrets
from flask import Flask, render_template, request, session, jsonify, make_response, send_from_directory

from sympy import latex, Eq, Rel, symbols, Symbol
from sympify import sympify
from derivative import derivative, yinhanshu_derivative
from integral import integral
from simplification import simplifies
from solvers import (
    solve_fangcheng, solve_weifenfangcheng,
    solve_fangchengzu, solve_budengshi, solve_budengshizu
)
from functions import get_function_attr

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))


# ─── 工具函数 ────────────────────────────────────────────────

def get_fs():
    """从session获取函数字典"""
    return session.get('fs', {})


def save_fs(fs):
    """将函数字典存入session"""
    session['fs'] = fs


TABS_NAME = ["首页", "定义", "求导", "积分", "变形", "方程", "方程组", "不等式", "不等式组", "帮助"]


def render_latex(expr, prefix='', suffix=''):
    """将SymPy表达式转为LaTeX HTML片段"""
    try:
        s = f'{prefix}{latex(expr)}{suffix}'
        return s
    except Exception:
        return ''


# ─── 路由 ─────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/define', methods=['GET', 'POST'])
def define():
    fs = get_fs()
    result = None
    result_latex = ''
    error = None

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'save':
            name = request.form.get('name', '').strip()
            expr = request.form.get('expr', '').strip()
            domain = request.form.get('domain', 'Reals').strip()
            var = request.form.get('var', 'x').strip()
            if name:
                fs[name] = [name, expr, domain, var]
                save_fs(fs)

        elif action == 'delete':
            name = request.form.get('name', '').strip()
            if name in fs:
                del fs[name]
                save_fs(fs)

        elif action == 'query_attr':
            name = request.form.get('name', '').strip()
            attr = int(request.form.get('attr', 0))
            if name in fs:
                try:
                    fn = fs[name]
                    function_attr = get_function_attr(fn[1], fn[3], fn[2], attr, fs)
                    result = str(function_attr)
                    if attr == 0:
                        result_latex = render_latex(function_attr[0],
                                                     f'{fn[0]}({fn[3]})=',
                                                     f'\\quad({fn[3]}\\in {latex(function_attr[1])})')
                    else:
                        result_latex = render_latex(function_attr)
                except Exception as e:
                    error = str(e)

        elif action == 'eval':
            name = request.form.get('name', '').strip()
            val = request.form.get('val', '').strip()
            if name in fs:
                try:
                    fn = fs[name]
                    f_val = sympify(fn[1], fs).subs(symbols(fn[3]), sympify(val, fs))
                    result = str(f_val)
                    result_latex = render_latex(f_val, f'{fn[0]}({latex(sympify(val, fs))})=')
                except Exception as e:
                    error = str(e)

    return render_template('define.html', fs=fs, result=result, result_latex=result_latex, error=error)


@app.route('/api/function_info')
def api_function_info():
    """AJAX接口：获取指定函数的详细信息"""
    name = request.args.get('name', '').strip()
    fs = get_fs()
    if name in fs:
        fn = fs[name]
        return jsonify({'found': True, 'name': fn[0], 'expr': fn[1], 'domain': fn[2], 'var': fn[3]})
    return jsonify({'found': False})


@app.route('/api/function_attr')
def api_function_attr():
    """AJAX接口：获取函数属性"""
    name = request.args.get('name', '').strip()
    attr = int(request.args.get('attr', 0))
    fs = get_fs()
    if name in fs:
        try:
            fn = fs[name]
            function_attr = get_function_attr(fn[1], fn[3], fn[2], attr, fs)
            if attr == 0:
                result_latex = render_latex(function_attr[0],
                                             f'{fn[0]}({fn[3]})=',
                                             f'\\quad({fn[3]}\\in {latex(function_attr[1])})')
                result_str = str(function_attr)
            else:
                result_latex = render_latex(function_attr)
                result_str = str(function_attr)
            return jsonify({'success': True, 'result': result_str, 'latex': result_latex})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '函数未定义'})


@app.route('/api/function_eval')
def api_function_eval():
    """AJAX接口：求函数值"""
    name = request.args.get('name', '').strip()
    val = request.args.get('val', '').strip()
    fs = get_fs()
    if name in fs:
        try:
            fn = fs[name]
            f_val = sympify(fn[1], fs).subs(symbols(fn[3]), sympify(val, fs))
            result_latex = render_latex(f_val, f'{fn[0]}({latex(sympify(val, fs))})=')
            return jsonify({'success': True, 'result': str(f_val), 'latex': result_latex})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    return jsonify({'success': False, 'error': '函数未定义'})


@app.route('/derivative', methods=['GET', 'POST'])
def derivative_page():
    fs = get_fs()
    result_derivative = ''
    result_derivative_latex = ''
    result_value = ''
    result_value_latex = ''
    error = None

    if request.method == 'POST':
        expr = request.form.get('expr', '')
        var = request.form.get('var', 'x')
        order = request.form.get('order', '1')
        is_implicit = request.form.get('is_implicit') == 'on'
        is_value = request.form.get('is_value') == 'on'
        dep_var = request.form.get('dep_var', 'y')
        var_val = request.form.get('var_val', '')

        try:
            if is_implicit:
                if is_value and var_val:
                    dif = yinhanshu_derivative(expr, var, dep_var, order, None, fs)
                    result_derivative = str(dif)
                    result_derivative_latex = render_latex(dif, "f'(x)=")
                    dif_val = yinhanshu_derivative(expr, var, dep_var, order, var_val, fs)
                    result_value = str(dif_val)
                    result_value_latex = render_latex(dif_val, f"f'({var_val})=")
                else:
                    dif = yinhanshu_derivative(expr, var, dep_var, order, None, fs)
                    result_derivative = str(dif)
                    result_derivative_latex = render_latex(dif, "f'(x)=")
            else:
                if is_value and var_val:
                    dif = derivative(expr, var, order, None, fs)
                    result_derivative = str(dif)
                    result_derivative_latex = render_latex(dif, "f'(x)=")
                    dif_val = derivative(expr, var, order, var_val, fs)
                    result_value = str(dif_val)
                    result_value_latex = render_latex(dif_val, f"f'({var_val})=")
                else:
                    dif = derivative(expr, var, order, None, fs)
                    result_derivative = str(dif)
                    result_derivative_latex = render_latex(dif, "f'(x)=")
        except Exception as e:
            error = str(e)

    return render_template('derivative.html', fs=fs,
                           result_derivative=result_derivative,
                           result_derivative_latex=result_derivative_latex,
                           result_value=result_value,
                           result_value_latex=result_value_latex,
                           error=error)


@app.route('/integral', methods=['GET', 'POST'])
def integral_page():
    fs = get_fs()
    result_antiderivative = ''
    result_antiderivative_latex = ''
    result_definite = ''
    result_definite_latex = ''
    error = None

    if request.method == 'POST':
        expr = request.form.get('expr', '')
        var = request.form.get('var', 'x')
        is_definite = request.form.get('is_definite') == 'on'
        lower = request.form.get('lower', '')
        upper = request.form.get('upper', '')

        try:
            if is_definite and lower and upper:
                F = integral(expr, var, fs)
                result_antiderivative = str(F)
                result_antiderivative_latex = render_latex(F, 'F(x)=')
                F_def = integral(expr, var, fs, lower, upper)
                result_definite = str(F_def)
                result_definite_latex = render_latex(F_def, 'F(x)=')
            else:
                F = integral(expr, var, fs)
                result_antiderivative = str(F)
                result_antiderivative_latex = render_latex(F, 'F(x)=')
        except Exception as e:
            error = str(e)

    return render_template('integral.html', fs=fs,
                           result_antiderivative=result_antiderivative,
                           result_antiderivative_latex=result_antiderivative_latex,
                           result_definite=result_definite,
                           result_definite_latex=result_definite_latex,
                           error=error)


@app.route('/simplify', methods=['GET', 'POST'])
def simplify_page():
    fs = get_fs()
    result = ''
    result_latex = ''
    error = None

    methods = [
        "通用化简(simplify)", "展开(expand)", "因式分解(factor)",
        "主元(collect)", "通分(cancel)", "分离(apart)",
        "三角变换(trigsimp)", "三角展开(expand_trig)",
        "指数合并(powsimp)", "指数展开(expand_power_exp)",
        "对数展开(expand_log)", "对数合并(logcombine)", "换元"
    ]

    if request.method == 'POST':
        expr = request.form.get('expr', '')
        method = int(request.form.get('method', 0))
        zhuyuan = request.form.get('zhuyuan', '').strip() or None
        huanyuan = request.form.get('huanyuan', '').strip() or None
        huanyuanshi = request.form.get('huanyuanshi', '').strip() or None

        try:
            expr_result = simplifies(expr, method, zhuyuan, huanyuan, huanyuanshi, fs)
            result = str(expr_result)
            result_latex = render_latex(expr_result)
        except Exception as e:
            error = str(e)

    return render_template('simplify.html', fs=fs,
                           result=result, result_latex=result_latex,
                           methods=methods, error=error)


@app.route('/equation', methods=['GET', 'POST'])
def equation_page():
    fs = get_fs()
    result = ''
    result_latex = ''
    error = None

    if request.method == 'POST':
        lhs = request.form.get('lhs', '')
        rhs = request.form.get('rhs', '0')
        var = request.form.get('var', 'x')
        domain = request.form.get('domain', 'Reals')
        is_ode = request.form.get('is_ode') == 'on'

        try:
            if is_ode:
                eq = Eq(sympify(lhs, {}), sympify(rhs, {}))
                sol = solve_weifenfangcheng(eq, 'f(x)', fs)
            else:
                eq = Eq(sympify(lhs, fs), sympify(rhs, fs))
                sol = solve_fangcheng(eq, var, domain, fs)
            result = str(sol)
            result_latex = render_latex(sol)
        except Exception as e:
            error = str(e)

    return render_template('equation.html', fs=fs,
                           result=result, result_latex=result_latex,
                           error=error)


@app.route('/equation_system', methods=['GET', 'POST'])
def equation_system_page():
    fs = get_fs()
    result = ''
    result_latex = ''
    error = None
    eqs = session.get('eqs', {})

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'save':
            lhs = request.form.get('lhs', '')
            rhs = request.form.get('rhs', '0')
            try:
                eq = Eq(sympify(lhs, fs), sympify(rhs, fs))
                key = str(eq)
                if key not in eqs:
                    eqs[key] = [lhs, rhs]
                    session['eqs'] = eqs
            except Exception as e:
                error = str(e)

        elif action == 'delete':
            key = request.form.get('key', '')
            if key in eqs:
                del eqs[key]
                session['eqs'] = eqs

        elif action == 'solve':
            vars_str = request.form.get('vars', 'x,y')
            try:
                sol = solve_fangchengzu(
                    [Eq(sympify(v[0], fs), sympify(v[1], fs)) for v in eqs.values()],
                    [Symbol(s.strip()) for s in vars_str.split(',')],
                    fs
                )
                result = str(sol)
                result_latex = render_latex(sol).replace(':', '=')
            except Exception as e:
                result = '无解'
                error = str(e)

    return render_template('equation_system.html', fs=fs, eqs=eqs,
                           result=result, result_latex=result_latex,
                           error=error)


@app.route('/inequality', methods=['GET', 'POST'])
def inequality_page():
    fs = get_fs()
    result = ''
    result_latex = ''
    error = None

    if request.method == 'POST':
        lhs = request.form.get('lhs', '')
        rhs = request.form.get('rhs', '0')
        rel = request.form.get('rel', '>')
        var = request.form.get('var', 'x')
        domain = request.form.get('domain', 'Reals')

        try:
            rel_obj = Rel(sympify(lhs, fs), sympify(rhs, fs), rel)
            sol = solve_budengshi(rel_obj, var, domain, fs)
            result = str(sol)
            result_latex = render_latex(sol)
        except Exception as e:
            error = str(e)

    return render_template('inequality.html', fs=fs,
                           result=result, result_latex=result_latex,
                           error=error)


@app.route('/inequality_system', methods=['GET', 'POST'])
def inequality_system_page():
    fs = get_fs()
    result = ''
    result_latex = ''
    error = None
    rels = session.get('rels', {})

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'save':
            lhs = request.form.get('lhs', '')
            rhs = request.form.get('rhs', '0')
            rel_sym = request.form.get('rel', '>')
            try:
                rel_obj = Rel(sympify(lhs, fs), sympify(rhs, fs), rel_sym)
                key = str(rel_obj)
                if key not in rels:
                    rels[key] = [lhs, rhs, rel_sym]
                    session['rels'] = rels
            except Exception as e:
                error = str(e)

        elif action == 'delete':
            key = request.form.get('key', '')
            if key in rels:
                del rels[key]
                session['rels'] = rels

        elif action == 'solve':
            var = request.form.get('var', 'x')
            try:
                sol = solve_budengshizu(
                    [Rel(sympify(v[0], fs), sympify(v[1], fs), v[2]) for v in rels.values()],
                    Symbol(var), fs
                )
                if sol:
                    result = str(sol)
                    result_latex = render_latex(sol)
                else:
                    result = '无解'
            except Exception as e:
                result = '无解'
                error = str(e)

    return render_template('inequality_system.html', fs=fs, rels=rels,
                           result=result, result_latex=result_latex,
                           error=error)


@app.route('/help')
def help_page():
    return render_template('help.html')


# ─── 桌面版下载 ──────────────────────────────────────────────

DOWNLOADS_DIR = os.path.join(app.root_path, 'static', 'downloads')


@app.route('/download')
def download_list():
    """列出可下载的桌面版安装文件"""
    files = []
    if os.path.isdir(DOWNLOADS_DIR):
        for f in os.listdir(DOWNLOADS_DIR):
            fp = os.path.join(DOWNLOADS_DIR, f)
            if os.path.isfile(fp):
                size = os.path.getsize(fp)
                files.append({
                    'name': f,
                    'size': size,
                    'size_str': format_size(size)
                })
    return jsonify({'files': files})


@app.route('/download/<path:filename>')
def download_file(filename):
    """提供安装文件的下载"""
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)


def format_size(size):
    """格式化文件大小"""
    if size < 1024:
        return f'{size} B'
    elif size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    elif size < 1024 * 1024 * 1024:
        return f'{size / 1024 / 1024:.1f} MB'
    else:
        return f'{size / 1024 / 1024 / 1024:.2f} GB'


# ─── 存档路由 ────────────────────────────────────────────────

@app.route('/save', methods=['POST'])
def save_project():
    """保存项目：返回JSON文件"""
    fs = get_fs()
    eqs = session.get('eqs', {})
    rels = session.get('rels', {})

    project = {
        'fs': fs,
        'eqs': eqs,
        'rels': rels
    }

    resp = make_response(json.dumps(project, ensure_ascii=False, indent=2))
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Content-Disposition'] = 'attachment; filename="project.json"'
    return resp


@app.route('/load', methods=['POST'])
def load_project():
    """打开项目：上传JSON文件并恢复状态"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未选择文件'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'})

    try:
        data = json.loads(file.read().decode('utf-8'))
        if 'fs' in data:
            session['fs'] = data['fs']
        if 'eqs' in data:
            session['eqs'] = data['eqs']
        if 'rels' in data:
            session['rels'] = data['rels']
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/clear_session')
def clear_session():
    session.clear()
    return jsonify({'success': True, 'message': '已清除所有数据'})


# ─── API: 渲染公式 ───────────────────────────────────────────

@app.route('/api/render')
def api_render():
    """AJAX接口：渲染表达式为LaTeX"""
    expr = request.args.get('expr', '')
    fs = get_fs()
    try:
        result = latex(sympify(expr, fs))
        return jsonify({'success': True, 'latex': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)
