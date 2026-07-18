"""CalculusCalculator Web 版 —— Flask 后端

适配 PythonAnywhere 部署。状态通过文件系统持久化（data/ 目录），
每个会话一个 JSON 文件，避免多 worker 下的共享问题。
"""
import os
import sys
import base64
import traceback

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use('Agg')

from io import BytesIO
from flask import (
    Flask, render_template, request, jsonify, session, send_file,
    redirect, url_for, Response
)
from sympy import latex, Eq, Rel, Symbol, symbols, radsimp, simplify, sqrt, atan2, acos, N
from sympy.geometry import Point3D, Line3D, Plane

from core.sympify import sympify
from core import settings as state_mgr
from functions.derivative import derivative, yinhanshu_derivative
from functions.integral import integral
from functions.functions import get_function_attr
from functions.simplification import simplifies
from functions.solvers import (
    solve_fangcheng, solve_weifenfangcheng, solve_fangchengzu,
    solve_budengshi, solve_budengshizu, solve_sanjiaoxing
)
from functions import planes, solids
from functions.paint2D import draw2d
from functions.paint3D import draw3d
from functions.saves import export_project, import_project

app = Flask(__name__)
app.secret_key = os.urandom(24)


# ============================================================
# 状态管理辅助函数
# ============================================================

def get_session_id():
    """获取或创建会话 ID。"""
    sid = session.get("sid")
    if not sid:
        sid = state_mgr.new_session_id()
        session["sid"] = sid
    return sid


def get_state():
    """读取当前会话的完整状态，并将序列化的几何对象还原为 SymPy 对象。"""
    sid = get_session_id()
    raw = state_mgr.read_session(sid) or {}
    if not isinstance(raw, dict):
        raw = {}

    fs = raw.get("fs", {})
    if not isinstance(fs, dict):
        fs = {}
    raw["fs"] = fs

    # 还原平面几何对象
    if "pjs" in raw and raw["pjs"]:
        raw["pjs"] = deserialize_pjs(raw["pjs"], fs)
    else:
        raw["pjs"] = {}
    # 还原立体几何对象
    if "ljs" in raw and raw["ljs"]:
        raw["ljs"] = deserialize_ljs(raw["ljs"], fs)
    else:
        raw["ljs"] = {}
    # 方程/不等式从字符串还原
    raw_eqs = raw.get("eqs", [])
    if isinstance(raw_eqs, list):
        raw["eqs"] = {k: sympify(k, fs) for k in raw_eqs if isinstance(k, str)}
    elif isinstance(raw_eqs, dict):
        pass  # 已经是字典
    else:
        raw["eqs"] = {}
    raw_rels = raw.get("rels", [])
    if isinstance(raw_rels, list):
        raw["rels"] = {k: sympify(k, fs) for k in raw_rels if isinstance(k, str)}
    elif isinstance(raw_rels, dict):
        pass
    else:
        raw["rels"] = {}
    if "vs" not in raw or not isinstance(raw["vs"], dict):
        raw["vs"] = {}
    if "cache" not in raw or not isinstance(raw["cache"], list):
        raw["cache"] = []
    return raw


def save_state(state):
    """保存当前会话的完整状态，将 SymPy 对象序列化为可 JSON 化的格式。"""
    sid = get_session_id()
    serializable = dict(state)
    # 序列化平面几何对象
    if "pjs" in serializable and serializable["pjs"]:
        pjs = serializable["pjs"]
        if any(isinstance(v, tuple) for v in pjs.values()):
            serializable["pjs"] = serialize_pjs(pjs)
    # 序列化立体几何对象
    if "ljs" in serializable and serializable["ljs"]:
        ljs = serializable["ljs"]
        if any(isinstance(v, tuple) for v in ljs.values()):
            serializable["ljs"] = serialize_ljs(ljs)
    # 方程/不等式保存为字符串键
    if "eqs" in serializable:
        eqs = serializable["eqs"]
        serializable["eqs"] = list(eqs.keys()) if eqs else []
    if "rels" in serializable:
        rels = serializable["rels"]
        serializable["rels"] = list(rels.keys()) if rels else []
    state_mgr.write_session(sid, serializable)


def get_fs(state=None):
    """获取函数列表。"""
    if state is None:
        state = get_state()
    return state.get("fs", {})


def serialize_pjs(pjs):
    """将平面几何对象字典序列化为可 JSON 化的格式。"""
    result = {}
    for k, v in pjs.items():
        cat = v[0]
        try:
            eq = v[1].equation() if hasattr(v[1], 'equation') else None
            eq_str = str(eq) if eq is not None else str(v[1])
        except Exception:
            eq_str = str(v[1])
        result[k] = {"category": cat, "repr": repr(v[1]), "equation": eq_str}
    return result


def serialize_ljs(ljs):
    """将立体几何对象字典序列化为可 JSON 化的格式。"""
    result = {}
    for k, v in ljs.items():
        cat = v[0]
        try:
            eq = v[1].equation() if hasattr(v[1], 'equation') else None
            eq_str = str(eq) if eq is not None else str(v[1])
        except Exception:
            eq_str = str(v[1])
        result[k] = {"category": cat, "repr": repr(v[1]), "equation": eq_str}
    return result


def deserialize_pjs(serialized, fs):
    """将序列化的平面几何对象字典还原。"""
    from sympy import Line, Circle
    result = {}
    for k, v in serialized.items():
        cat = v["category"]
        try:
            obj = sympify(v["repr"], fs)
            if cat == "直线" and not isinstance(obj, Line):
                obj = Line(sympify(v["repr"], fs))
            elif cat == "圆" and not isinstance(obj, Circle):
                obj = Circle(sympify(v["repr"], fs))
        except Exception:
            continue
        if obj is not None:
            result[k] = (cat, obj)
    return result


def deserialize_ljs(serialized, fs):
    """将序列化的立体几何对象字典还原。"""
    result = {}
    for k, v in serialized.items():
        cat = v["category"]
        try:
            obj = sympify(v["repr"], fs)
            if cat == "直线" and not isinstance(obj, Line3D):
                obj = Line3D(sympify(v["repr"], fs))
            elif cat == "平面" and not isinstance(obj, Plane):
                obj = Plane(sympify(v["repr"], fs))
        except Exception:
            continue
        if obj is not None:
            result[k] = (cat, obj)
    return result


def fig_to_base64(fig, fmt='png', dpi=100):
    """将 matplotlib Figure 转为 base64 编码字符串。"""
    buf = BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    data = base64.b64encode(buf.getvalue()).decode('utf-8')
    import matplotlib.pyplot as plt
    plt.close(fig)
    return data


