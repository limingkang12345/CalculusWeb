"""平面几何与立体几何：对象创建与计算，移植自原 ui/pjjisuan.py、ui/ljjisuan.py、
ui/dingyi_pj.py、ui/dingyi_lj.py，数学行为与原版完全一致。"""
from sympy import Line, Line3D
from sympy.geometry import Point as SymPoint
from core.sympify import sympify


# ------------------------- 平面几何查找辅助 -------------------------
def _find_point(pjs, name):
    n = name.strip()
    if n in pjs and pjs[n][0] == "点":
        return pjs[n][1]
    raise ValueError("未找到点 '%s'" % n)


def _find_line(pjs, name):
    n = name.strip()
    if n in pjs and pjs[n][0] == "直线":
        return pjs[n][1]
    raise ValueError("未找到直线 '%s'" % n)


def _find_segment(pjs, name):
    n = name.strip()
    if n in pjs and pjs[n][0] == "线段":
        return pjs[n][1]
    raise ValueError("未找到线段 '%s'" % n)


def _find_triangle(pjs, name):
    n = name.strip()
    if n in pjs and pjs[n][0] == "三角形":
        return pjs[n][1]
    raise ValueError("未找到三角形 '%s'" % n)


def _find_circle(pjs, name):
    n = name.strip()
    if n in pjs and pjs[n][0] == "圆":
        return pjs[n][1]
    raise ValueError("未找到圆 '%s'" % n)


def _find_points(pjs, names_str):
    return [_find_point(pjs, p) for p in names_str.split(",")]


# ------------------------- 平面几何对象创建 -------------------------
def create_plane_object(idx, name, params_str, fs, pjs):
    raw = [p.strip() for p in params_str.split(",")] if params_str else []
    from functions.planes import (
        create_point, create_line, create_circle, create_circle_three_points,
        create_triangle, create_polygon, circle_with_diameter,
        circle_by_center_and_point, perpendicular_bisector,
        line_parallel_through_point, line_perpendicular_through_point,
        angle_bisector_line, angle_bisector, triangle_median,
        triangle_altitude, triangle_midsegment, triangle_incircle,
        triangle_excircle, segment_from_points,
    )
    if idx == 1:
        return ("点", create_point(raw[0], raw[1], fs))
    elif idx == 2:
        p1, p2 = _find_points(pjs, raw[0] + "," + raw[1])
        return ("直线", create_line(p1, p2))
    elif idx == 3:
        center = _find_point(pjs, raw[0])
        return ("圆", create_circle(center, raw[1], fs))
    elif idx == 4:
        pts = _find_points(pjs, raw[0] + "," + raw[1] + "," + raw[2])
        return ("圆", create_circle_three_points(*pts))
    elif idx == 5:
        pts = _find_points(pjs, raw[0] + "," + raw[1] + "," + raw[2])
        return ("三角形", create_triangle(*pts))
    elif idx == 6:
        pts = _find_points(pjs, ",".join(raw))
        return ("多边形", create_polygon(pts))
    elif idx == 7:
        pts = _find_points(pjs, raw[0] + "," + raw[1])
        return ("圆", circle_with_diameter(*pts))
    elif idx == 8:
        pts = _find_points(pjs, raw[0] + "," + raw[1])
        return ("圆", circle_by_center_and_point(pts[0], pts[1]))
    elif idx == 9:
        seg = _find_segment(pjs, raw[0])
        return ("直线", perpendicular_bisector(seg.points[0], seg.points[1]))
    elif idx == 10:
        pts = _find_points(pjs, raw[0])
        line_ref = None
        try:
            line_ref = _find_line(pjs, raw[1])
        except ValueError:
            seg = _find_segment(pjs, raw[1])
            line_ref = Line(seg.points[0], seg.points[1])
        return ("直线", line_parallel_through_point(line_ref, pts[0]))
    elif idx == 11:
        pts = _find_points(pjs, raw[0])
        line_ref = None
        try:
            line_ref = _find_line(pjs, raw[1])
        except ValueError:
            seg = _find_segment(pjs, raw[1])
            line_ref = Line(seg.points[0], seg.points[1])
        return ("直线", line_perpendicular_through_point(line_ref, pts[0]))
    elif idx == 12:
        l1 = _find_line(pjs, raw[0])
        l2 = _find_line(pjs, raw[1])
        res = angle_bisector_line(l1, l2)
        if isinstance(res, str):
            raise ValueError(res)
        return ("直线", res)
    elif idx == 13:
        pts = _find_points(pjs, raw[0] + "," + raw[1] + "," + raw[2])
        return ("直线", angle_bisector(*pts))
    elif idx == 14:
        tri = _find_triangle(pjs, raw[0])
        return ("线段", triangle_median(tri, int(raw[1])))
    elif idx == 15:
        tri = _find_triangle(pjs, raw[0])
        return ("直线", triangle_altitude(tri, int(raw[1])))
    elif idx == 16:
        tri = _find_triangle(pjs, raw[0])
        return ("线段", triangle_midsegment(tri))
    elif idx == 17:
        tri = _find_triangle(pjs, raw[0])
        return ("圆", triangle_incircle(tri))
    elif idx == 18:
        tri = _find_triangle(pjs, raw[0])
        return ("圆", triangle_excircle(tri, int(raw[1])))
    elif idx == 19:
        pts = _find_points(pjs, raw[0] + "," + raw[1])
        return ("线段", segment_from_points(*pts))
    raise ValueError("未知的平面几何创建方法")


