import math
from dataclasses import dataclass
from typing import Optional

from logic.dimension_styles import DEFAULT_DIMENSION_STYLES
from logic.geometry import Arc, Circle, Point, Segment


def _point_from(obj):
    return Point(obj.x, obj.y)


def _distance_point_to_segment(px, py, a: Point, b: Point):
    return Segment(a, b).distance_to_point(px, py)


def _project_point_to_segment(point: Point, a: Point, b: Point):
    dx = b.x - a.x
    dy = b.y - a.y
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return Point(a.x, a.y), 0.0
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / len_sq
    t = max(0.0, min(1.0, t))
    return Point(a.x + dx * t, a.y + dy * t), t


def _normalize_angle(angle):
    two_pi = 2 * math.pi
    return angle % two_pi


def _ccw_delta(start, end):
    return (_normalize_angle(end) - _normalize_angle(start)) % (2 * math.pi)


def _is_between_ccw(test, start, end):
    delta_total = _ccw_delta(start, end)
    delta_test = _ccw_delta(start, test)
    return delta_test <= delta_total + 1e-9


def _normalized_text_angle(angle_rad):
    while angle_rad > math.pi / 2:
        angle_rad -= math.pi
    while angle_rad < -math.pi / 2:
        angle_rad += math.pi
    return angle_rad