def safe_latex(expr):
    """安全地将表达式转为 LaTeX，出错时返回空字符串。"""
    try:
        if isinstance(expr, str):
            return expr
        return latex(expr)
    except Exception:
        return str(expr) if expr is not None else ""


def safe_str(expr):
    """安全地将表达式转为字符串。"""
    try:
        return str(expr) if expr is not None else ""
    except Exception:
        return ""


# ============================================================
# 页面路由
# ============================================================

@app.route("/")
def index():
    state = get_state()
    return render_template("index.html", state=state)


@app.route("/dingyi")
def page_dingyi():
    state = get_state()
    return render_template("dingyi.html", state=state)


@app.route("/qiudao")
def page_qiudao():
    state = get_state()
    return render_template("qiudao.html", state=state)


@app.route("/jifen")
def page_jifen():
    state = get_state()
    return render_template("jifen.html", state=state)


@app.route("/bianxing")
def page_bianxing():
    state = get_state()
    return render_template("bianxing.html", state=state)


@app.route("/fangcheng")
def page_fangcheng():
    state = get_state()
    return render_template("fangcheng.html", state=state)


@app.route("/fangchengzu")
def page_fangchengzu():
    state = get_state()
    return render_template("fangchengzu.html", state=state,
                           eqs=list(state.get("eqs", {}).keys()))


@app.route("/budengshi")
def page_budengshi():
    state = get_state()
    return render_template("budengshi.html", state=state)


@app.route("/budengshizu")
def page_budengshizu():
    state = get_state()
    return render_template("budengshizu.html", state=state,
                           rels=list(state.get("rels", {}).keys()))


@app.route("/jisuan")
def page_jisuan():
    state = get_state()
    return render_template("jisuan.html", state=state)


@app.route("/dingyixiangliang")
def page_dingyixiangliang():
    state = get_state()
    return render_template("dingyixiangliang.html", state=state,
                           vs=state.get("vs", {}))


@app.route("/huitu_hanshu")
def page_huitu_hanshu():
    state = get_state()
    return render_template("huitu_hanshu.html", state=state,
                           fs=state.get("fs", {}))


@app.route("/jiesanjiaoxing")
def page_jiesanjiaoxing():
    state = get_state()
    return render_template("jiesanjiaoxing.html", state=state)


@app.route("/dingyi_pj")
def page_dingyi_pj():
    state = get_state()
    pjs = state.get("pjs", {})
    return render_template("dingyi_pj.html", state=state,
                           pjs=serialize_pjs(pjs) if pjs else {})


@app.route("/huitu_pj")
def page_huitu_pj():
    state = get_state()
    pjs = state.get("pjs", {})
    return render_template("huitu_pj.html", state=state,
                           pjs=serialize_pjs(pjs) if pjs else {})


@app.route("/pjjisuan")
def page_pjjisuan():
    state = get_state()
    pjs = state.get("pjs", {})
    return render_template("pjjisuan.html", state=state,
                           pjs=serialize_pjs(pjs) if pjs else {})


@app.route("/dingyi_lj")
def page_dingyi_lj():
    state = get_state()
    ljs = state.get("ljs", {})
    return render_template("dingyi_lj.html", state=state,
                           ljs=serialize_ljs(ljs) if ljs else {})


@app.route("/huitu_lj")
def page_huitu_lj():
    state = get_state()
    ljs = state.get("ljs", {})
    return render_template("huitu_lj.html", state=state,
                           ljs=serialize_ljs(ljs) if ljs else {})


@app.route("/ljjisuan")
def page_ljjisuan():
    state = get_state()
    ljs = state.get("ljs", {})
    return render_template("ljjisuan.html", state=state,
                           ljs=serialize_ljs(ljs) if ljs else {})


@app.route("/huancun")
def page_huancun():
    state = get_state()
    return render_template("huancun.html", state=state,
                           cache=state.get("cache", []))


# ============================================================
# API 路由 —— 函数定义
# ============================================================

@app.route("/api/dingyi/save", methods=["POST"])
def api_dingyi_save():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    name = data.get("name", "").strip()
    expr = data.get("expr", "").strip()
    domain = data.get("domain", "Reals").strip()
    var = data.get("var", "").strip()
    if not name or not expr:
        return jsonify({"error": "函数名和表达式不能为空"})
    try:
        simplified = str(sympify(expr, fs))
    except Exception:
        simplified = expr
    fs[name] = [name, simplified, domain, var]
    state["fs"] = fs
    save_state(state)
    return jsonify({"ok": True, "fs": fs})


@app.route("/api/dingyi/delete", methods=["POST"])
def api_dingyi_delete():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    name = data.get("name", "").strip()
    if name in fs:
        del fs[name]
    state["fs"] = fs
    save_state(state)
    return jsonify({"ok": True, "fs": fs})


@app.route("/api/dingyi/attr", methods=["POST"])
def api_dingyi_attr():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    expr = data.get("expr", "")
    var = data.get("var", "")
    domain = data.get("domain", "Reals")
    attr = int(data.get("attr", 0))
    var_val = data.get("var_val", "")
    try:
        result = get_function_attr(expr, var, domain, attr, fs)
        result_latex = safe_latex(result)
        result_str = safe_str(result)
        # 函数值
        f_value = ""
        f_value_latex = ""
        if var_val:
            try:
                fv = radsimp(sympify(expr, fs).subs(symbols(var), sympify(var_val, fs)))
                f_value = str(fv)
                f_value_latex = safe_latex(fv)
            except Exception:
                pass
        return jsonify({"ok": True, "latex": result_latex, "text": result_str,
                         "f_value": f_value, "f_value_latex": f_value_latex})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 求导
# ============================================================

@app.route("/api/qiudao", methods=["POST"])
def api_qiudao():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    f = data.get("expr", "")
    v = data.get("var", "x")
    n = data.get("n", "1")
    x_val = data.get("x_val", "")
    is_yin = data.get("is_yin", False)
    yin_var = data.get("yin_var", "y")
    try:
        if is_yin:
            dif = yinhanshu_derivative(f, v, yin_var, n, None, fs)
        else:
            dif = derivative(f, v, n, None, fs)
        result_latex = safe_latex(dif)
        result_str = safe_str(dif)
        x_result_latex = ""
        x_result_str = ""
        if x_val:
            if is_yin:
                dif_x = yinhanshu_derivative(f, v, yin_var, n, x_val, fs)
            else:
                dif_x = derivative(f, v, n, x_val, fs)
            x_result_latex = safe_latex(dif_x)
            x_result_str = safe_str(dif_x)
        return jsonify({"ok": True, "latex": result_latex, "text": result_str,
                         "x_latex": x_result_latex, "x_text": x_result_str})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 积分