# ------------------------- 平面几何计算 -------------------------
def compute_plane(idx, params_str, fs, pjs):
    raw = [p.strip() for p in params_str.split(",")]
    from sympy import radsimp, simplify
    from functions.planes import (
        point_distance, midpoint, collinear_check, translate_point,
        rotate_point, reflect_point, line_equation, line_slope,
        line_intersection, point_to_line_distance, angle_between_lines,
        parallel_check, perpendicular_check, circle_area_func,
        circle_circumference, circle_intersection, circle_tangent_lines,
        triangle_area, triangle_perimeter, triangle_circumcenter,
        triangle_circumradius, triangle_incenter, triangle_inradius,
        triangle_centroid, triangle_orthocenter, triangle_is_right,
        triangle_is_isosceles, triangle_is_equilateral,
        polygon_area_func, polygon_perimeter_func,
    )

    def get_point(n):
        return _find_point(pjs, n)

    def get_line_points(*params):
        if len(params) == 1:
            n = params[0].strip()
            if n in pjs and pjs[n][0] == "直线":
                return pjs[n][1].points[0], pjs[n][1].points[1]
        return tuple(get_point(p) for p in params[:2])

    def get_circle(n):
        return _find_circle(pjs, n)

    def get_triangle_points(*params):
        if len(params) == 1:
            n = params[0].strip()
            if n in pjs and pjs[n][0] == "三角形":
                return pjs[n][1].vertices
        return tuple(get_point(p) for p in params[:3])

    if idx == 1:
        return point_distance(get_point(raw[0]), get_point(raw[1]))
    elif idx == 2:
        return midpoint(get_point(raw[0]), get_point(raw[1]))
    elif idx == 3:
        return collinear_check([get_point(p) for p in raw])
    elif idx == 4:
        return translate_point(get_point(raw[0]), raw[1], raw[2], fs)
    elif idx == 5:
        return rotate_point(get_point(raw[0]), raw[1], get_point(raw[2]), fs)
    elif idx == 6:
        pt = get_point(raw[0])
        lp = get_line_points(*raw[1:])
        return reflect_point(pt, lp[0], lp[1])
    elif idx == 7:
        return line_equation(get_point(raw[0]), get_point(raw[1]))
    elif idx == 8:
        return line_slope(get_point(raw[0]), get_point(raw[1]))
    elif idx == 9:
        if len(raw) <= 2:
            lp1 = get_line_points(raw[0]); lp2 = get_line_points(raw[1])
        else:
            lp1 = get_line_points(raw[0], raw[1]); lp2 = get_line_points(raw[2], raw[3])
        return line_intersection(lp1[0], lp1[1], lp2[0], lp2[1])
    elif idx == 10:
        pt = get_point(raw[0]); lp = get_line_points(*raw[1:])
        return point_to_line_distance(pt, lp[0], lp[1])
    elif idx == 11:
        if len(raw) <= 2:
            lp1 = get_line_points(raw[0]); lp2 = get_line_points(raw[1])
        else:
            lp1 = get_line_points(raw[0], raw[1]); lp2 = get_line_points(raw[2], raw[3])
        return angle_between_lines(lp1[0], lp1[1], lp2[0], lp2[1])
    elif idx == 12:
        if len(raw) <= 2:
            lp1 = get_line_points(raw[0]); lp2 = get_line_points(raw[1])
        else:
            lp1 = get_line_points(raw[0], raw[1]); lp2 = get_line_points(raw[2], raw[3])
        return parallel_check(lp1[0], lp1[1], lp2[0], lp2[1])
    elif idx == 13:
        if len(raw) <= 2:
            lp1 = get_line_points(raw[0]); lp2 = get_line_points(raw[1])
        else:
            lp1 = get_line_points(raw[0], raw[1]); lp2 = get_line_points(raw[2], raw[3])
        return perpendicular_check(lp1[0], lp1[1], lp2[0], lp2[1])
    elif idx == 14:
        c = get_circle(raw[0]); return (radsimp(c.center.x), radsimp(c.center.y))
    elif idx == 15:
        c = get_circle(raw[0]); return radsimp(c.radius)
    elif idx == 16:
        c = get_circle(raw[0]); return radsimp(c.area)
    elif idx == 17:
        c = get_circle(raw[0]); return radsimp(c.circumference)
    elif idx == 18:
        c1, c2 = get_circle(raw[0]), get_circle(raw[1])
        inter = c1.intersection(c2)
        result = [(radsimp(pt.x), radsimp(pt.y)) for pt in inter]
        return result if result else "两圆不相交"
    elif idx == 19:
        pt = get_point(raw[0]); c = get_circle(raw[1])
        tangents = c.tangent_lines(pt)
        result = [simplify(line.equation()) for line in tangents]
        return result if result else "无切线"
    elif idx == 20:
        v = get_triangle_points(*raw); return triangle_area(*v)
    elif idx == 21:
        v = get_triangle_points(*raw); return triangle_perimeter(*v)
    elif idx == 22:
        v = get_triangle_points(*raw); return triangle_circumcenter(*v)
    elif idx == 23:
        v = get_triangle_points(*raw); return triangle_circumradius(*v)
    elif idx == 24:
        v = get_triangle_points(*raw); return triangle_incenter(*v)
    elif idx == 25:
        v = get_triangle_points(*raw); return triangle_inradius(*v)
    elif idx == 26:
        v = get_triangle_points(*raw); return triangle_centroid(*v)
    elif idx == 27:
        v = get_triangle_points(*raw); return triangle_orthocenter(*v)
    elif idx == 28:
        v = get_triangle_points(*raw); return triangle_is_right(*v)
    elif idx == 29:
        v = get_triangle_points(*raw); return triangle_is_isosceles(*v)
    elif idx == 30:
        v = get_triangle_points(*raw); return triangle_is_equilateral(*v)
    elif idx == 31:
        pts = [get_point(p) for p in raw]; return polygon_area_func(pts)
    elif idx == 32:
        pts = [get_point(p) for p in raw]; return polygon_perimeter_func(pts)
    raise ValueError("未知的操作")


