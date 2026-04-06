import math
from dataclasses import dataclass
from typing import Optional

from logic.dimension_styles import DEFAULT_DIMENSION_STYLES
from logic.geometry import Arc, Circle, Point, Segment


def _point_from(obj):
    return Point(obj.x, obj.y)


def _distance_point_to_segment(px, py, a: Point, b: Point):
    return Segment(a, b).distance_to_point(px, py)


def _normalize_angle(angle):
    two_pi = 2 * math.pi
    return angle % two_pi


def _ccw_delta(start, end):
    return (_normalize_angle(end) - _normalize_angle(start)) % (2 * math.pi)


def _is_between_ccw(test, start, end):
    delta_total = _ccw_delta(start, end)
    delta_test = _ccw_delta(start, test)
    return delta_test <= delta_total + 1e-9


@dataclass
class GeometryReference:
    kind: str
    point: Point
    source_object: object = None
    ref_kind: Optional[str] = None
    ref_index: Optional[int] = None

    @classmethod
    def static(cls, point: Point):
        return cls("static", _point_from(point))

    def clone_point(self):
        return _point_from(self.point)

    def resolve(self):
        if self.source_object is None or self.ref_kind is None:
            return self.clone_point()

        obj = self.source_object

        try:
            if self.ref_kind == "segment_endpoint":
                return _point_from(obj.p1 if self.ref_index == 0 else obj.p2)
            if self.ref_kind == "segment_midpoint":
                return Point((obj.p1.x + obj.p2.x) / 2.0, (obj.p1.y + obj.p2.y) / 2.0)
            if self.ref_kind == "circle_center":
                return _point_from(obj.center)
            if self.ref_kind == "circle_angle":
                angle = math.atan2(self.point.y - obj.center.y, self.point.x - obj.center.x)
                return Point(
                    obj.center.x + obj.radius * math.cos(angle),
                    obj.center.y + obj.radius * math.sin(angle),
                )
            if self.ref_kind == "arc_center":
                return _point_from(obj.center)
            if self.ref_kind == "arc_angle":
                angle = math.atan2(self.point.y - obj.center.y, self.point.x - obj.center.x)
                if not _is_between_ccw(angle, obj.start_angle, obj.end_angle):
                    angle = obj.start_angle + obj.sweep_angle / 2.0
                return Point(
                    obj.center.x + obj.radius * math.cos(angle),
                    obj.center.y + obj.radius * math.sin(angle),
                )
            if self.ref_kind == "arc_endpoint":
                angle = obj.start_angle if self.ref_index == 0 else obj.end_angle
                return Point(
                    obj.center.x + obj.radius * math.cos(angle),
                    obj.center.y + obj.radius * math.sin(angle),
                )
            if self.ref_kind == "arc_midpoint":
                angle = obj.start_angle + obj.sweep_angle / 2.0
                return Point(
                    obj.center.x + obj.radius * math.cos(angle),
                    obj.center.y + obj.radius * math.sin(angle),
                )
            if self.ref_kind == "ellipse_center":
                return _point_from(obj.center)
            if self.ref_kind == "rectangle_corner":
                corners = obj.corners()
                if self.ref_index is not None and 0 <= self.ref_index < len(corners):
                    return _point_from(corners[self.ref_index])
            if self.ref_kind == "rectangle_center":
                return _point_from(obj.center)
            if self.ref_kind == "rectangle_edge_midpoint":
                edges, _ = obj.build_edges()
                if self.ref_index is not None and 0 <= self.ref_index < len(edges):
                    edge = edges[self.ref_index]
                    return Point((edge.p1.x + edge.p2.x) / 2.0, (edge.p1.y + edge.p2.y) / 2.0)
            if self.ref_kind == "polygon_vertex":
                verts = obj.vertices()
                if self.ref_index is not None and 0 <= self.ref_index < len(verts):
                    return _point_from(verts[self.ref_index])
            if self.ref_kind == "polygon_center":
                return _point_from(obj.center)
            if self.ref_kind == "polygon_edge_midpoint":
                edges = obj.edges()
                if self.ref_index is not None and 0 <= self.ref_index < len(edges):
                    edge = edges[self.ref_index]
                    return Point((edge.p1.x + edge.p2.x) / 2.0, (edge.p1.y + edge.p2.y) / 2.0)
            if self.ref_kind == "spline_control":
                pts = obj.control_points
                if self.ref_index is not None and 0 <= self.ref_index < len(pts):
                    return _point_from(pts[self.ref_index])
        except Exception:
            return self.clone_point()

        return self.clone_point()

    def break_associativity(self, new_point: Point):
        self.kind = "static"
        self.point = _point_from(new_point)
        self.source_object = None
        self.ref_kind = None
        self.ref_index = None

    def depends_on(self, obj):
        return self.source_object is obj