# ============================================================

@app.route("/api/jifen", methods=["POST"])
def api_jifen():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    f = data.get("expr", "")
    v = data.get("var", "x")
    a = data.get("a", "")
    b = data.get("b", "")
    is_ding = data.get("is_ding", False)
    try:
        if is_ding and a and b:
            F = integral(f, v, fs, a=a, b=b)
            result_latex = safe_latex(F)
            result_str = safe_str(F)
            # 同时返回不定积分
            F2 = integral(f, v, fs)
            return jsonify({"ok": True, "latex": result_latex, "text": result_str,
                             "indef_latex": safe_latex(F2), "indef_text": safe_str(F2)})
        else:
            F = integral(f, v, fs)
            return jsonify({"ok": True, "latex": safe_latex(F), "text": safe_str(F)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 变形
# ============================================================

@app.route("/api/bianxing", methods=["POST"])
def api_bianxing():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    expr = data.get("expr", "")
    method = int(data.get("method", 0))
    zhuyuan = data.get("zhuyuan", "")
    huanyuan = data.get("huanyuan", "")
    huanyuanshi = data.get("huanyuanshi", "")
    try:
        result = simplifies(expr, method, zhuyuan, huanyuan, huanyuanshi, fs)
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 方程
# ============================================================

@app.route("/api/fangcheng", methods=["POST"])
def api_fangcheng():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    lhs = data.get("lhs", "")
    rhs = data.get("rhs", "")
    zhuyuan = data.get("zhuyuan", "x")
    domain = data.get("domain", "Reals")
    is_weifen = data.get("is_weifen", False)
    try:
        if is_weifen:
            eq = Eq(sympify(lhs, {}), sympify(rhs, {}))
            result = solve_weifenfangcheng(eq, zhuyuan, fs)
        else:
            eq = Eq(sympify(lhs, fs), sympify(rhs, fs))
            result = solve_fangcheng(eq, zhuyuan, domain, fs)
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 方程组
# ============================================================

@app.route("/api/fangchengzu/save", methods=["POST"])
def api_fangchengzu_save():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    eqs = state.get("eqs", {})
    lhs = data.get("lhs", "")
    rhs = data.get("rhs", "")
    try:
        eq = Eq(sympify(lhs, fs), sympify(rhs, fs))
        key = str(eq)
        eqs[key] = eq
        state["eqs"] = eqs
        save_state(state)
        return jsonify({"ok": True, "eqs": list(eqs.keys())})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/fangchengzu/delete", methods=["POST"])
def api_fangchengzu_delete():
    data = request.json
    state = get_state()
    eqs = state.get("eqs", {})
    key = data.get("key", "")
    if key in eqs:
        del eqs[key]
    state["eqs"] = eqs
    save_state(state)
    return jsonify({"ok": True, "eqs": list(eqs.keys())})


@app.route("/api/fangchengzu/solve", methods=["POST"])
def api_fangchengzu_solve():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    eqs = state.get("eqs", {})
    ziyoubianliang = data.get("vars", "")
    try:
        zhuyuan = [Symbol(s.strip()) for s in ziyoubianliang.split(",")]
        result = solve_fangchengzu(list(eqs.values()), zhuyuan, fs)
        return jsonify({"ok": True, "latex": safe_latex(result).replace(":", "="), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 不等式
# ============================================================

@app.route("/api/budengshi", methods=["POST"])
def api_budengshi():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    lhs = data.get("lhs", "")
    rhs = data.get("rhs", "")
    op = data.get("op", ">")
    zhuyuan = data.get("zhuyuan", "x")
    domain = data.get("domain", "Reals")
    try:
        rel = Rel(sympify(lhs, fs), sympify(rhs, fs), op)
        result = solve_budengshi(rel, zhuyuan, domain, fs)
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 不等式组
# ============================================================

@app.route("/api/budengshizu/save", methods=["POST"])
def api_budengshizu_save():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    rels = state.get("rels", {})
    lhs = data.get("lhs", "")
    rhs = data.get("rhs", "")
    op = data.get("op", ">")
    try:
        rel = Rel(sympify(lhs, fs), sympify(rhs, fs), op)
        key = str(rel)
        rels[key] = rel
        state["rels"] = rels
        save_state(state)
        return jsonify({"ok": True, "rels": list(rels.keys())})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/budengshizu/delete", methods=["POST"])
def api_budengshizu_delete():
    data = request.json
    state = get_state()
    rels = state.get("rels", {})
    key = data.get("key", "")
    if key in rels:
        del rels[key]
    state["rels"] = rels
    save_state(state)
    return jsonify({"ok": True, "rels": list(rels.keys())})


@app.route("/api/budengshizu/solve", methods=["POST"])
def api_budengshizu_solve():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    rels = state.get("rels", {})
    ziyoubianliang = data.get("var", "x")
    try:
        result = solve_budengshizu(list(rels.values()), Symbol(ziyoubianliang), fs)
        if not result:
            result = "无解"
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 计算
# ============================================================

@app.route("/api/jisuan", methods=["POST"])
def api_jisuan():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    expr = data.get("expr", "")
    engine = int(data.get("engine", 0))
    jingdu = data.get("jingdu", "50")
    try:
        sys.set_int_max_str_digits(0)
        if engine == 0:
            result = eval(expr)
        elif engine == 1:
            import mpmath as mp
            from mpmath import sin, cos, tan, cot, sec, csc, sinh, cosh, tanh, coth, sech, csch, exp, log, ln, sqrt, root, pi, e, phi
            with mp.workdps(int(jingdu)):
                result = eval(expr)
        elif engine == 2:
            result = radsimp(sympify(expr, fs, is_simplify=True))
        elif engine == 3:
            result = sympify(expr, fs={})
            return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_latex(result)})
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 向量
# ============================================================

@app.route("/api/xiangliang/save", methods=["POST"])
def api_xiangliang_save():
    data = request.json
    state = get_state()
    vs = state.get("vs", {})
    name = data.get("name", "").strip()
    x = data.get("x", "")
    y = data.get("y", "")
    if not name:
        return jsonify({"error": "向量名不能为空"})
    vs[name] = [name, x, y]
    state["vs"] = vs
    save_state(state)
    return jsonify({"ok": True, "vs": vs})


@app.route("/api/xiangliang/delete", methods=["POST"])
def api_xiangliang_delete():
    data = request.json
    state = get_state()
    vs = state.get("vs", {})
    name = data.get("name", "").strip()
    if name in vs:
        del vs[name]
    state["vs"] = vs
    save_state(state)
    return jsonify({"ok": True, "vs": vs})


@app.route("/api/xiangliang/attr", methods=["POST"])
def api_xiangliang_attr():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    x_str = data.get("x", "")
    y_str = data.get("y", "")
    name = data.get("name", "")
    attr = int(data.get("attr", 0))
    try:
        x = sympify(x_str, fs)
        y = sympify(y_str, fs)
        if attr == 0:
            result = f"({x}, {y})"
            latex_str = f"\\vec{{{name}}}=({latex(x)}, {latex(y)})"
        elif attr == 1:
            result = simplify(sqrt(x**2 + y**2))
            latex_str = f"|\\vec{{{name}}}|=" + latex(result)
        elif attr == 2:
            result = simplify(atan2(y, x))
            latex_str = f"\\theta_{{{name}}}=" + latex(result)
        elif attr == 3:
            mag = sqrt(x**2 + y**2)
            ux = simplify(x / mag)
            uy = simplify(y / mag)
            result = f"({ux}, {uy})"
            latex_str = f"\\hat{{\\vec{{{name}}}}}=({latex(ux)}, {latex(uy)})"
        return jsonify({"ok": True, "latex": latex_str, "text": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/xiangliang/compute", methods=["POST"])
def api_xiangliang_compute():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    vs = state.get("vs", {})
    v1_name = data.get("v1", "")
    v2_name = data.get("v2", "")
    method = int(data.get("method", 0))
    if v1_name not in vs or v2_name not in vs:
        return jsonify({"error": "未找到向量"})
    try:
        x1 = sympify(vs[v1_name][1], fs)
        y1 = sympify(vs[v1_name][2], fs)
        x2 = sympify(vs[v2_name][1], fs)
        y2 = sympify(vs[v2_name][2], fs)
        if method == 0:
            rx = simplify(x1 + x2)
            ry = simplify(y1 + y2)
            result = f"({rx}, {ry})"
            latex_str = f"\\vec{{{v1_name}}}+\\vec{{{v2_name}}}=({latex(rx)}, {latex(ry)})"
        elif method == 1:
            rx = simplify(x1 - x2)
            ry = simplify(y1 - y2)
            result = f"({rx}, {ry})"
            latex_str = f"\\vec{{{v1_name}}}-\\vec{{{v2_name}}}=({latex(rx)}, {latex(ry)})"
        elif method == 2:
            dot = simplify(x1 * x2 + y1 * y2)
            result = dot
            latex_str = f"\\vec{{{v1_name}}}\\cdot\\vec{{{v2_name}}}=" + latex(dot)
        elif method == 3:
            dot = x1 * x2 + y1 * y2
            mag1 = sqrt(x1**2 + y1**2)
            mag2 = sqrt(x2**2 + y2**2)
            cos_theta = simplify(dot / (mag1 * mag2))
            angle = simplify(acos(cos_theta))
            result = angle
            latex_str = f"\\angle(\\vec{{{v1_name}}},\\vec{{{v2_name}}})=" + latex(angle)
        return jsonify({"ok": True, "latex": latex_str, "text": str(result)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 函数绘图
# ============================================================

@app.route("/api/huitu_hanshu", methods=["POST"])
def api_huitu_hanshu():
    import numpy as np
    from matplotlib.figure import Figure
    from sympy import lambdify, Symbol
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    expr_str = data.get("expr", "")
    func_name = data.get("func", "")
    left_str = data.get("left", "-10")
    right_str = data.get("right", "10")
    try:
        if func_name:
            fn = func_name.split("(")[0]
            if fn not in fs:
                return jsonify({"error": "未找到函数"})
            expr = sympify(fs[fn][1], fs)
            var = Symbol(fs[fn][3])
        else:
            expr = sympify(expr_str, fs)
            free_syms = list(expr.free_symbols)
            var = free_syms[0] if free_syms else Symbol('x')
        try:
            left = float(sympify(left_str, fs))
            right = float(sympify(right_str, fs))
        except Exception:
            left, right = -10, 10
        if left >= right:
            left, right = -10, 10

        f = lambdify(var, expr, modules=['numpy', {'conjugate': np.conj}])
        num_points = 2000
        x_vals = np.linspace(left, right, num_points)
        with np.errstate(invalid='ignore', divide='ignore'):
            y_vals = np.asarray(f(x_vals), dtype=np.float64)

        fig = Figure(figsize=(7, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        mask = np.isfinite(y_vals)
        segments = []
        start = 0
        while start < len(mask):
            if mask[start]:
                end = start
                while end < len(mask) and mask[end]:
                    end += 1
                segments.append((start, end))
                start = end
            else:
                start += 1
        for seg_start, seg_end in segments:
            ax.plot(x_vals[seg_start:seg_end], y_vals[seg_start:seg_end],
                    color='#1f77b4', linewidth=1.5)
        ax.axhline(y=0, color='black', linewidth=0.5)
        ax.axvline(x=0, color='black', linewidth=0.5)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.set_xlim(left, right)
        if np.any(mask):
            y_min, y_max = np.min(y_vals[mask]), np.max(y_vals[mask])
            margin = max((y_max - y_min) * 0.1, 1.0)
            ax.set_ylim(y_min - margin, y_max + margin)
        fig.tight_layout()
        img_data = fig_to_base64(fig)
        return jsonify({"ok": True, "image": img_data})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 解三角形
# ============================================================

@app.route("/api/jiesanjiaoxing", methods=["POST"])
def api_jiesanjiaoxing():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    conditions = data.get("conditions", [])
    angle_names = {1: 'A', 2: 'B', 3: 'C'}
    side_names = {4: 'a', 5: 'b', 6: 'c'}
    angles = {}
    sides = {}
    for cond in conditions:
        idx = cond.get("type", 0)
        val_text = cond.get("value", "").strip()
        if idx == 0 or not val_text:
            continue
        try:
            val = sympify(val_text, fs)
        except Exception:
            return jsonify({"error": "条件值格式错误"})
        if idx in angle_names:
            angles[angle_names[idx]] = val
        elif idx in side_names:
            sides[side_names[idx]] = val
    total = len(angles) + len(sides)
    if total != 3:
        return jsonify({"error": "请填入恰好3个有效且不重复的条件"})

    # 条件 LaTeX
    known_parts = []
    for k, v in {**angles, **sides}.items():
        known_parts.append(f"{k} = {latex(v)}")
    condition_latex = r"\triangle ABC \quad " + r",\ ".join(known_parts)

    try:
        result = solve_sanjiaoxing(angles, sides, fs)
        if not result:
            return jsonify({"ok": True, "condition_latex": condition_latex, "result_latex": "", "text": "无解"})
        if isinstance(result, str):
            return jsonify({"ok": True, "condition_latex": condition_latex, "result_latex": "", "text": result})
        lines = []
        for i, (res_angles, res_sides) in enumerate(result):
            parts = []
            for k, v in res_angles.items():
                parts.append(f"{k} = {latex(v)}")
            for k, v in res_sides.items():
                parts.append(f"{k} = {latex(v)}")
            if len(result) > 1:
                lines.append(r"\text{解}" + str(i + 1) + r":\ " + r",\ ".join(parts))
            else:
                lines.append(r",\ ".join(parts))
        result_latex = r" \\ ".join(lines) if len(lines) > 1 else lines[0]
        flat = []
        for i, (res_angles, res_sides) in enumerate(result):
            seg = []
            for k, v in res_angles.items():
                seg.append(f"{k} = {v}")
            for k, v in res_sides.items():
                seg.append(f"{k} = {v}")
            flat.append(" | ".join(seg))
        return jsonify({"ok": True, "condition_latex": condition_latex,
                         "result_latex": result_latex, "text": "  ||  ".join(flat)})
    except Exception as e:
        return jsonify({"error": str(e)})


# ============================================================
# API 路由 —— 平面几何定义
# ============================================================

@app.route("/api/dingyi_pj/create", methods=["POST"])
def api_dingyi_pj_create():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    pjs = state.get("pjs", {})
    idx = int(data.get("method", 0))
    name = data.get("name", "").strip()
    params_str = data.get("params", "").strip()
    if idx == 0 or not name:
        return jsonify({"error": "请选择方法并填写名称"})
    raw = [p.strip() for p in params_str.split(',')] if params_str else []

    def find_point(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "点":
            return pjs[n][1]
        return None

    def find_line(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "直线":
            return pjs[n][1]
        return None

    def find_segment(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "线段":
            return pjs[n][1]
        return None

    def find_triangle(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "三角形":
            return pjs[n][1]
        return None

    def find_points(names_str):
        pts = []
        for n in names_str.split(','):
            p = find_point(n.strip())
            if p is None:
                raise ValueError(f"未找到点'{n.strip()}'")
            pts.append(p)
        return pts

    from sympy import Point, Line
    try:
        if idx == 1:
            pt = planes.create_point(raw[0], raw[1], fs)
            pjs[name] = ("点", pt)
        elif idx == 2:
            p1, p2 = find_points(raw[0] + "," + raw[1])
            pjs[name] = ("直线", planes.create_line(p1, p2))
        elif idx == 3:
            pts = find_points(raw[0])
            pjs[name] = ("圆", planes.create_circle(pts[0], raw[1], fs))
        elif idx == 4:
            pts = find_points(raw[0] + "," + raw[1] + "," + raw[2])
            pjs[name] = ("圆", planes.create_circle_three_points(*pts))
        elif idx == 5:
            pts = find_points(raw[0] + "," + raw[1] + "," + raw[2])
            pjs[name] = ("三角形", planes.create_triangle(*pts))
        elif idx == 6:
            pts = find_points(",".join(raw))
            pjs[name] = ("多边形", planes.create_polygon(pts))
        elif idx == 7:
            pts = find_points(raw[0] + "," + raw[1])
            pjs[name] = ("圆", planes.circle_with_diameter(*pts))
        elif idx == 8:
            pts = find_points(raw[0] + "," + raw[1])
            pjs[name] = ("圆", planes.circle_by_center_and_point(pts[0], pts[1]))
        elif idx == 9:
            seg = find_segment(raw[0])
            if seg is None:
                return jsonify({"error": "未找到线段"})
            pjs[name] = ("直线", planes.perpendicular_bisector(seg.points[0], seg.points[1]))
        elif idx == 10:
            pts = find_points(raw[0])
            line_ref = find_line(raw[1])
            if line_ref is None:
                seg = find_segment(raw[1])
                if seg:
                    line_ref = Line(seg.points[0], seg.points[1])
            if line_ref is None:
                return jsonify({"error": "未找到直线/线段"})
            pjs[name] = ("直线", planes.line_parallel_through_point(line_ref, pts[0]))
        elif idx == 11:
            pts = find_points(raw[0])
            line_ref = find_line(raw[1])
            if line_ref is None:
                seg = find_segment(raw[1])
                if seg:
                    line_ref = Line(seg.points[0], seg.points[1])
            if line_ref is None:
                return jsonify({"error": "未找到直线/线段"})
            pjs[name] = ("直线", planes.line_perpendicular_through_point(line_ref, pts[0]))
        elif idx == 12:
            l1 = find_line(raw[0])
            l2 = find_line(raw[1])
            if l1 is None or l2 is None:
                return jsonify({"error": "未找到直线"})
            result = planes.angle_bisector_line(l1, l2)
            if isinstance(result, str):
                return jsonify({"error": result})
            pjs[name] = ("直线", result)
        elif idx == 13:
            pts = find_points(raw[0] + "," + raw[1] + "," + raw[2])
            pjs[name] = ("直线", planes.angle_bisector(*pts))
        elif idx == 14:
            tri = find_triangle(raw[0])
            if tri is None:
                return jsonify({"error": "未找到三角形"})
            v_idx = int(raw[1])
            pjs[name] = ("线段", planes.triangle_median(tri, v_idx))
        elif idx == 15:
            tri = find_triangle(raw[0])
            if tri is None:
                return jsonify({"error": "未找到三角形"})
            v_idx = int(raw[1])
            pjs[name] = ("直线", planes.triangle_altitude(tri, v_idx))
        elif idx == 16:
            tri = find_triangle(raw[0])
            if tri is None:
                return jsonify({"error": "未找到三角形"})
            pjs[name] = ("线段", planes.triangle_midsegment(tri))
        elif idx == 17:
            tri = find_triangle(raw[0])
            if tri is None:
                return jsonify({"error": "未找到三角形"})
            pjs[name] = ("圆", planes.triangle_incircle(tri))
        elif idx == 18:
            tri = find_triangle(raw[0])
            if tri is None:
                return jsonify({"error": "未找到三角形"})
            v_idx = int(raw[1])
            pjs[name] = ("圆", planes.triangle_excircle(tri, v_idx))
        elif idx == 19:
            pts = find_points(raw[0] + "," + raw[1])
            pjs[name] = ("线段", planes.segment_from_points(*pts))
        else:
            return jsonify({"error": "未知方法"})
        state["pjs"] = pjs
        save_state(state)
        return jsonify({"ok": True, "pjs": serialize_pjs(pjs)})
    except Exception as e:
        return jsonify({"error": f"创建失败: {e}"})


@app.route("/api/dingyi_pj/delete", methods=["POST"])
def api_dingyi_pj_delete():
    data = request.json
    state = get_state()
    pjs = state.get("pjs", {})
    name = data.get("name", "").strip()
    if name in pjs:
        del pjs[name]
    state["pjs"] = pjs
    save_state(state)
    return jsonify({"ok": True, "pjs": serialize_pjs(pjs)})


# ============================================================
# API 路由 —— 平面几何绘图
# ============================================================

@app.route("/api/huitu_pj", methods=["POST"])
def api_huitu_pj():
    data = request.json
    state = get_state()
    pjs = state.get("pjs", {})
    checked = data.get("checked", [])
    objects = []
    for name in checked:
        if name in pjs:
            objects.append((pjs[name][1], {'label': name}))
    if not objects:
        return jsonify({"error": "没有可绘制的对象"})
    try:
        fig = draw2d(objects, figsize=(7, 5.5), dpi=100)
        img_data = fig_to_base64(fig)
        return jsonify({"ok": True, "image": img_data})
    except Exception as e:
        return jsonify({"error": f"绘制失败: {e}"})


# ============================================================
# API 路由 —— 平面几何计算
# ============================================================

@app.route("/api/pjjisuan", methods=["POST"])
def api_pjjisuan():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    pjs = state.get("pjs", {})
    idx = int(data.get("method", 0))
    params_str = data.get("params", "").strip()
    if idx == 0 or not params_str:
        return jsonify({"error": "请选择方法并填写参数"})
    raw = [p.strip() for p in params_str.split(',')]

    def get_point(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "点":
            return pjs[n][1]
        raise ValueError(f"未找到点'{n}'")

    def get_line_points(*params):
        if len(params) == 1:
            n = params[0].strip()
            if n in pjs and pjs[n][0] == "直线":
                return pjs[n][1].points[0], pjs[n][1].points[1]
        return tuple(get_point(p) for p in params[:2])

    def get_circle(n):
        n = n.strip()
        if n in pjs and pjs[n][0] == "圆":
            return pjs[n][1]
        raise ValueError(f"未找到圆'{n}'")

    def get_triangle_points(*params):
        if len(params) == 1:
            n = params[0].strip()
            if n in pjs and pjs[n][0] == "三角形":
                return pjs[n][1].vertices
        return tuple(get_point(p) for p in params[:3])

    try:
        if idx == 1:
            result = planes.point_distance(get_point(raw[0]), get_point(raw[1]))
        elif idx == 2:
            result = planes.midpoint(get_point(raw[0]), get_point(raw[1]))
        elif idx == 3:
            pts = [get_point(p) for p in raw]
            result = planes.collinear_check(pts)
        elif idx == 4:
            result = planes.translate_point(get_point(raw[0]), raw[1], raw[2], fs)
        elif idx == 5:
            result = planes.rotate_point(get_point(raw[0]), raw[1], get_point(raw[2]), fs)
        elif idx == 6:
            pt = get_point(raw[0])
            lp = get_line_points(*raw[1:])
            result = planes.reflect_point(pt, lp[0], lp[1])
        elif idx == 7:
            result = planes.line_equation(get_point(raw[0]), get_point(raw[1]))
        elif idx == 8:
            result = planes.line_slope(get_point(raw[0]), get_point(raw[1]))
        elif idx == 9:
            if len(raw) <= 2:
                lp1 = get_line_points(raw[0])
                lp2 = get_line_points(raw[1])
            else:
                lp1 = get_line_points(raw[0], raw[1])
                lp2 = get_line_points(raw[2], raw[3])
            result = planes.line_intersection(lp1[0], lp1[1], lp2[0], lp2[1])
        elif idx == 10:
            pt = get_point(raw[0])
            lp = get_line_points(*raw[1:])
            result = planes.point_to_line_distance(pt, lp[0], lp[1])
        elif idx == 11:
            if len(raw) <= 2:
                lp1 = get_line_points(raw[0])
                lp2 = get_line_points(raw[1])
            else:
                lp1 = get_line_points(raw[0], raw[1])
                lp2 = get_line_points(raw[2], raw[3])
            result = planes.angle_between_lines(lp1[0], lp1[1], lp2[0], lp2[1])
        elif idx == 12:
            if len(raw) <= 2:
                lp1 = get_line_points(raw[0])
                lp2 = get_line_points(raw[1])
            else:
                lp1 = get_line_points(raw[0], raw[1])
                lp2 = get_line_points(raw[2], raw[3])
            result = planes.parallel_check(lp1[0], lp1[1], lp2[0], lp2[1])
        elif idx == 13:
            if len(raw) <= 2:
                lp1 = get_line_points(raw[0])
                lp2 = get_line_points(raw[1])
            else:
                lp1 = get_line_points(raw[0], raw[1])
                lp2 = get_line_points(raw[2], raw[3])
            result = planes.perpendicular_check(lp1[0], lp1[1], lp2[0], lp2[1])
        elif idx == 14:
            c = get_circle(raw[0])
            result = (radsimp(c.center.x), radsimp(c.center.y))
        elif idx == 15:
            c = get_circle(raw[0])
            result = radsimp(c.radius)
        elif idx == 16:
            c = get_circle(raw[0])
            result = radsimp(c.area)
        elif idx == 17:
            c = get_circle(raw[0])
            result = radsimp(c.circumference)
        elif idx == 18:
            c1, c2 = get_circle(raw[0]), get_circle(raw[1])
            inter = c1.intersection(c2)
            result = [(radsimp(pt.x), radsimp(pt.y)) for pt in inter] if inter else "两圆不相交"
        elif idx == 19:
            pt = get_point(raw[0])
            c = get_circle(raw[1])
            tangents = c.tangent_lines(pt)
            result = [simplify(line.equation()) for line in tangents] if tangents else "无切线"
        elif idx == 20:
            v = get_triangle_points(*raw)
            result = planes.triangle_area(*v)
        elif idx == 21:
            v = get_triangle_points(*raw)
            result = planes.triangle_perimeter(*v)
        elif idx == 22:
            v = get_triangle_points(*raw)
            result = planes.triangle_circumcenter(*v)
        elif idx == 23:
            v = get_triangle_points(*raw)
            result = planes.triangle_circumradius(*v)
        elif idx == 24:
            v = get_triangle_points(*raw)
            result = planes.triangle_incenter(*v)
        elif idx == 25:
            v = get_triangle_points(*raw)
            result = planes.triangle_inradius(*v)
        elif idx == 26:
            v = get_triangle_points(*raw)
            result = planes.triangle_centroid(*v)
        elif idx == 27:
            v = get_triangle_points(*raw)
            result = planes.triangle_orthocenter(*v)
        elif idx == 28:
            v = get_triangle_points(*raw)
            result = planes.triangle_is_right(*v)
        elif idx == 29:
            v = get_triangle_points(*raw)
            result = planes.triangle_is_isosceles(*v)
        elif idx == 30:
            v = get_triangle_points(*raw)
            result = planes.triangle_is_equilateral(*v)
        elif idx == 31:
            pts = [get_point(p) for p in raw]
            result = planes.polygon_area_func(pts)
        elif idx == 32:
            pts = [get_point(p) for p in raw]
            result = planes.polygon_perimeter_func(pts)
        else:
            result = "未知操作"
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": f"计算错误: {e}"})


# ============================================================
# API 路由 —— 立体几何定义
# ============================================================

@app.route("/api/dingyi_lj/create", methods=["POST"])
def api_dingyi_lj_create():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    ljs = state.get("ljs", {})
    idx = int(data.get("method", 0))
    name = data.get("name", "").strip()
    params_str = data.get("params", "").strip()
    if idx == 0 or not name:
        return jsonify({"error": "请选择方法并填写名称"})
    raw = [p.strip() for p in params_str.split(',')] if params_str else []

    def find_point3d(n):
        n = n.strip()
        return ljs[n][1] if n in ljs and ljs[n][0] == "点" else None

    def find_line3d(n):
        n = n.strip()
        return ljs[n][1] if n in ljs and ljs[n][0] == "直线" else None

    def find_plane(n):
        n = n.strip()
        return ljs[n][1] if n in ljs and ljs[n][0] == "平面" else None

    def find_points3d(names_str):
        pts = []
        for n in names_str.split(','):
            p = find_point3d(n.strip())
            if p is None:
                raise ValueError(f"未找到点'{n.strip()}'")
            pts.append(p)
        return pts

    try:
        if idx == 1:
            pt = solids.create_point3d(raw[0], raw[1], raw[2], fs)
            ljs[name] = ("点", pt)
        elif idx == 2:
            pts = find_points3d(raw[0] + "," + raw[1])
            ljs[name] = ("直线", solids.create_line3d(*pts))
        elif idx == 3:
            pl = find_plane(raw[0])
            pt = find_point3d(raw[1])
            if pl and pt:
                ljs[name] = ("平面", solids.plane_parallel_through_point(pl, pt))
        elif idx == 4:
            line = find_line3d(raw[0])
            pt = find_point3d(raw[1])
            if line and pt:
                ljs[name] = ("平面", solids.plane_perpendicular_to_line_through_point(line, pt))
        elif idx == 5:
            line = find_line3d(raw[0])
            pt = find_point3d(raw[1])
            if line and pt:
                ljs[name] = ("直线", solids.line_parallel_through_point_3d(line, pt))
        elif idx == 6:
            pt = find_point3d(raw[0])
            line = find_line3d(raw[1])
            if pt and line:
                foot = solids.perpendicular_foot_to_line_3d(pt, line)
                ljs[name] = ("直线", solids.create_line3d(pt, foot))
        elif idx == 7:
            pl = find_plane(raw[0])
            pt = find_point3d(raw[1])
            if pl and pt:
                ljs[name] = ("直线", solids.line_perpendicular_to_plane_through_point(pl, pt))
        elif idx == 8:
            line = find_line3d(raw[0])
            pt = find_point3d(raw[1])
            if line and pt:
                result = solids.plane_through_line_and_point(line, pt)
                if not isinstance(result, str):
                    ljs[name] = ("平面", result)
        elif idx == 9:
            l1 = find_line3d(raw[0])
            l2 = find_line3d(raw[1])
            if l1 and l2:
                result = solids.plane_through_two_lines(l1, l2)
                if not isinstance(result, str):
                    ljs[name] = ("平面", result)
        elif idx == 10:
            pt = find_point3d(raw[0])
            pl = find_plane(raw[1])
            if pt and pl:
                ljs[name] = ("点", solids.perpendicular_foot_to_plane(pt, pl))
        elif idx == 11:
            pt = find_point3d(raw[0])
            line = find_line3d(raw[1])
            if pt and line:
                ljs[name] = ("点", solids.perpendicular_foot_to_line_3d(pt, line))
        elif idx == 12:
            pts = find_points3d(raw[0] + "," + raw[1])
            ljs[name] = ("线段", solids.segment3d_from_points(*pts))
        else:
            return jsonify({"error": "未知方法"})
        state["ljs"] = ljs
        save_state(state)
        return jsonify({"ok": True, "ljs": serialize_ljs(ljs)})
    except Exception as e:
        return jsonify({"error": f"创建失败: {e}"})


@app.route("/api/dingyi_lj/delete", methods=["POST"])
def api_dingyi_lj_delete():
    data = request.json
    state = get_state()
    ljs = state.get("ljs", {})
    name = data.get("name", "").strip()
    if name in ljs:
        del ljs[name]
    state["ljs"] = ljs
    save_state(state)
    return jsonify({"ok": True, "ljs": serialize_ljs(ljs)})


# ============================================================
# API 路由 —— 立体几何绘图
# ============================================================

@app.route("/api/huitu_lj", methods=["POST"])
def api_huitu_lj():
    data = request.json
    state = get_state()
    ljs = state.get("ljs", {})
    checked = data.get("checked", [])
    objects = []
    for name in checked:
        if name in ljs:
            objects.append((ljs[name][1], {'label': name}))
    if not objects:
        return jsonify({"error": "没有可绘制的对象"})
    try:
        fig = draw3d(objects, figsize=(7, 5.5), dpi=100)
        img_data = fig_to_base64(fig)
        return jsonify({"ok": True, "image": img_data})
    except Exception as e:
        return jsonify({"error": f"绘制失败: {e}"})


# ============================================================
# API 路由 —— 立体几何计算
# ============================================================

@app.route("/api/ljjisuan", methods=["POST"])
def api_ljjisuan():
    data = request.json
    state = get_state()
    fs = state.get("fs", {})
    ljs = state.get("ljs", {})
    idx = int(data.get("method", 0))
    params_str = data.get("params", "").strip()
    if idx == 0 or not params_str:
        return jsonify({"error": "请选择方法并填写参数"})
    raw = [p.strip() for p in params_str.split(',')]

    def get_point3d(n):
        n = n.strip()
        if n in ljs and ljs[n][0] == "点":
            return ljs[n][1]
        raise ValueError(f"未找到三维点'{n}'")

    def get_line3d_or_from_points(*params):
        if len(params) == 1:
            n = params[0].strip()
            if n in ljs and ljs[n][0] == "直线":
                return ljs[n][1]
            raise ValueError(f"未找到三维直线'{n}'")
        return Line3D(get_point3d(params[0]), get_point3d(params[1]))

    def get_plane(n):
        n = n.strip()
        if n in ljs and ljs[n][0] == "平面":
            return ljs[n][1]
        raise ValueError(f"未找到平面'{n}'")

    try:
        if idx == 1:
            result = solids.point3d_distance(get_point3d(raw[0]), get_point3d(raw[1]))
        elif idx == 2:
            result = solids.point3d_midpoint(get_point3d(raw[0]), get_point3d(raw[1]))
        elif idx == 3:
            result = solids.point3d_to_plane_distance(get_point3d(raw[0]), get_plane(raw[1]))
        elif idx == 4:
            result = solids.point3d_to_line_distance(get_point3d(raw[0]), get_line3d_or_from_points(*raw[1:]))
        elif idx == 5:
            result = solids.point3d_projection_on_plane(get_point3d(raw[0]), get_plane(raw[1]))
        elif idx == 6:
            result = solids.point3d_projection_on_line(get_point3d(raw[0]), get_line3d_or_from_points(*raw[1:]))
        elif idx == 7:
            pts = [get_point3d(p) for p in raw]
            result = solids.are_coplanar(pts)
        elif idx == 8:
            result = solids.line3d_direction(get_line3d_or_from_points(*raw))
        elif idx == 9:
            result = solids.line3d_intersection(
                get_line3d_or_from_points(*raw[:len(raw)//2]),
                get_line3d_or_from_points(*raw[len(raw)//2:]))
        elif idx == 10:
            result = solids.line3d_angle(
                get_line3d_or_from_points(*raw[:len(raw)//2]),
                get_line3d_or_from_points(*raw[len(raw)//2:]))
        elif idx == 11:
            result = solids.line3d_parallel_check(
                get_line3d_or_from_points(*raw[:len(raw)//2]),
                get_line3d_or_from_points(*raw[len(raw)//2:]))
        elif idx == 12:
            result = solids.line3d_perpendicular_check(
                get_line3d_or_from_points(*raw[:len(raw)//2]),
                get_line3d_or_from_points(*raw[len(raw)//2:]))
        elif idx == 13:
            result = solids.line3d_projection_on_plane(
                get_line3d_or_from_points(*raw[:-1]),
                get_plane(raw[-1]))
        elif idx == 14:
            result = solids.plane_equation_from_points(
                get_point3d(raw[0]), get_point3d(raw[1]), get_point3d(raw[2]))
        elif idx == 15:
            result = solids.plane_normal_vector(get_plane(raw[0]))
        elif idx == 16:
            result = solids.plane_angle_between(get_plane(raw[0]), get_plane(raw[1]))
        elif idx == 17:
            result = solids.plane_intersection(get_plane(raw[0]), get_plane(raw[1]))
        elif idx == 18:
            result = solids.plane_parallel_check(get_plane(raw[0]), get_plane(raw[1]))
        elif idx == 19:
            result = solids.plane_perpendicular_check(get_plane(raw[0]), get_plane(raw[1]))
        elif idx == 20:
            result = solids.plane_line_intersection(get_plane(raw[0]), get_line3d_or_from_points(*raw[1:]))
        elif idx == 21:
            result = solids.tetrahedron_volume(
                get_point3d(raw[0]), get_point3d(raw[1]),
                get_point3d(raw[2]), get_point3d(raw[3]))
        elif idx == 22:
            result = solids.line_plane_angle(
                get_line3d_or_from_points(*raw[:-1]),
                get_plane(raw[-1]))
        else:
            result = "未知操作"
        return jsonify({"ok": True, "latex": safe_latex(result), "text": safe_str(result)})
    except Exception as e:
        return jsonify({"error": f"计算错误: {e}"})


# ============================================================
# API 路由 —— 缓存区
# ============================================================

@app.route("/api/huancun/add", methods=["POST"])
def api_huancun_add():
    data = request.json
    state = get_state()
    cache = state.get("cache", [])
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "内容为空"})
    if text in cache:
        cache.remove(text)
    cache.insert(0, text)
    state["cache"] = cache
    save_state(state)
    return jsonify({"ok": True, "cache": cache})


@app.route("/api/huancun/delete", methods=["POST"])
def api_huancun_delete():
    data = request.json
    state = get_state()
    cache = state.get("cache", [])
    text = data.get("text", "").strip()
    if text in cache:
        cache.remove(text)
    state["cache"] = cache
    save_state(state)
    return jsonify({"ok": True, "cache": cache})


@app.route("/api/huancun/clear", methods=["POST"])
def api_huancun_clear():
    state = get_state()
    state["cache"] = []
    save_state(state)
    return jsonify({"ok": True})


@app.route("/api/huancun/list", methods=["GET"])
def api_huancun_list():
    state = get_state()
    return jsonify({"cache": state.get("cache", [])})


# ============================================================
# API 路由 —— 存档/读档
# ============================================================

@app.route("/api/save", methods=["GET", "POST"])
def api_save():
    state = get_state()
    try:
        json_str = export_project(state)
        return Response(
            json_str,
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment; filename=calculus_project.json'}
        )
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/load", methods=["POST"])
def api_load():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "未上传文件"})
    try:
        json_str = file.read().decode('utf-8')
        state = import_project(json_str, {})
        save_state(state)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": f"读取失败: {e}"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