def _angle_distance(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def _clamp_angle_to_arc(angle, arc: Arc):
    if _is_between_ccw(angle, arc.start_angle, arc.end_angle):
        return angle

    start_dist = _angle_distance(angle, arc.start_angle)
    end_dist = _angle_distance(angle, arc.end_angle)
    return arc.start_angle if start_dist <= end_dist else arc.end_angle


def _project_point_to_radial_object(obj, point: Point):
    if isinstance(obj, Circle):
        angle = math.atan2(point.y - obj.center.y, point.x - obj.center.x)
        return Point(
            obj.center.x + obj.radius * math.cos(angle),
            obj.center.y + obj.radius * math.sin(angle),
        )

    if isinstance(obj, Arc):
        angle = math.atan2(point.y - obj.center.y, point.x - obj.center.x)
        angle = _clamp_angle_to_arc(angle, obj)
        return Point(
            obj.center.x + obj.radius * math.cos(angle),
            obj.center.y + obj.radius * math.sin(angle),
        )

    return _point_from(point)


@dataclass
class GeometryReference:
    kind: str
    point: Point
    source_object: object = None
    ref_kind: Optional[str] = None
    ref_index: Optional[float] = None

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
            if self.ref_kind == "segment_param":
                t = max(0.0, min(1.0, float(self.ref_index if self.ref_index is not None else 0.0)))
                return Point(
                    obj.p1.x + (obj.p2.x - obj.p1.x) * t,
                    obj.p1.y + (obj.p2.y - obj.p1.y) * t,
                )
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
    ARROW_TYPES = {"triangle", "circle", "square", "tick"}
    TEXT_POSITIONS = {"above", "center", "below"}
    APPEARANCE_ATTRS = [
        "extension_line_color",
        "extension_line_style_name",
        "extension_overrun_mm",
        "dim_line_color",
        "dim_line_style_name",
        "dim_line_extension_mm",
        "arrow_type",
        "arrow_size_mm",
        "arrow_filled",
        "text_color",
        "text_font_family",
        "text_height_mm",
        "text_position_mode",
    ]

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
        self.extension_line_color = None
        self.extension_line_style_name = None
        self.extension_overrun_mm = None
        self.dim_line_color = None
        self.dim_line_style_name = None
        self.dim_line_extension_mm = None
        self.arrow_type = None
        self.arrow_size_mm = None
        self.arrow_filled = None
        self.text_color = None
        self.text_font_family = None
        self.text_height_mm = None
        self.text_position_mode = None
        self.custom_style_snapshot = {}

    def _style(self, state):
        styles = getattr(state, "dimension_styles", DEFAULT_DIMENSION_STYLES)
        return styles.get(self.dimension_style_name) or next(iter(styles.values()))

    def copy_display_overrides_from(self, other):
        attrs = [
            "text_override",
        ] + list(self.APPEARANCE_ATTRS)
        for attr in attrs:
            setattr(self, attr, getattr(other, attr, None))
        self.custom_style_snapshot = dict(getattr(other, "custom_style_snapshot", {}) or {})

        manual_text = getattr(other, "manual_text_position", None)
        self.manual_text_position = None if manual_text is None else Point(manual_text.x, manual_text.y)

    def _format_linear(self, value, state):
        style = self._style(state)
        return f"{value:.{style.decimal_places}f}"

    def _format_angular(self, value_rad, state):
        style = self._style(state)
        value_deg = math.degrees(value_rad)
        return f"{value_deg:.{style.decimal_places}f}°"

    def _override_display_text(self, state):
        return self.text_override

    def _effective_extension_line_color(self, state):
        return self.extension_line_color or self.color

    def _effective_extension_line_style_name(self, state):
        return self.extension_line_style_name or self._style(state).line_style_name

    def _effective_extension_overrun_mm(self, state):
        style = self._style(state)
        return style.extension_overrun_mm if self.extension_overrun_mm is None else max(0.0, float(self.extension_overrun_mm))

    def _effective_dim_line_color(self, state):
        return self.dim_line_color or self.color

    def _effective_dim_line_style_name(self, state):
        return self.dim_line_style_name or self._style(state).line_style_name

    def _effective_dim_line_extension_mm(self, state):
        if self.dim_line_extension_mm is None:
            return max(0.0, float(self._default_dim_line_extension_mm(state)))
        return max(0.0, float(self.dim_line_extension_mm))

    def _default_dim_line_extension_mm(self, state):
        return self._style(state).dim_line_extension_mm

    def _effective_arrow_type(self, state):
        arrow_type = (self.arrow_type or "triangle").lower()
        return arrow_type if arrow_type in self.ARROW_TYPES else "triangle"

    def _effective_arrow_size_mm(self, state):
        style = self._style(state)
        return style.arrow_size_mm if self.arrow_size_mm is None else max(0.1, float(self.arrow_size_mm))

    def _effective_arrow_filled(self, state):
        style = self._style(state)
        return style.arrow_filled if self.arrow_filled is None else bool(self.arrow_filled)

    def _effective_text_color(self, state):
        return self.text_color or self._style(state).text_color

    def _effective_text_font_family(self, state):
        return self.text_font_family or "ГОСТ тип А наклонный"

    def _effective_text_height_mm(self, state):
        style = self._style(state)
        return style.text_height_mm if self.text_height_mm is None else max(0.1, float(self.text_height_mm))

    def _effective_text_position_mode(self, state):
        position = (self.text_position_mode or "above").lower()
        return position if position in self.TEXT_POSITIONS else "above"

    def _text_offset_factor(self, state):
        position = self._effective_text_position_mode(state)
        if position == "center":
            return 0.0
        if position == "below":
            return -1.0
        return 1.0

    def _capture_appearance_state(self):
        return {attr: getattr(self, attr, None) for attr in self.APPEARANCE_ATTRS}

    def _restore_appearance_state(self, snapshot):
        snapshot = snapshot or {}
        for attr in self.APPEARANCE_ATTRS:
            setattr(self, attr, snapshot.get(attr))

    def activate_dimension_style(self, style_name):
        if self.dimension_style_name == "user_custom":
            self.custom_style_snapshot = self._capture_appearance_state()

        if style_name == "user_custom":
            self._restore_appearance_state(self.custom_style_snapshot)
        else:
            for attr in self.APPEARANCE_ATTRS:
                setattr(self, attr, None)

        self.dimension_style_name = style_name

    def display_text(self, state):
        if self.text_override:
            return self._override_display_text(state)
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
        if "extension_segments" in geo or "dimension_segments" in geo:
            segment_groups = [
                geo.get("extension_segments", []),
                geo.get("dimension_segments", []),
            ]
        else:
            segment_groups = [geo.get("segments", [])]
        for seg_group in segment_groups:
            for seg in seg_group:
                distances.append(seg.distance_to_point(mx, my))

        if "dimension_arcs" in geo:
            arc_groups = [geo.get("dimension_arcs", [])]
        else:
            arc_groups = [geo.get("arcs", [])]
        for arc_group in arc_groups:
            for arc in arc_group:
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
        text_gap = style.text_gap_mm * self._text_offset_factor(state)
        text_height = self._effective_text_height_mm(state)
        extension_overrun = self._effective_extension_overrun_mm(state)
        dim_line_extension = self._effective_dim_line_extension_mm(state)
        ext_style_name = self._effective_extension_line_style_name(state)
        dim_style_name = self._effective_dim_line_style_name(state)

        if self.mode == "horizontal":
            dim_dir = Point(1.0, 0.0)
            dim_y = line_pt.y
            dim_p1 = Point(p1.x, dim_y)
            dim_p2 = Point(p2.x, dim_y)
            base1 = Point(p1.x, p1.y)
            base2 = Point(p2.x, p2.y)
            sign = 1.0 if dim_y >= (p1.y + p2.y) / 2.0 else -1.0
            normal = Point(0.0, sign)
            text_point = Point((dim_p1.x + dim_p2.x) / 2.0, dim_y + sign * text_gap)
            text_angle = 0.0
        elif self.mode == "vertical":
            dim_dir = Point(0.0, 1.0)
            dim_x = line_pt.x
            dim_p1 = Point(dim_x, p1.y)
            dim_p2 = Point(dim_x, p2.y)
            base1 = Point(p1.x, p1.y)
            base2 = Point(p2.x, p2.y)
            sign = 1.0 if dim_x >= (p1.x + p2.x) / 2.0 else -1.0
            normal = Point(sign, 0.0)
            text_point = Point(dim_x + sign * text_gap, (dim_p1.y + dim_p2.y) / 2.0)
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
            sign = 1.0 if offset >= 0.0 else -1.0
            normal = Point(nx * sign, ny * sign)
            text_point = Point(
                (dim_p1.x + dim_p2.x) / 2.0 + normal.x * text_gap,
                (dim_p1.y + dim_p2.y) / 2.0 + normal.y * text_gap,
            )
            text_angle = math.atan2(uy, ux)

        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        ext1_start = Point(base1.x, base1.y)
        ext2_start = Point(base2.x, base2.y)
        ext1_end = Point(dim_p1.x + normal.x * extension_overrun, dim_p1.y + normal.y * extension_overrun)
        ext2_end = Point(dim_p2.x + normal.x * extension_overrun, dim_p2.y + normal.y * extension_overrun)

        dim_start = Point(dim_p1.x - dim_dir.x * dim_line_extension, dim_p1.y - dim_dir.y * dim_line_extension)
        dim_end = Point(dim_p2.x + dim_dir.x * dim_line_extension, dim_p2.y + dim_dir.y * dim_line_extension)

        extension_segments = [
            Segment(ext1_start, ext1_end, style_name=ext_style_name, color=self.color),
            Segment(ext2_start, ext2_end, style_name=ext_style_name, color=self.color),
        ]
        dimension_segments = [
            Segment(dim_start, dim_end, style_name=dim_style_name, color=self.color),
        ]

        return {
            "segments": extension_segments + dimension_segments,
            "extension_segments": extension_segments,
            "dimension_segments": dimension_segments,
            "arcs": [],
            "dimension_arcs": [],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": text_angle,
            "text_height_mm": text_height,
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
            if isinstance(self.p1_ref.source_object, Segment):
                projected, t = _project_point_to_segment(new_point, self.p1_ref.source_object.p1, self.p1_ref.source_object.p2)
                self.p1_ref.kind = "associative"
                self.p1_ref.point = projected
                self.p1_ref.ref_kind = "segment_param"
                self.p1_ref.ref_index = t
            else:
                self.p1_ref.break_associativity(new_point)
        elif grip_name == "p2":
            if isinstance(self.p2_ref.source_object, Segment):
                projected, t = _project_point_to_segment(new_point, self.p2_ref.source_object.p1, self.p2_ref.source_object.p2)
                self.p2_ref.kind = "associative"
                self.p2_ref.point = projected
                self.p2_ref.ref_kind = "segment_param"
                self.p2_ref.ref_index = t
            else:
                self.p2_ref.break_associativity(new_point)
        elif grip_name == "line":
            old_line = self.line_ref.resolve()
            self.line_ref.break_associativity(new_point)
            if self.manual_text_position is not None:
                self.manual_text_position = Point(
                    self.manual_text_position.x + (new_point.x - old_line.x),
                    self.manual_text_position.y + (new_point.y - old_line.y),
                )
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
        return any(ref.depends_on(obj) for ref in [self.center_ref, self.edge_ref])

    def measured_value(self, state):
        center = self.center_ref.resolve()
        edge = self.edge_ref.resolve()
        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if self.prefix == "⌀":
            return radius * 2.0
        return radius

    def default_text(self, state):
        return f"{self.prefix}{self._format_linear(self.measured_value(state), state)}"

    def _override_display_text(self, state):
        raw = self.text_override.strip()
        if self.prefix == "R":
            raw = raw.removeprefix("R").strip()
            return f"R{raw}"
        raw = raw.removeprefix("⌀").strip()
        return f"⌀{raw}"

    def _circle_diameter_layout_mode(self):
        obj = self.center_ref.source_object
        if self.prefix != "⌀" or not isinstance(obj, Circle):
            return "default"

        diameter = obj.radius * 2.0
        if diameter < 12.0:
            return "outside"
        return "inside"

    def _default_dim_line_extension_mm(self, state):
        mode = self._circle_diameter_layout_mode()
        if mode == "outside":
            return 7.0
        return 0.0

    def resolve_geometry(self, state):
        center = self.center_ref.resolve()
        edge = self.edge_ref.resolve()
        style = self._style(state)
        text_gap = style.text_gap_mm * self._text_offset_factor(state)
        dim_style_name = self._effective_dim_line_style_name(state)
        text_height = self._effective_text_height_mm(state)
        dim_line_extension = self._effective_dim_line_extension_mm(state)

        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if radius < 1e-9:
            return None

        dir_x = (edge.x - center.x) / radius
        dir_y = (edge.y - center.y) / radius
        normal = Point(-dir_y, dir_x)
        layout_mode = self._circle_diameter_layout_mode()

        if self.prefix == "⌀":
            inner_start = Point(center.x - dir_x * radius, center.y - dir_y * radius)
            inner_end = edge
            text_anchor_start = inner_start
            text_anchor_end = inner_end
            if layout_mode == "outside":
                dim_start = Point(center.x - dir_x * (radius + dim_line_extension), center.y - dir_y * (radius + dim_line_extension))
                dim_end = Point(center.x + dir_x * (radius + dim_line_extension), center.y + dir_y * (radius + dim_line_extension))
                arrow_points = [
                    {"point": inner_start, "direction": Point(-dir_x, -dir_y)},
                    {"point": inner_end, "direction": Point(dir_x, dir_y)},
                ]
            else:
                dim_start = inner_start
                dim_end = inner_end
                arrow_points = [
                    {"point": inner_start, "direction": Point(dir_x, dir_y)},
                    {"point": inner_end, "direction": Point(-dir_x, -dir_y)},
                ]
        else:
            text_anchor_start = center
            text_anchor_end = edge
            dim_start = center
            dim_end = Point(center.x + dir_x * (radius + dim_line_extension), center.y + dir_y * (radius + dim_line_extension))
            arrow_points = [
                {"point": edge, "direction": Point(-dir_x, -dir_y)},
            ]

        text_point = Point(
            (text_anchor_start.x + text_anchor_end.x) / 2.0 + normal.x * text_gap,
            (text_anchor_start.y + text_anchor_end.y) / 2.0 + normal.y * text_gap,
        )

        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        dimension_segments = [
            Segment(dim_start, dim_end, style_name=dim_style_name, color=self.color),
        ]

        return {
            "segments": dimension_segments,
            "extension_segments": [],
            "dimension_segments": dimension_segments,
            "arcs": [],
            "dimension_arcs": [],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": _normalized_text_angle(math.atan2(dir_y, dir_x)),
            "text_height_mm": text_height,
            "arrow_points": arrow_points,
            "grips": {
                "line": edge,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point):
        if grip_name == "line":
            old_edge = self.edge_ref.resolve()
            edge_object = self.edge_ref.source_object
            if isinstance(edge_object, (Circle, Arc)):
                projected = _project_point_to_radial_object(edge_object, new_point)
                self.edge_ref.kind = "associative"
                self.edge_ref.point = projected
                self.edge_ref.ref_kind = "circle_angle" if isinstance(edge_object, Circle) else "arc_angle"
                self.edge_ref.source_object = edge_object
                self.leader_ref.break_associativity(projected)
                new_point = projected
            else:
                self.edge_ref.break_associativity(new_point)
                self.leader_ref.break_associativity(new_point)

            if self.manual_text_position is not None:
                self.manual_text_position = Point(
                    self.manual_text_position.x + (new_point.x - old_edge.x),
                    self.manual_text_position.y + (new_point.y - old_edge.y),
                )
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

    def _override_display_text(self, state):
        raw = self.text_override.strip()
        raw = raw.removesuffix("°").strip()
        return f"{raw}°"

    def _default_dim_line_extension_mm(self, state):
        return 7.0

    def resolve_geometry(self, state):
        p1, vertex, p2, arc_point, start, end = self._angles()
        style = self._style(state)
        extension_overrun = self._effective_extension_overrun_mm(state)
        ext_style_name = self._effective_extension_line_style_name(state)
        dim_style_name = self._effective_dim_line_style_name(state)
        text_height = self._effective_text_height_mm(state)
        radial_offset = (style.text_gap_mm + text_height * 0.5) * self._text_offset_factor(state)
        dim_line_extension = self._effective_dim_line_extension_mm(state)
        radius = math.hypot(arc_point.x - vertex.x, arc_point.y - vertex.y)
        if radius < 1e-9:
            return None

        arc_extension = max(0.0, dim_line_extension)
        arc_extension_angle = arc_extension / radius if radius > 1e-9 else 0.0
        dim_start = start - arc_extension_angle
        dim_end = end + arc_extension_angle

        dim_arc = Arc.from_center_angles(
            _point_from(vertex),
            radius,
            dim_start,
            dim_end,
            style_name=dim_style_name,
            color=self.color,
        )
        start_point = Point(vertex.x + radius * math.cos(start), vertex.y + radius * math.sin(start))
        end_point = Point(vertex.x + radius * math.cos(end), vertex.y + radius * math.sin(end))

        ex1_end = Point(
            vertex.x + (radius + extension_overrun) * math.cos(start),
            vertex.y + (radius + extension_overrun) * math.sin(start),
        )
        ex2_end = Point(
            vertex.x + (radius + extension_overrun) * math.cos(end),
            vertex.y + (radius + extension_overrun) * math.sin(end),
        )

        bisector = start + _ccw_delta(start, end) / 2.0
        text_point = Point(
            vertex.x + (radius + radial_offset) * math.cos(bisector),
            vertex.y + (radius + radial_offset) * math.sin(bisector),
        )
        if self.manual_text_position is not None:
            text_point = _point_from(self.manual_text_position)

        tangent_angle = _normalized_text_angle(bisector + math.pi / 2.0)

        extension_segments = [
            Segment(vertex, ex1_end, style_name=ext_style_name, color=self.color),
            Segment(vertex, ex2_end, style_name=ext_style_name, color=self.color),
        ]

        return {
            "segments": extension_segments,
            "extension_segments": extension_segments,
            "dimension_segments": [],
            "arcs": [dim_arc],
            "dimension_arcs": [dim_arc],
            "text_point": text_point,
            "text": self.display_text(state),
            "text_angle": tangent_angle,
            "text_height_mm": text_height,
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
            old_arc = self.arc_ref.resolve()
            self.arc_ref.break_associativity(new_point)
            if self.manual_text_position is not None:
                self.manual_text_position = Point(
                    self.manual_text_position.x + (new_point.x - old_arc.x),
                    self.manual_text_position.y + (new_point.y - old_arc.y),
                )
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