class DimensionBase:
    dimension_type = "dimension"

    def __init__(
        self,
        *,
        color="black",
        layer="0",
        dimension_style_name="gost_default",
        text_override="",
    ):
        self.color = color
        self.layer = layer
        self.dimension_style_name = dimension_style_name
        self.text_override = text_override
        self.manual_text_position = None

    def _style(self, state):
        styles = getattr(state, "dimension_styles", DEFAULT_DIMENSION_STYLES)
        return styles.get(self.dimension_style_name) or next(iter(styles.values()))

    def _format_linear(self, value, state):
        style = self._style(state)
        return f"{value:.{style.decimal_places}f}"

    def _format_angular(self, value_rad, state):
        style = self._style(state)
        value_deg = math.degrees(value_rad)
        return f"{value_deg:.{style.decimal_places}f}°"

    def display_text(self, state):
        if self.text_override:
            return self.text_override
        return self.default_text(state)

    def default_text(self, state):
        raise NotImplementedError

    def resolve_geometry(self, state):
        raise NotImplementedError

    def distance_to_point(self, mx, my, state):
        geo = self.resolve_geometry(state)
        if not geo:
            return float("inf")

        distances = []
        for seg in geo.get("segments", []):
            distances.append(seg.distance_to_point(mx, my))
        for arc in geo.get("arcs", []):
            distances.append(arc.distance_to_point(mx, my))

        text_point = geo.get("text_point")
        if text_point is not None:
            distances.append(math.hypot(mx - text_point.x, my - text_point.y))

        return min(distances) if distances else float("inf")

    def depends_on(self, obj):
        return False

    def grip_points(self, state):
        geo = self.resolve_geometry(state)
        return geo.get("grips", {}) if geo else {}

    def move_grip(self, grip_name, new_point: Point):
        raise NotImplementedError


