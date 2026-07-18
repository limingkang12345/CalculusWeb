"""Web 版存档/读档 —— 基于 JSON 文件下载/上传。"""
import json
from io import BytesIO
from core.sympify import sympify


def export_project(state):
    """将会话状态导出为 JSON 字符串。"""
    output = {}

    # 函数列表
    output["fs"] = state.get("fs", {})

    # 方程列表
    output["eqs"] = list(state.get("eqs", {}).keys())

    # 不等式列表
    output["rels"] = list(state.get("rels", {}).keys())

    # 向量列表
    output["vs"] = state.get("vs", {})

    # 缓存区
    output["cache"] = state.get("cache", [])

    # 平面几何对象
    pjs = state.get("pjs", {})
    pjs_save = {}
    for k, v in pjs.items():
        cat = v[0]
        pjs_save[k] = [cat, repr(v[1])]
    output["pjs"] = pjs_save

    # 立体几何对象
    ljs = state.get("ljs", {})
    ljs_save = {}
    for k, v in ljs.items():
        cat = v[0]
        ljs_save[k] = [cat, repr(v[1])]
    output["ljs"] = ljs_save

    return json.dumps(output, ensure_ascii=False)


def import_project(json_str, fs):
    """从 JSON 字符串导入项目状态。"""
    from sympy import Line, Circle
    from sympy.geometry import Line3D, Plane

    json_data = json.loads(json_str)
    state = {}

    state["fs"] = json_data.get("fs", {})
    _fs = state["fs"]

    # 方程/不等式列表
    state["eqs"] = {i: sympify(i, _fs) for i in json_data.get("eqs", [])}
    state["rels"] = {i: sympify(i, _fs) for i in json_data.get("rels", [])}

    # 向量列表
    state["vs"] = json_data.get("vs", {})

    # 缓存区
    state["cache"] = list(json_data.get("cache", []))

    # 平面几何对象
    pjs = {}
    for k, v in json_data.get("pjs", {}).items():
        cat, val_str = v[0], v[1]
        try:
            obj = sympify(val_str, _fs)
            # 向后兼容：旧格式用 equation() 存了线和圆的方程字符串
            if cat == "直线" and not isinstance(obj, Line):
                obj = Line(sympify(val_str, _fs))
            elif cat == "圆" and not isinstance(obj, Circle):
                obj = Circle(sympify(val_str, _fs))
        except Exception:
            obj = None
        if obj is not None:
            pjs[k] = (cat, obj)
    state["pjs"] = pjs

    # 立体几何对象
    ljs = {}
    for k, v in json_data.get("ljs", {}).items():
        cat, val_str = v[0], v[1]
        try:
            obj = sympify(val_str, _fs)
            if cat == "直线" and not isinstance(obj, Line3D):
                obj = Line3D(sympify(val_str, _fs))
            elif cat == "平面" and not isinstance(obj, Plane):
                obj = Plane(sympify(val_str, _fs))
        except Exception:
            obj = None
        if obj is not None:
            ljs[k] = (cat, obj)
    state["ljs"] = ljs

    return state
