"""每个浏览器会话的共享状态（函数定义、方程、向量、几何对象、缓存）。"""
import threading
import uuid


class CalcState:
    def __init__(self):
        # 函数定义：name -> [name, expr, domain, var]
        self.fs = {}
        # 方程定义：key -> sympy Eq
        self.eqs = {}
        # 不等式定义：key -> sympy Rel
        self.rels = {}
        # 向量定义：name -> [name, x_str, y_str]
        self.vs = {}
        # 平面几何对象：name -> (类别, sympy 对象)
        self.pjs = {}
        # 立体几何对象：name -> (类别, sympy 对象)
        self.ljs = {}
        # 缓存区：列表，元素为 [latex, text]
        self.cache = []

    def to_dict(self):
        """导出为可 JSON 序列化的字典。

        与桌面版 .cca 存档格式保持一致：函数表达式保存原始字符串，
        读取后再由 core.sympify 重新解析，确保往返无损。
        """
        fs = {}
        for k, v in self.fs.items():
            fs[k] = [v[0], v[1], v[2], v[3]]
        return {
            "fs": fs,
            "eqs": {k: [latex_safe(v.lhs), latex_safe(v.rhs), str(v.rel_op)]
                    for k, v in self.eqs.items()},
            "rels": {k: [latex_safe(v.lhs), latex_safe(v.rhs), str(v.rel_op)]
                     for k, v in self.rels.items()},
            "vs": dict(self.vs),
            "pjs": {k: [v[0]] for k, v in self.pjs.items()},
            "ljs": {k: [v[0]] for k, v in self.ljs.items()},
            "cache": list(self.cache),
        }

    def load_dict(self, data):
        from sympy import Eq, Rel
        self.fs = {}
        self.eqs = {}
        self.rels = {}
        self.vs = dict(data.get("vs", {}))
        self.pjs = {}
        self.ljs = {}
        # 缓存区：兼容 Web 版（[latex, text]）与桌面版（纯字符串列表）两种格式
        self.cache = []
        for item in data.get("cache", []):
            if isinstance(item, (list, tuple)):
                a = str(item[0]) if len(item) > 0 else ""
                b = str(item[1]) if len(item) > 1 else a
                self.cache.append([a, b])
            else:
                s = str(item)
                self.cache.append([s, s])
        for k, v in data.get("fs", {}).items():
            self.fs[k] = [v[0], v[1], v[2], v[3]]  # 表达式以字符串保存，计算时再解析
        # 方程：兼容 Web 版（{key: [lhs, rhs, op]}）与桌面版（Eq 字符串列表）
        eqs = data.get("eqs", {})
        if isinstance(eqs, dict):
            for k, v in eqs.items():
                try:
                    self.eqs[k] = Eq(S_latex(v[0]), S_latex(v[1]))
                except Exception:
                    pass
        elif isinstance(eqs, list):
            for i, v in enumerate(eqs):
                try:
                    self.eqs[str(i)] = S_latex(v) if isinstance(v, str) else Eq(S_latex(v[0]), S_latex(v[1]))
                except Exception:
                    pass
        # 不等式：兼容两种格式
        rels = data.get("rels", {})
        if isinstance(rels, dict):
            for k, v in rels.items():
                try:
                    self.rels[k] = Rel(S_latex(v[0]), S_latex(v[1]), v[2])
                except Exception:
                    pass
        elif isinstance(rels, list):
            for i, v in enumerate(rels):
                try:
                    self.rels[str(i)] = S_latex(v) if isinstance(v, str) else Rel(S_latex(v[0]), S_latex(v[1]), v[2])
                except Exception:
                    pass
        # 平面/立体几何对象：Web 版仅保存类别；桌面版含 sympy 字符串，可尝试还原
        for k, v in data.get("pjs", {}).items():
            if isinstance(v, (list, tuple)) and len(v) > 1:
                try:
                    self.pjs[k] = [v[0], S_latex(v[1])]
                    continue
                except Exception:
                    pass
            self.pjs[k] = [v[0]]
        for k, v in data.get("ljs", {}).items():
            if isinstance(v, (list, tuple)) and len(v) > 1:
                try:
                    self.ljs[k] = [v[0], S_latex(v[1])]
                    continue
                except Exception:
                    pass
            self.ljs[k] = [v[0]]


def latex_safe(expr):
    from sympy import latex
    try:
        return latex(expr)
    except Exception:
        return str(expr)


def S_latex(text):
    from core.sympify import sympify
    from sympy import Basic as SympyBasic
    if isinstance(text, SympyBasic):
        return text
    r = sympify(text, {})
    if isinstance(r, str) and text and text[0] != "$":
        # sympify 无法解析（如 Web 版存档中的 LaTeX 字符串），尝试 latex2sympy
        try:
            return sympify("$" + text, {})
        except Exception:
            pass
    return r


_STATES = {}
_LOCK = threading.Lock()


def get_state(sid):
    with _LOCK:
        s = _STATES.get(sid)
        if s is None:
            s = CalcState()
            _STATES[sid] = s
        return s


def new_state():
    sid = uuid.uuid4().hex
    with _LOCK:
        _STATES[sid] = CalcState()
    return sid


def drop_state(sid):
    with _LOCK:
        _STATES.pop(sid, None)