class LinearDimension(DimensionBase):
    dimension_type = "linear"

    def __init__(self, p1_ref, p2_ref, line_ref, mode="aligned", **kwargs):
        super().__init__(**kwargs)
        self.p1_ref = p1_ref
        self.p2_ref = p2_ref
        self.line_ref = line_ref
        self.mode = mode

    def depends_on(self, obj):
        return any(ref.depends_on(obj) for ref in [self.p1_ref, self.p2_ref, self.line_ref])

    def _resolved_points(self):
        return self.p1_ref.resolve(), self.p2_ref.resolve(), self.line_ref.resolve()

    def measured_value(self, state):
        p1, p2, _ = self._resolved_points()
        if self.mode == "horizontal":
            return abs(p2.x - p1.x)
        if self.mode == "vertical":
            return abs(p2.y - p1.y)
        return math.hypot(p2.x - p1.x, p2.y - p1.y)

    def default_text(self, state):
        return self._format_linear(self.measured_value(state), state)

    def resolve_geometry(self, state):
        p1, p2, line_pt = self._resolved_points()
        style = self._style(state)

        if self.mode == "horizontal":
            dim_dir = Point(1.0, 0.0)
            normal = Point(0.0, 1.0)
            dim_y = line_pt.y
            dim_p1 = Point(p1.x, dim_y)
            dim_p2 = Point(p2.x, dim_y)
            base1 = Point(p1.x, p1.y)
            base2 = Point(p2.x, p2.y)
            text_point = Point((dim_p1.x + dim_p2.x) / 2.0, dim_y + style.text_gap_mm)
            text_angle = 0.0
        elif self.mode == "vertical":
            dim_dir = Point(0.0, 1.0)
            normal = Point(1.0, 0.0)
            dim_x = line_pt.x
            dim_p1 = Point(dim_x, p1.y)
            dim_p2 = Point(dim_x, p2.y)
            base1 = Point(p1.x, p1.y)
            base2 = Point(p2.x, p2.y)
            text_point = Point(dim_x + style.text_gap_mm, (dim_p1.y + dim_p2.y) / 2.0)
            text_angle = math.pi / 2
        else:
            vx = p2.x - p1.x
            vy = p2.y - p1.y
            length = math.hypot(vx, vy)
            if length < 1e-9:
                return None
            ux = vx / length
            uy = vy / length
            nx = -uy
            ny = ux
            offset = (line_pt.x - p1.x) * nx + (line_pt.y - p1.y) * ny
            dim_p1 = Point(p1.x + nx * offset, p1.y + ny * offset)
            dim_p2 = Point(p2.x + nx * offset, p2.y + ny * offset)
            base1 = Point(p1.x, p1.y)
            base2 = Point(p2.x, p2.y)
            dim_dir = Point(ux, uy)
            normal = Point(nx, ny)
            text_point = Point(
                (dim_p1.x + dim_p2.x) / 2.0 + nx * style.text_gap_mm,
                (dim_p1.y + dim_p2.y) / 2.0 + ny * style.text_gap_mm,
            )
            text_angle = math.atan2(uy, ux)

        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        ext1_start = Point(base1.x + normal.x * style.extension_offset_mm, base1.y + normal.y * style.extension_offset_mm)
        ext2_start = Point(base2.x + normal.x * style.extension_offset_mm, base2.y + normal.y * style.extension_offset_mm)
        ext1_end = Point(dim_p1.x + normal.x * style.extension_overrun_mm, dim_p1.y + normal.y * style.extension_overrun_mm)
        ext2_end = Point(dim_p2.x + normal.x * style.extension_overrun_mm, dim_p2.y + normal.y * style.extension_overrun_mm)

        dim_start = Point(dim_p1.x - dim_dir.x * style.dim_line_extension_mm, dim_p1.y - dim_dir.y * style.dim_line_extension_mm)
        dim_end = Point(dim_p2.x + dim_dir.x * style.dim_line_extension_mm, dim_p2.y + dim_dir.y * style.dim_line_extension_mm)

        return {
            "segments": [
                Segment(ext1_start, ext1_end, style_name=style.line_style_name, color=self.color),
                Segment(ext2_start, ext2_end, style_name=style.line_style_name, color=self.color),
                Segment(dim_start, dim_end, style_name=style.line_style_name, color=self.color),
            ],
            "arcs": [],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": text_angle,
            "arrow_points": [
                {"point": dim_p1, "direction": Point(dim_dir.x, dim_dir.y)},
                {"point": dim_p2, "direction": Point(-dim_dir.x, -dim_dir.y)},
            ],
            "grips": {
                "p1": base1,
                "p2": base2,
                "line": line_pt,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point):
        if grip_name == "p1":
            self.p1_ref.break_associativity(new_point)
        elif grip_name == "p2":
            self.p2_ref.break_associativity(new_point)
        elif grip_name == "line":
            self.line_ref.break_associativity(new_point)
        elif grip_name == "text":
            self.manual_text_position = _point_from(new_point)


class RadialDimension(DimensionBase):
    dimension_type = "radius"

    def __init__(self, center_ref, edge_ref, leader_ref, prefix="R", **kwargs):
        super().__init__(**kwargs)
        self.center_ref = center_ref
        self.edge_ref = edge_ref
        self.leader_ref = leader_ref
        self.prefix = prefix
        self.dimension_type = "diameter" if prefix == "⌀" else "radius"

    def depends_on(self, obj):
        return any(ref.depends_on(obj) for ref in [self.center_ref, self.edge_ref, self.leader_ref])

    def measured_value(self, state):
        center = self.center_ref.resolve()
        edge = self.edge_ref.resolve()
        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if self.prefix == "⌀":
            return radius * 2.0
        return radius

    def default_text(self, state):
        return f"{self.prefix}{self._format_linear(self.measured_value(state), state)}"

    def resolve_geometry(self, state):
        center = self.center_ref.resolve()
        edge = self.edge_ref.resolve()
        leader = self.leader_ref.resolve()
        style = self._style(state)

        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if radius < 1e-9:
            return None

        dir_x = (edge.x - center.x) / radius
        dir_y = (edge.y - center.y) / radius

        if self.prefix == "⌀":
            opp = Point(center.x - dir_x * radius, center.y - dir_y * radius)
            dim_segments = [
                Segment(opp, edge, style_name=style.line_style_name, color=self.color),
            ]
            arrow_points = [
                {"point": opp, "direction": Point(dir_x, dir_y)},
                {"point": edge, "direction": Point(-dir_x, -dir_y)},
            ]
        else:
            dim_segments = [
                Segment(center, edge, style_name=style.line_style_name, color=self.color),
            ]
            arrow_points = [
                {"point": edge, "direction": Point(-dir_x, -dir_y)},
            ]

        if math.hypot(leader.x - edge.x, leader.y - edge.y) > style.text_gap_mm:
            dim_segments.append(Segment(edge, leader, style_name=style.line_style_name, color=self.color))
            text_point = Point(
                leader.x + dir_x * style.text_gap_mm,
                leader.y + dir_y * style.text_gap_mm,
            )
        else:
            text_point = Point(
                edge.x + dir_x * style.text_gap_mm,
                edge.y + dir_y * style.text_gap_mm,
            )

        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        return {
            "segments": dim_segments,
            "arcs": [],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": 0.0,
            "arrow_points": arrow_points,
            "grips": {
                "edge": edge,
                "leader": leader,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point):
        if grip_name == "edge":
            self.edge_ref.break_associativity(new_point)
        elif grip_name == "leader":
            self.leader_ref.break_associativity(new_point)
        elif grip_name == "text":
            self.manual_text_position = _point_from(new_point)


class AngularDimension(DimensionBase):
    dimension_type = "angular"

    def __init__(self, p1_ref, vertex_ref, p2_ref, arc_ref, **kwargs):
        super().__init__(**kwargs)
        self.p1_ref = p1_ref
        self.vertex_ref = vertex_ref
        self.p2_ref = p2_ref
        self.arc_ref = arc_ref

    def depends_on(self, obj):
        return any(ref.depends_on(obj) for ref in [self.p1_ref, self.vertex_ref, self.p2_ref, self.arc_ref])

    def _resolved_points(self):
        return self.p1_ref.resolve(), self.vertex_ref.resolve(), self.p2_ref.resolve(), self.arc_ref.resolve()

    def _angles(self):
        p1, vertex, p2, arc_point = self._resolved_points()
        a1 = math.atan2(p1.y - vertex.y, p1.x - vertex.x)
        a2 = math.atan2(p2.y - vertex.y, p2.x - vertex.x)
        at = math.atan2(arc_point.y - vertex.y, arc_point.x - vertex.x)
        if _is_between_ccw(at, a1, a2):
            start, end = a1, a2
        else:
            start, end = a2, a1
        return p1, vertex, p2, arc_point, start, end

    def measured_value(self, state):
        _, _, _, _, start, end = self._angles()
        return _ccw_delta(start, end)

    def default_text(self, state):
        return self._format_angular(self.measured_value(state), state)

    def resolve_geometry(self, state):
        p1, vertex, p2, arc_point, start, end = self._angles()
        style = self._style(state)
        radius = math.hypot(arc_point.x - vertex.x, arc_point.y - vertex.y)
        if radius < 1e-9:
            return None

        dim_arc = Arc.from_center_angles(
            _point_from(vertex),
            radius,
            start,
            end,
            style_name=style.line_style_name,
            color=self.color,
        )
        start_point = Point(vertex.x + radius * math.cos(start), vertex.y + radius * math.sin(start))
        end_point = Point(vertex.x + radius * math.cos(end), vertex.y + radius * math.sin(end))

        ex1_end = Point(
            vertex.x + (radius + style.extension_overrun_mm) * math.cos(start),
            vertex.y + (radius + style.extension_overrun_mm) * math.sin(start),
        )
        ex2_end = Point(
            vertex.x + (radius + style.extension_overrun_mm) * math.cos(end),
            vertex.y + (radius + style.extension_overrun_mm) * math.sin(end),
        )

        bisector = start + _ccw_delta(start, end) / 2.0
        text_point = Point(
            vertex.x + (radius + style.text_gap_mm) * math.cos(bisector),
            vertex.y + (radius + style.text_gap_mm) * math.sin(bisector),
        )
        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        return {
            "segments": [
                Segment(vertex, ex1_end, style_name=style.line_style_name, color=self.color),
                Segment(vertex, ex2_end, style_name=style.line_style_name, color=self.color),
            ],
            "arcs": [dim_arc],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": 0.0,
            "arrow_points": [
                {"point": start_point, "direction": Point(math.sin(start), -math.cos(start))},
                {"point": end_point, "direction": Point(-math.sin(end), math.cos(end))},
            ],
            "grips": {
                "p1": p1,
                "vertex": vertex,
                "p2": p2,
                "arc": arc_point,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point):
        if grip_name == "p1":
            self.p1_ref.break_associativity(new_point)
        elif grip_name == "vertex":
            self.vertex_ref.break_associativity(new_point)
        elif grip_name == "p2":
            self.p2_ref.break_associativity(new_point)
        elif grip_name == "arc":
            self.arc_ref.break_associativity(new_point)
        elif grip_name == "text":
            self.manual_text_position = _point_from(new_point)


def make_reference_from_snap(snap_point, fallback_point: Point):
    if snap_point and getattr(snap_point, "source_object", None) is not None and getattr(snap_point, "ref_kind", None):
        return GeometryReference(
            "associative",
            _point_from(fallback_point),
            source_object=snap_point.source_object,
            ref_kind=snap_point.ref_kind,
            ref_index=getattr(snap_point, "ref_index", None),
        )
    return GeometryReference.static(fallback_point)


def make_radial_dimension_from_object(obj, leader_point: Point, prefix="R", **kwargs):
    if isinstance(obj, Circle):
        center_ref = GeometryReference("associative", _point_from(obj.center), source_object=obj, ref_kind="circle_center")
        dx = leader_point.x - obj.center.x
        dy = leader_point.y - obj.center.y
        dist = math.hypot(dx, dy) or 1.0
        edge_point = Point(obj.center.x + obj.radius * dx / dist, obj.center.y + obj.radius * dy / dist)
        edge_ref = GeometryReference("associative", _point_from(edge_point), source_object=obj, ref_kind="circle_angle")
        leader_ref = GeometryReference.static(_point_from(leader_point))
        return RadialDimension(center_ref, edge_ref, leader_ref, prefix=prefix, **kwargs)

    if isinstance(obj, Arc):
        center_ref = GeometryReference("associative", _point_from(obj.center), source_object=obj, ref_kind="arc_center")
        dx = leader_point.x - obj.center.x
        dy = leader_point.y - obj.center.y
        angle = math.atan2(dy, dx)
        if not _is_between_ccw(angle, obj.start_angle, obj.end_angle):
            angle = obj.start_angle + obj.sweep_angle / 2.0
        edge_point = Point(obj.center.x + obj.radius * math.cos(angle), obj.center.y + obj.radius * math.sin(angle))
        edge_ref = GeometryReference("associative", _point_from(edge_point), source_object=obj, ref_kind="arc_angle")
        leader_ref = GeometryReference.static(_point_from(leader_point))
        return RadialDimension(center_ref, edge_ref, leader_ref, prefix=prefix, **kwargs)

    return None
