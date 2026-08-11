"""工具函数：表达式解析、结果转 LaTeX、绘图转图片等。"""
import io
import base64

import matplotlib

matplotlib.use("Agg")  # 服务端无显示器，使用 Agg 后端
import matplotlib.pyplot as plt
from sympy import latex, Point, Point3D

from core.sympify import sympify as _sympify


def S(text, fs=None, **kw):
    """将用户输入（LaTeX / 文本）解析为 sympy 对象。"""
    return _sympify(text, fs, **kw)


def to_latex(r):
    """将计算结果转换为可在 MathJax 中渲染的 LaTeX 字符串。"""
    if r is None:
        return ""
    if isinstance(r, str):
        return r
    if isinstance(r, bool):
        return r"\text{真}" if r else r"\text{假}"
    # mpmath 浮点
    if hasattr(r, "_mpf_"):
        r = float(r)
    if isinstance(r, float):
        if r == int(r):
            return str(int(r))
        return repr(r)
    if isinstance(r, (Point, Point3D)):
        return r"\left(" + ", ".join(latex(c) for c in r) + r"\right)"
    if isinstance(r, dict):
        items = ", ".join(to_latex(k) + "=" + to_latex(v) for k, v in r.items())
        return r"\left\{" + items + r"\right\}"
    if isinstance(r, (list, tuple)):
        if len(r) == 0:
            return r"[]" if isinstance(r, list) else r"()"
        inner = ", ".join(to_latex(x) for x in r)
        if isinstance(r, list):
            return r"\left[" + inner + r"\right]"
        return r"\left(" + inner + r"\right)"
    try:
        return latex(r)
    except Exception:
        return str(r)


def fig_to_png(fig):
    """将 matplotlib Figure 转为 base64 PNG data url。"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=fig.dpi)
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def ok(latex_str, text=None):
    return {"ok": True, "latex": latex_str, "text": text if text is not None else latex_str}


def err(msg):
    return {"ok": False, "error": str(msg)}
