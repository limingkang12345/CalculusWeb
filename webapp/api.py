"""Flask API：封装原 functions/core 计算内核，提供与桌面版一致的计算能力。"""
import uuid

from flask import Blueprint, request, session, jsonify, Response
from sympy import (
    Eq, Rel, Symbol, sqrt, acos, atan2, radsimp, latex,
)
from core.sympify import sympify
from . import state as statemod
from .util import S, to_latex, fig_to_png, ok, err
from . import geometry

api = Blueprint("api", __name__)


def current_state():
    sid = session.get("sid")
    if not sid:
        sid = uuid.uuid4().hex
        session["sid"] = sid
    return statemod.get_state(sid)


def j(data):
    return jsonify(data)


# ------------------------- 通用计算包装 -------------------------
def _calc(fn, *args):
    try:
        res = fn(*args)
        return ok(to_latex(res))
    except Exception as e:  # noqa: BLE001
        return err(e)


# ========================= 定义类接口 =========================
@api.route("/api/func", methods=["POST"])
def save_func():
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get("name") or "").strip()
    expr = (d.get("expr") or "").strip()
    if not name or not expr:
        return j(err("函数名与表达式均不可为空"))
    st = current_state()
    try:
        # 与桌面版一致：fs 中保存表达式字符串（sympify 内部会再次解析，
        # 且 _preprocess_func_calls 需要对函数体字符串做正则替换）
        e = S(expr, st.fs)
        st.fs[name] = [name, str(e), d.get("domain", "") or "", d.get("var", "") or ""]
        return j(ok("已保存函数 $%s$" % name))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/func/<name>", methods=["DELETE"])
def del_func(name):
    current_state().fs.pop(name, None)
    return j(ok("已删除"))


@api.route("/api/vector", methods=["POST"])
def save_vector():
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get("name") or "").strip()
    x = (d.get("x") or "").strip()
    y = (d.get("y") or "").strip()
    if not name or not x or not y:
        return j(err("向量名与两个分量均不可为空"))
    current_state().vs[name] = [name, x, y]
    return j(ok("已保存向量 $\\vec{%s}$" % name))


@api.route("/api/vector/<name>", methods=["DELETE"])
def del_vector(name):
    current_state().vs.pop(name, None)
    return j(ok("已删除"))


def _eq_key(lhs, rhs):
    return "$%s=%s$" % (to_latex(S(lhs, {})), to_latex(S(rhs, {})))


@api.route("/api/eq", methods=["POST"])
def save_eq():
    d = request.get_json(force=True, silent=True) or {}
    lhs, rhs = (d.get("lhs") or "").strip(), (d.get("rhs") or "").strip()
    if not lhs or not rhs:
        return j(err("等式左右两边均不可为空"))
    st = current_state()
    try:
        eq = Eq(S(lhs, st.fs), S(rhs, st.fs))
        key = _eq_key(lhs, rhs)
        st.eqs[key] = eq
        return j(ok("已保存方程 %s" % key))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/eq/<path:key>", methods=["DELETE"])
def del_eq(key):
    current_state().eqs.pop(key, None)
    return j(ok("已删除"))


@api.route("/api/rel", methods=["POST"])
def save_rel():
    d = request.get_json(force=True, silent=True) or {}
    lhs = (d.get("lhs") or "").strip()
    rhs = (d.get("rhs") or "").strip()
    op = d.get("op") or ">="
    if not lhs or not rhs:
        return j(err("不等式左右两边均不可为空"))
    st = current_state()
    try:
        rel = Rel(S(lhs, st.fs), S(rhs, st.fs), op)
        key = "$%s%s%s$" % (to_latex(S(lhs, {})), op, to_latex(S(rhs, {})))
        st.rels[key] = rel
        return j(ok("已保存不等式 %s" % key))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/rel/<path:key>", methods=["DELETE"])
def del_rel(key):
    current_state().rels.pop(key, None)
    return j(ok("已删除"))


