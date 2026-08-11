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
        self.cache = list(data.get("cache", []))
        for k, v in data.get("fs", {}).items():
            self.fs[k] = [v[0], v[1], v[2], v[3]]  # 表达式以字符串保存，计算时再解析
        for k, v in data.get("eqs", {}).items():
            self.eqs[k] = Eq(S_latex(v[0]), S_latex(v[1]))
        for k, v in data.get("rels", {}).items():
            self.rels[k] = Rel(S_latex(v[0]), S_latex(v[1]), v[2])
        # 平面/立体几何对象含 sympy 几何对象，无法纯文本还原，仅保留可重建的参数较复杂，
        # 这里采用简化处理：不跨会话保存几何对象（与桌面“保存/加载”仅保存函数定义一致）。


def latex_safe(expr):
    from sympy import latex
    try:
        return latex(expr)
    except Exception:
        return str(expr)


def S_latex(text):
    from core.sympify import sympify
    return sympify(text, None)


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