# ------------------------- 立体几何查找辅助 -------------------------
def _find_point3d(ljs, name):
    n = name.strip()
    if n in ljs and ljs[n][0] == "点":
        return ljs[n][1]
    raise ValueError("未找到三维点 '%s'" % n)


def _find_line3d(ljs, name):
    n = name.strip()
    if n in ljs and ljs[n][0] == "直线":
        return ljs[n][1]
    raise ValueError("未找到三维直线 '%s'" % n)


def _find_plane(ljs, name):
    n = name.strip()
    if n in ljs and ljs[n][0] == "平面":
        return ljs[n][1]
    raise ValueError("未找到平面 '%s'" % n)


def _find_points3d(ljs, names_str):
    return [_find_point3d(ljs, p) for p in names_str.split(",")]


def _line3d_from(ljs, *params):
    if len(params) == 1:
        return _find_line3d(ljs, params[0])
    return Line3D(_find_point3d(ljs, params[0]), _find_point3d(ljs, params[1]))


# ------------------------- 立体几何对象创建 -------------------------
def create_solid_object(idx, name, params_str, fs, ljs):
    raw = [p.strip() for p in params_str.split(",")] if params_str else []
    from functions.solids import (
        create_point3d, create_line3d, plane_parallel_through_point,
        plane_perpendicular_to_line_through_point,
        line_parallel_through_point_3d, line_perpendicular_to_plane_through_point,
        plane_through_line_and_point, plane_through_two_lines,
        perpendicular_foot_to_plane, perpendicular_foot_to_line_3d,
        segment3d_from_points,
    )
    if idx == 1:
        return ("点", create_point3d(raw[0], raw[1], raw[2], fs))
    elif idx == 2:
        pts = _find_points3d(ljs, raw[0] + "," + raw[1])
        return ("直线", create_line3d(*pts))
    elif idx == 3:
        pl = _find_plane(ljs, raw[0]); pt = _find_point3d(ljs, raw[1])
        return ("平面", plane_parallel_through_point(pl, pt))
    elif idx == 4:
        line = _find_line3d(ljs, raw[0]); pt = _find_point3d(ljs, raw[1])
        return ("平面", plane_perpendicular_to_line_through_point(line, pt))
    elif idx == 5:
        line = _find_line3d(ljs, raw[0]); pt = _find_point3d(ljs, raw[1])
        return ("直线", line_parallel_through_point_3d(line, pt))
    elif idx == 6:
        pt = _find_point3d(ljs, raw[0]); line = _find_line3d(ljs, raw[1])
        foot = perpendicular_foot_to_line_3d(pt, line)
        return ("直线", create_line3d(pt, foot))
    elif idx == 7:
        pl = _find_plane(ljs, raw[0]); pt = _find_point3d(ljs, raw[1])
        return ("直线", line_perpendicular_to_plane_through_point(pl, pt))
    elif idx == 8:
        line = _find_line3d(ljs, raw[0]); pt = _find_point3d(ljs, raw[1])
        res = plane_through_line_and_point(line, pt)
        if isinstance(res, str):
            raise ValueError(res)
        return ("平面", res)
    elif idx == 9:
        l1 = _find_line3d(ljs, raw[0]); l2 = _find_line3d(ljs, raw[1])
        res = plane_through_two_lines(l1, l2)
        if isinstance(res, str):
            raise ValueError(res)
        return ("平面", res)
    elif idx == 10:
        pt = _find_point3d(ljs, raw[0]); pl = _find_plane(ljs, raw[1])
        return ("点", perpendicular_foot_to_plane(pt, pl))
    elif idx == 11:
        pt = _find_point3d(ljs, raw[0]); line = _find_line3d(ljs, raw[1])
        return ("点", perpendicular_foot_to_line_3d(pt, line))
    elif idx == 12:
        pts = _find_points3d(ljs, raw[0] + "," + raw[1])
        return ("线段", segment3d_from_points(*pts))
    raise ValueError("未知的立体几何创建方法")