@api.route("/api/pjs", methods=["POST"])
def save_pjs():
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get("name") or "").strip()
    method = int(d.get("method", 0))
    params = d.get("params", "") or ""
    if not name:
        return j(err("对象名不可为空"))
    st = current_state()
    try:
        obj = geometry.create_plane_object(method, name, params, st.fs, st.pjs)
        st.pjs[name] = obj
        return j(ok("已定义%s '%s'" % (obj[0], name)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/pjs/<name>", methods=["DELETE"])
def del_pjs(name):
    current_state().pjs.pop(name, None)
    return j(ok("已删除"))


@api.route("/api/ljs", methods=["POST"])
def save_ljs():
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get("name") or "").strip()
    method = int(d.get("method", 0))
    params = d.get("params", "") or ""
    if not name:
        return j(err("对象名不可为空"))
    st = current_state()
    try:
        obj = geometry.create_solid_object(method, name, params, st.fs, st.ljs)
        st.ljs[name] = obj
        return j(ok("已定义%s '%s'" % (obj[0], name)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/ljs/<name>", methods=["DELETE"])
def del_ljs(name):
    current_state().ljs.pop(name, None)
    return j(ok("已删除"))


# ========================= 计算类接口 =========================
@api.route("/api/derivative", methods=["POST"])
def derivative():
    from functions.derivative import derivative as der, yinhanshu_derivative
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        # 原函数内部会自行 sympify，因此这里传入原始文本
        f = d.get("expr", "")
        v = d.get("var", "x")
        n = int(d.get("order", 1) or 1)
        x = d.get("point", "") or ""
        if d.get("yinhanshu"):
            yinvar = d.get("yinvar", "t")
            res = yinhanshu_derivative(f, v, yinvar, n, x, st.fs)
        else:
            res = der(f, v, n, x, st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/integral", methods=["POST"])
def integral():
    from functions.integral import integral as integ
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        # 原 integral 内部会自行 sympify
        f = d.get("expr", "")
        v = d.get("var", "x")
        a = d.get("a", "") or None
        b = d.get("b", "") or None
        res = integ(f, v, st.fs, a, b)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/simplify", methods=["POST"])
def simplify():
    from functions.simplification import simplifies
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        # simplifies 内部自行解析表达式，因此传入原始文本
        res = simplifies(
            d.get("expr", ""),
            int(d.get("method", 0)),
            (d.get("zhuyuan") or "") or None,
            (d.get("huanyuan") or "") or None,
            (d.get("huayuanshi") or "") or None,
            st.fs,
        )
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/equation", methods=["POST"])
def equation():
    from functions.solvers import solve_fangcheng, solve_weifenfangcheng
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        if d.get("de"):
            # 微分方程：不替换已定义函数，f(x) 是未知函数而非已保存函数
            lhs = S(d.get("lhs", ""), {})
            rhs = S(d.get("rhs", ""), {})
            eq = Eq(lhs, rhs)
            res = solve_weifenfangcheng(eq, d.get("var", "f(x)"), st.fs)
        else:
            lhs = S(d.get("lhs", ""), st.fs)
            rhs = S(d.get("rhs", ""), st.fs)
            eq = Eq(lhs, rhs)
            res = solve_fangcheng(eq, d.get("var", "x"), d.get("domain", "Reals"), st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/system", methods=["POST"])
def system():
    from functions.solvers import solve_fangchengzu
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        eqs = [Eq(S(l, st.fs), S(r, st.fs)) for l, r in d.get("eqs", [])]
        vs = [S(v, st.fs) for v in d.get("vars", [])]
        res = solve_fangchengzu(eqs, vs, st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/inequality", methods=["POST"])
def inequality():
    from functions.solvers import solve_budengshi
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        lhs = S(d.get("lhs", ""), st.fs)
        rhs = S(d.get("rhs", ""), st.fs)
        rel = Rel(lhs, rhs, d.get("op", ">="))
        res = solve_budengshi(rel, d.get("var", "x"), d.get("domain", "Reals"), st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/inequality_system", methods=["POST"])
def inequality_system():
    from functions.solvers import solve_budengshizu
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        rels = list(st.rels.values())
        if not rels:
            return j(err("请先在不等式设置中至少添加一条不等式"))
        var = S(d.get("var", "x"), st.fs)
        res = solve_budengshizu(rels, var, st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/latex2expr", methods=["POST"])
def latex2expr():
    """将 LaTeX 代码解析为原生 SymPy 表达式字符串（与桌面版公式输入对话框一致）。

    桌面版行为：拿到 MathLive 的 LaTeX 后执行 sympify('$' + latex)，
    再把 str(expr) 填回输入框 —— 即"原生 Sympy 表达式"。本接口复刻该行为，
    供页面底部 MathLive 虚拟键盘的"插入"按钮调用。
    
    使用空函数字典 {} 避免将 LaTeX 中的未知函数（如微分方程中的 f(x)）
    误替换为已定义的保存函数。
    """
    d = request.get_json(force=True, silent=True) or {}
    try:
        text = (d.get("latex") or "").strip()
        if not text:
            return j(err("LaTeX 内容为空"))
        if not text.startswith("$"):
            text = "$" + text
        # 使用空函数字典，避免将 LaTeX 中的函数误替换为已保存函数
        expr = S(text, {})
        # ok(): latex 供前端预览渲染；text 为原生 SymPy 表达式，插入输入框
        return j(ok(to_latex(expr), text=str(expr)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/expr2latex", methods=["POST"])
def expr2latex():
    """将原生 SymPy 表达式（或 '$'+LaTeX）转换为 LaTeX，供前端预览浮层渲染。

    输入框在通过虚拟键盘“插入”后会保存为原生 SymPy 表达式（如 x**2+1），
    而前端预览浮层使用 MathJax 渲染、只接受 LaTeX。本接口补全反向转换，
    让预览框既能显示用户直接键入的 LaTeX（$ 前缀），也能渲染 SymPy 表达式。
    """
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        text = (d.get("expr") or "").strip()
        if not text:
            return j(err("表达式为空"))
        # S() 内部识别 '$' 前缀：带 $ -> 按 LaTeX 解析；否则按原生 SymPy 解析
        expr = S(text, st.fs)
        return j(ok(to_latex(expr)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/calculate", methods=["POST"])
def calculate():
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    engine = int(d.get("engine", 0))
    text = d.get("expr", "")
    try:
        if engine == 0:
            result = eval(text, {"__builtins__": __builtins__}, {})  # noqa: S307
            result = to_latex(result)
        elif engine == 1:
            import mpmath as mp
            mp.mp.dps = int(d.get("precision", 16) or 16)
            result = to_latex(eval(text, {"__builtins__": {}}, mp.__dict__))  # noqa: S307
        elif engine == 2:
            result = to_latex(radsimp(S(text, st.fs, is_simplify=True)))
        else:
            result = to_latex(latex(S(text, {})))
        return j(ok(result))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/triangle", methods=["POST"])
def triangle():
    from functions.solvers import solve_sanjiaoxing
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        angles = {}
        sides = {}
        for c in d.get("conds", []):
            idx = int(c.get("type"))
            val = S(c.get("value", ""), st.fs)
            if 1 <= idx <= 3:
                angles["ABC"[idx - 1]] = val
            else:
                sides["abc"[idx - 4]] = val
        if len(angles) + len(sides) != 3:
            return j(err("请填入恰好 3 个有效且不重复的条件"))
        res = solve_sanjiaoxing(angles, sides, st.fs)
        if isinstance(res, list):
            lines = []
            for i, sol in enumerate(res):
                ang, sid = sol
                parts = []
                for k in "ABC":
                    if ang.get(k) is not None:
                        parts.append("%s=%s" % (k, to_latex(ang[k])))
                for k in "abc":
                    if sid.get(k) is not None:
                        parts.append("%s=%s" % (k, to_latex(sid[k])))
                line = ", ".join(parts)
                if len(res) > 1:
                    line = r"\text{解%s}:\ " % (i + 1) + line
                lines.append(line)
            latex_str = r" \\ ".join(lines)
        elif isinstance(res, str):
            latex_str = res
        else:
            latex_str = "无解"
        return j(ok(latex_str))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/funcattr", methods=["POST"])
def funcattr():
    from functions.functions import get_function_attr
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        # get_function_attr 内部会自行 sympify（含定义域）
        f = d.get("expr", "")
        s = d.get("var", "x")
        res = get_function_attr(f, s, d.get("domain", "") or "Reals", int(d.get("attr", 0)), st.fs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/geometry", methods=["POST"])
def geometry_calc():
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    kind = d.get("kind", "plane")
    method = int(d.get("method", 0))
    params = d.get("params", "") or ""
    try:
        if kind == "plane":
            res = geometry.compute_plane(method, params, st.fs, st.pjs)
        else:
            res = geometry.compute_solid(method, params, st.fs, st.ljs)
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


# ------------------------- 向量运算 -------------------------
def _vec(name, st):
    v = st.vs.get(name)
    if not v:
        raise ValueError("未找到向量 '%s'" % name)
    return S(v[1], st.fs), S(v[2], st.fs)


@api.route("/api/vector_compute", methods=["POST"])
def vector_compute():
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    op = d.get("op")
    try:
        x1, y1 = _vec(d.get("v1"), st)
        if op in ("add", "sub"):
            x2, y2 = _vec(d.get("v2"), st)
            res = [x1 + x2, y1 + y2] if op == "add" else [x1 - x2, y1 - y2]
        elif op == "scalar":
            c = S(d.get("scalar", "1"), st.fs)
            res = [c * x1, c * y1]
        elif op == "dot":
            x2, y2 = _vec(d.get("v2"), st)
            res = x1 * x2 + y1 * y2
        elif op == "cross":
            x2, y2 = _vec(d.get("v2"), st)
            res = x1 * y2 - y1 * x2
        elif op == "length":
            res = sqrt(x1 ** 2 + y1 ** 2)
        elif op == "angle":
            x2, y2 = _vec(d.get("v2"), st)
            res = acos((x1 * x2 + y1 * y2) / (sqrt(x1 ** 2 + y1 ** 2) * sqrt(x2 ** 2 + y2 ** 2)))
        elif op == "projection":
            x2, y2 = _vec(d.get("v2"), st)
            dot = x1 * x2 + y1 * y2
            l2 = x2 ** 2 + y2 ** 2
            res = [(dot / l2) * x2, (dot / l2) * y2]
        elif op == "unit":
            l = sqrt(x1 ** 2 + y1 ** 2)
            res = [x1 / l, y1 / l]
        else:
            return j(err("未知的向量运算"))
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/vector_attr", methods=["POST"])
def vector_attr():
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    attr = int(d.get("attr", 0))
    try:
        x, y = _vec(d.get("name"), st)
        if attr == 0:
            res = [x, y]
        elif attr == 1:
            res = sqrt(x ** 2 + y ** 2)
        elif attr == 2:
            res = atan2(y, x)
        elif attr == 3:
            l = sqrt(x ** 2 + y ** 2)
            res = [x / l, y / l]
        else:
            res = [x, y]
        return j(ok(to_latex(res)))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


# ========================= 绘图类接口 =========================
def plot_functions(items, opts):
    import numpy as np
    import matplotlib.pyplot as plt
    from sympy import lambdify

    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    if not opts.get("show_axis", True):
        ax.set_axis_off()
    if opts.get("show_grid", True):
        ax.grid(True, alpha=0.3)
    for it in items:
        try:
            expr = S(it["expr"], {})
            var = it.get("var", "x")
            f = lambdify(Symbol(var), expr, "numpy")
            a = float(S(it["a"], {}))
            b = float(S(it["b"], {}))
            xs = np.linspace(a, b, 2000)
            ys = f(xs)
            ax.plot(xs, ys, label=it.get("expr", ""), color=it.get("color") or None)
        except Exception:
            continue
    if items:
        ax.legend()
    if opts.get("xlim"):
        ax.set_xlim(opts["xlim"])
    if opts.get("ylim"):
        ax.set_ylim(opts["ylim"])
    return fig


@api.route("/api/plot/func", methods=["POST"])
def plot_func():
    d = request.get_json(force=True, silent=True) or {}
    try:
        fig = plot_functions(d.get("items", []), d.get("opts", {}))
        return j({"ok": True, "image": fig_to_png(fig)})
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/plot/pjs", methods=["POST"])
def plot_pjs():
    from functions.paint2D import draw2d
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        theme = d.get("theme", "light")
        objects = [(st.pjs[n][1], None) for n in d.get("names", []) if n in st.pjs]
        fig = draw2d(objects, theme=theme)
        return j({"ok": True, "image": fig_to_png(fig)})
    except Exception as e:  # noqa: BLE001
        return j(err(e))


@api.route("/api/plot/ljs", methods=["POST"])
def plot_ljs():
    from functions.paint3D import draw3d
    d = request.get_json(force=True, silent=True) or {}
    st = current_state()
    try:
        theme = d.get("theme", "light")
        objects = [(st.ljs[n][1], None) for n in d.get("names", []) if n in st.ljs]
        fig = draw3d(objects, theme=theme)
        return j({"ok": True, "image": fig_to_png(fig)})
    except Exception as e:  # noqa: BLE001
        return j(err(e))


# ========================= 状态 / 缓存 / 存档 =========================
@api.route("/api/state", methods=["GET"])
def state_info():
    st = current_state()
    return j({
        "ok": True,
        "fs": list(st.fs.keys()),
        "vs": list(st.vs.keys()),
        "eqs": list(st.eqs.keys()),
        "rels": list(st.rels.keys()),
        "pjs": {k: v[0] for k, v in st.pjs.items()},
        "ljs": {k: v[0] for k, v in st.ljs.items()},
        "cache": st.cache,
    })


@api.route("/api/cache", methods=["POST"])
def cache_add():
    d = request.get_json(force=True, silent=True) or {}
    latex_str = d.get("latex", "")
    text = d.get("text", latex_str)
    st = current_state()
    st.cache.append([latex_str, text])
    return j(ok("已加入缓存"))


@api.route("/api/cache", methods=["GET"])
def cache_list():
    return j({"ok": True, "cache": current_state().cache})


@api.route("/api/cache", methods=["DELETE"])
def cache_clear():
    current_state().cache = []
    return j(ok("已清空缓存"))


@api.route("/api/save", methods=["GET"])
def save():
    data = current_state().to_dict()
    return Response(
        __import__("json").dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=calc_save.json"},
    )


@api.route("/api/load", methods=["POST"])
def load():
    d = request.get_json(force=True, silent=True) or {}
    try:
        current_state().load_dict(d)
        return j(ok("已从存档加载"))
    except Exception as e:  # noqa: BLE001
        return j(err(e))


# ========================= Blockly 积木编辑器执行 =========================
def _blockly_format_value(value):
    """将任意值转为 (显示文本, 是否为 LaTeX) 二元组，与桌面端桥接保持一致。"""
    if value is None:
        return ("", False)
    if isinstance(value, dict):
        items = [(k, _blockly_format_value(v)) for k, v in value.items()]
        parts = ["{}={}".format(k, t) for k, (t, _) in items]
        return (r",\ ".join(parts), any(f for _, f in items))
    if isinstance(value, (list, tuple, set)):
        items = [_blockly_format_value(v) for v in value]
        parts = [t for t, _ in items]
        return (r"\ \ \ ".join(parts), any(f for _, f in items))
    if isinstance(value, str):
        if value.strip():
            try:
                from sympy import latex as _latex, sympify as _sympify
                return (_latex(_sympify(value)), True)
            except Exception:
                pass
        return (value, False)
    try:
        from sympy import latex as _latex
        return (_latex(value), True)
    except Exception:
        return (str(value), False)


@api.route("/api/blockly/run", methods=["POST"])
def blockly_run():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "")
    inputs = data.get("inputs") or {}
    state = current_state()
    fs = state.fs

    # 让积木生成的 `from functions import get_function_attr` 在 web 包结构下可用：
    # 把 get_function_attr 挂到 functions 模块上，使该 import 语句能解析。
    import functions as _functions_pkg
    from functions.functions import get_function_attr as _gfa
    _functions_pkg.get_function_attr = _gfa

    outputs = []

    def py_output(name, value):
        text, is_latex = _blockly_format_value(value)
        outputs.append({"name": name, "text": text, "latex": is_latex})

    def get_input(name):
        return inputs.get(name, "")

    def define_func(name, expr, domain, var):
        from core.sympify import sympify
        if not name or not expr:
            return "错误：函数名称和表达式不能为空"
        try:
            body = str(sympify(expr, fs))
        except Exception as err:  # noqa: BLE001
            return "错误：函数表达式无效 - {}".format(err)
        fs[name] = [name, body, domain or "Reals", var or "x"]
        return "已定义函数 {}({}) = {}".format(name, var or "x", body)

    def py_simplifies(expr, method, zhuyuan="", huanyuan="", huanyuanshi=""):
        from functions.simplification import simplifies
        return simplifies(expr, int(method), zhuyuan or None,
                          huanyuan or None, huanyuanshi or None, fs)

    def py_solve_fangchengzu(eqs, vars_text):
        from functions.solvers import solve_fangchengzu
        from core.sympify import sympify
        from sympy import Eq, Symbol
        eq_list = [Eq(sympify(e, fs), 0) for e in eqs]
        var_list = [Symbol(s.strip()) for s in vars_text.split(",") if s.strip()]
        return solve_fangchengzu(eq_list, var_list, fs)

    def py_solve_budengshi(lhs, op, rhs, var, domain="Reals"):
        from functions.solvers import solve_budengshi
        from core.sympify import sympify
        from sympy import Rel
        rel = Rel(sympify(lhs, fs), sympify(rhs, fs), op)
        return solve_budengshi(rel, var, domain or "Reals", fs)

    def py_solve_budengshizu(items, var):
        from functions.solvers import solve_budengshizu
        from core.sympify import sympify
        from sympy import Rel, Symbol
        rels = [Rel(sympify(l, fs), sympify(r, fs), o) for (l, o, r) in items]
        return solve_budengshizu(rels, Symbol(var), fs)

    def py_solve_triangle(*conds):
        from functions.solvers import solve_sanjiaoxing
        from core.sympify import sympify
        angles, sides = {}, {}
        mapping = {"A": ("A", angles), "B": ("B", angles), "C": ("C", angles),
                   "a": ("a", sides), "b": ("b", sides), "c": ("c", sides)}
        for kind, val in conds:
            key = (kind or "").strip()
            if not key or key not in mapping or not val:
                continue
            target_key, target = mapping[key]
            target[target_key] = sympify(val, fs)
        return solve_sanjiaoxing(angles, sides, fs)

    def py_calc(expr):
        from core.sympify import sympify
        from sympy import radsimp
        return radsimp(sympify(expr, fs, is_simplify=True))

    def py_func_value(name, arg=""):
        from core.sympify import sympify
        from sympy import symbols
        if not name or name not in fs:
            return "未定义函数: {}".format(name or "?")
        body = fs[name][1]
        var = fs[name][3]
        expr = sympify(body, fs)
        if not arg:
            return expr
        return expr.subs(symbols(var), sympify(arg, fs))

    env = {
        "fs": fs,
        "get_input": get_input,
        "py_output": py_output,
        "define_func": define_func,
        "py_simplifies": py_simplifies,
        "py_solve_fangchengzu": py_solve_fangchengzu,
        "py_solve_budengshi": py_solve_budengshi,
        "py_solve_budengshizu": py_solve_budengshizu,
        "py_solve_triangle": py_solve_triangle,
        "py_calc": py_calc,
        "py_func_value": py_func_value,
    }

    error = None
    try:
        # 优先按单表达式执行（生成器大多产出表达式积木）。
        eval(compile(code, "<blockly>", "eval"), env)
    except SyntaxError:
        # 多语句代码：捕获标准输出，并捕获运行异常。
        import io as _io
        import sys as _sys
        out = _io.StringIO()
        old = _sys.stdout
        try:
            _sys.stdout = out
            exec(code, env)
        except Exception as err:  # noqa: BLE001
            error = "执行错误: {}".format(err)
        finally:
            _sys.stdout = old
        captured = out.getvalue()
        if captured:
            for line in captured.splitlines():
                if line.strip():
                    outputs.append({"name": "输出", "text": line, "latex": False})
    except Exception as err:  # noqa: BLE001
        error = "执行错误: {}".format(err)

    return j(ok({
        "outputs": outputs,
        "error": error,
        "message": error or "执行完成",
        "functions": list(fs.keys()),
    }))