# ------------------------- 立体几何计算 -------------------------
def compute_solid(idx, params_str, fs, ljs):
    raw = [p.strip() for p in params_str.split(",")]
    from functions.solids import (
        point3d_distance, point3d_midpoint, point3d_to_plane_distance,
        point3d_to_line_distance, point3d_projection_on_plane,
        point3d_projection_on_line, are_coplanar, line3d_direction,
        line3d_intersection, line3d_angle, line3d_parallel_check,
        line3d_perpendicular_check, line3d_projection_on_plane,
        plane_equation_from_points, plane_normal_vector,
        plane_angle_between, plane_parallel_check,
        plane_perpendicular_check, plane_intersection,
        plane_line_intersection, tetrahedron_volume, line_plane_angle,
    )

    def split_half(seq):
        h = len(seq) // 2
        return seq[:h], seq[h:]

    if idx == 1:
        return point3d_distance(_find_point3d(ljs, raw[0]), _find_point3d(ljs, raw[1]))
    elif idx == 2:
        return point3d_midpoint(_find_point3d(ljs, raw[0]), _find_point3d(ljs, raw[1]))
    elif idx == 3:
        return point3d_to_plane_distance(_find_point3d(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 4:
        return point3d_to_line_distance(_find_point3d(ljs, raw[0]), _line3d_from(ljs, *raw[1:]))
    elif idx == 5:
        return point3d_projection_on_plane(_find_point3d(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 6:
        return point3d_projection_on_line(_find_point3d(ljs, raw[0]), _line3d_from(ljs, *raw[1:]))
    elif idx == 7:
        return are_coplanar([_find_point3d(ljs, p) for p in raw])
    elif idx == 8:
        a, b = split_half(raw); return line3d_direction(_line3d_from(ljs, *a))
    elif idx == 9:
        a, b = split_half(raw); return line3d_intersection(_line3d_from(ljs, *a), _line3d_from(ljs, *b))
    elif idx == 10:
        a, b = split_half(raw); return line3d_angle(_line3d_from(ljs, *a), _line3d_from(ljs, *b))
    elif idx == 11:
        a, b = split_half(raw); return line3d_parallel_check(_line3d_from(ljs, *a), _line3d_from(ljs, *b))
    elif idx == 12:
        a, b = split_half(raw); return line3d_perpendicular_check(_line3d_from(ljs, *a), _line3d_from(ljs, *b))
    elif idx == 13:
        a, b = split_half(raw); return line3d_projection_on_plane(_line3d_from(ljs, *a), _find_plane(ljs, b[0]))
    elif idx == 14:
        return plane_equation_from_points(_find_point3d(ljs, raw[0]), _find_point3d(ljs, raw[1]), _find_point3d(ljs, raw[2]))
    elif idx == 15:
        return plane_normal_vector(_find_plane(ljs, raw[0]))
    elif idx == 16:
        return plane_angle_between(_find_plane(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 17:
        return plane_intersection(_find_plane(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 18:
        return plane_parallel_check(_find_plane(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 19:
        return plane_perpendicular_check(_find_plane(ljs, raw[0]), _find_plane(ljs, raw[1]))
    elif idx == 20:
        return plane_line_intersection(_find_plane(ljs, raw[0]), _line3d_from(ljs, *raw[1:]))
    elif idx == 21:
        return tetrahedron_volume(_find_point3d(ljs, raw[0]), _find_point3d(ljs, raw[1]),
                                  _find_point3d(ljs, raw[2]), _find_point3d(ljs, raw[3]))
    elif idx == 22:
        a, b = split_half(raw); return line_plane_angle(_line3d_from(ljs, *a), _find_plane(ljs, b[0]))
    raise ValueError("未知的操作")
