import math
from dataclasses import dataclass
from typing import Optional

from logic.dimension_styles import DEFAULT_DIMENSION_STYLES
from logic.geometry import Arc, Circle, Ellipse, Point, Rectangle, Segment


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


def _project_point_to_line(point: Point, a: Point, b: Point):
    dx = b.x - a.x
    dy = b.y - a.y
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return Point(a.x, a.y)
    t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / len_sq
    return Point(a.x + dx * t, a.y + dy * t)


def _translate_text_along_line(target_point: Point, current_text_point: Point, line_a: Point, line_b: Point):
    projected_target = _project_point_to_line(target_point, line_a, line_b)
    projected_current = _project_point_to_line(current_text_point, line_a, line_b)
    return Point(
        projected_target.x + (current_text_point.x - projected_current.x),
        projected_target.y + (current_text_point.y - projected_current.y),
    )


def _reapply_text_offset_on_line(manual_point: Point, auto_text_point: Point, line_a: Point, line_b: Point):
    projected_manual = _project_point_to_line(manual_point, line_a, line_b)
    projected_auto = _project_point_to_line(auto_text_point, line_a, line_b)
    return Point(
        projected_manual.x + (auto_text_point.x - projected_auto.x),
        projected_manual.y + (auto_text_point.y - projected_auto.y),
    )


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


def _signed_angle_delta(start, end):
    return ((end - start + math.pi) % (2 * math.pi)) - math.pi


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
            if self.ref_kind == "ellipse_axis":
                points = obj.axis_snap_points()
                idx = int(self.ref_index if self.ref_index is not None else 0)
                if 0 <= idx < len(points):
                    return _point_from(points[idx])
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
            if self.ref_kind == "rectangle_fillet_center":
                arcs = obj.fillet_arcs()
                idx = int(self.ref_index if self.ref_index is not None else 0)
                if 0 <= idx < len(arcs):
                    return _point_from(arcs[idx].center)
            if self.ref_kind == "rectangle_fillet_angle":
                arcs = obj.fillet_arcs()
                idx = int(self.ref_index if self.ref_index is not None else 0)
                if 0 <= idx < len(arcs):
                    arc = arcs[idx]
                    angle = math.atan2(self.point.y - arc.center.y, self.point.x - arc.center.x)
                    angle = _clamp_angle_to_arc(angle, arc)
                    return Point(
                        arc.center.x + arc.radius * math.cos(angle),
                        arc.center.y + arc.radius * math.sin(angle),
                    )
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

    def _requested_dim_line_extension_mm(self, state):
        if self.dim_line_extension_mm is None:
            return max(0.0, float(self._default_dim_line_extension_mm(state)))
        return max(0.0, float(self.dim_line_extension_mm))

    def _minimum_dim_line_extension_mm(self, state):
        return 0.0

    def _effective_dim_line_extension_mm(self, state):
        return max(self._requested_dim_line_extension_mm(state), self._minimum_dim_line_extension_mm(state))

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

    def _approx_text_width_mm(self, state, text=None, text_height=None):
        text = self.display_text(state) if text is None else str(text)
        text_height = self._effective_text_height_mm(state) if text_height is None else max(0.1, float(text_height))
        width_units = 0.0
        for ch in text:
            if ch.isspace():
                width_units += 0.35
            elif ch in ".,:;!|ilI1'`":
                width_units += 0.3
            elif ch in "°":
                width_units += 0.45
            elif ch in "MWЖШЩЮ@#":
                width_units += 0.85
            else:
                width_units += 0.6
        return max(text_height, width_units * text_height)

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

    def move_grip(self, grip_name, new_point: Point, state=None):
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

    def _outside_arrow_mode(self, state):
        return self.measured_value(state) < 12.0

    def _line_basis(self, state):
        p1, p2, line_pt = self._resolved_points()
        style = self._style(state)
        text_gap = style.text_gap_mm * self._text_offset_factor(state)
        text_height = self._effective_text_height_mm(state)

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
            text_angle = _normalized_text_angle(math.atan2(uy, ux))

        if self.manual_text_position is not None:
            text_point = _reapply_text_offset_on_line(self.manual_text_position, text_point, dim_p1, dim_p2)

        return {
            "p1": p1,
            "p2": p2,
            "line_pt": line_pt,
            "dim_p1": dim_p1,
            "dim_p2": dim_p2,
            "base1": base1,
            "base2": base2,
            "dim_dir": dim_dir,
            "normal": normal,
            "text_point": text_point,
            "text_angle": text_angle,
            "text_height": text_height,
        }

    def _text_extension_requirements(self, state):
        basis = self._line_basis(state)
        if basis is None:
            return 0.0, 0.0, None

        dim_p1 = basis["dim_p1"]
        dim_p2 = basis["dim_p2"]
        dim_dir = basis["dim_dir"]
        text_point = basis["text_point"]
        length = math.hypot(dim_p2.x - dim_p1.x, dim_p2.y - dim_p1.y)
        if length < 1e-9:
            return 0.0, 0.0, basis

        center_coord = (text_point.x - dim_p1.x) * dim_dir.x + (text_point.y - dim_p1.y) * dim_dir.y
        half_span = self._approx_text_width_mm(state, text_height=basis["text_height"]) / 2.0
        left_required = max(0.0, half_span - center_coord)
        right_required = max(0.0, center_coord + half_span - length)
        return left_required, right_required, basis

    def _minimum_dim_line_extension_mm(self, state):
        left_required, right_required, _ = self._text_extension_requirements(state)
        outside_min = 7.0 if self._outside_arrow_mode(state) else 0.0
        return max(outside_min, left_required, right_required)

    def resolve_geometry(self, state):
        basis = self._line_basis(state)
        if basis is None:
            return None

        p1 = basis["p1"]
        p2 = basis["p2"]
        line_pt = basis["line_pt"]
        dim_p1 = basis["dim_p1"]
        dim_p2 = basis["dim_p2"]
        base1 = basis["base1"]
        base2 = basis["base2"]
        dim_dir = basis["dim_dir"]
        normal = basis["normal"]
        text_point = basis["text_point"]
        text_angle = basis["text_angle"]
        text_height = basis["text_height"]
        extension_overrun = self._effective_extension_overrun_mm(state)
        ext_style_name = self._effective_extension_line_style_name(state)
        dim_style_name = self._effective_dim_line_style_name(state)
        requested_extension = self._requested_dim_line_extension_mm(state)
        left_required, right_required, _ = self._text_extension_requirements(state)
        outside_min = 7.0 if self._outside_arrow_mode(state) else 0.0
        left_extension = max(requested_extension, outside_min, left_required)
        right_extension = max(requested_extension, outside_min, right_required)

        ext1_start = Point(base1.x, base1.y)
        ext2_start = Point(base2.x, base2.y)
        ext1_end = Point(dim_p1.x + normal.x * extension_overrun, dim_p1.y + normal.y * extension_overrun)
        ext2_end = Point(dim_p2.x + normal.x * extension_overrun, dim_p2.y + normal.y * extension_overrun)

        dim_start = Point(dim_p1.x - dim_dir.x * left_extension, dim_p1.y - dim_dir.y * left_extension)
        dim_end = Point(dim_p2.x + dim_dir.x * right_extension, dim_p2.y + dim_dir.y * right_extension)

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
            "arrow_points": (
                [
                    {"point": dim_p1, "direction": Point(-dim_dir.x, -dim_dir.y)},
                    {"point": dim_p2, "direction": Point(dim_dir.x, dim_dir.y)},
                ]
                if self._outside_arrow_mode(state)
                else [
                    {"point": dim_p1, "direction": Point(dim_dir.x, dim_dir.y)},
                    {"point": dim_p2, "direction": Point(-dim_dir.x, -dim_dir.y)},
                ]
            ),
            "grips": {
                "p1": base1,
                "p2": base2,
                "line": line_pt,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point, state=None):
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
            if state is not None:
                geometry = self.resolve_geometry(state)
                if geometry and geometry["dimension_segments"]:
                    dim_segment = geometry["dimension_segments"][0]
                    self.manual_text_position = _translate_text_along_line(
                        new_point,
                        geometry["text_point"],
                        dim_segment.p1,
                        dim_segment.p2,
                    )
                    return
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

    def _outside_arrow_mode(self, state):
        return self.measured_value(state) < 12.0

    def _default_dim_line_extension_mm(self, state):
        if self._outside_arrow_mode(state):
            return 7.0
        return 0.0

    def _radial_basis(self, state):
        center = self.center_ref.resolve()
        edge = self.edge_ref.resolve()
        style = self._style(state)
        text_gap = style.text_gap_mm * self._text_offset_factor(state)
        text_height = self._effective_text_height_mm(state)

        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if radius < 1e-9:
            return None

        dir_x = (edge.x - center.x) / radius
        dir_y = (edge.y - center.y) / radius
        normal = Point(-dir_y, dir_x)

        if self.prefix == "⌀":
            base_start = Point(center.x - dir_x * radius, center.y - dir_y * radius)
            base_end = edge
            text_anchor_start = base_start
            text_anchor_end = base_end
        else:
            base_start = center
            base_end = edge
            text_anchor_start = center
            text_anchor_end = edge

        text_point = Point(
            (text_anchor_start.x + text_anchor_end.x) / 2.0 + normal.x * text_gap,
            (text_anchor_start.y + text_anchor_end.y) / 2.0 + normal.y * text_gap,
        )
        if self.manual_text_position is not None:
            text_point = _reapply_text_offset_on_line(self.manual_text_position, text_point, base_start, base_end)

        return {
            "center": center,
            "edge": edge,
            "radius": radius,
            "dir_x": dir_x,
            "dir_y": dir_y,
            "normal": normal,
            "base_start": base_start,
            "base_end": base_end,
            "text_point": text_point,
            "text_height": text_height,
            "text_angle": _normalized_text_angle(math.atan2(dir_y, dir_x)),
        }

    def _text_extension_requirements(self, state):
        basis = self._radial_basis(state)
        if basis is None:
            return 0.0, 0.0, None

        base_start = basis["base_start"]
        base_end = basis["base_end"]
        text_point = basis["text_point"]
        length = math.hypot(base_end.x - base_start.x, base_end.y - base_start.y)
        if length < 1e-9:
            return 0.0, 0.0, basis

        coord = (text_point.x - base_start.x) * basis["dir_x"] + (text_point.y - base_start.y) * basis["dir_y"]
        half_span = self._approx_text_width_mm(state, text_height=basis["text_height"]) / 2.0
        left_required = max(0.0, half_span - coord)
        right_required = max(0.0, coord + half_span - length)
        return left_required, right_required, basis

    def _minimum_dim_line_extension_mm(self, state):
        left_required, right_required, _ = self._text_extension_requirements(state)
        if self.prefix == "R":
            outside_min = 7.0 if self._outside_arrow_mode(state) else 0.0
            return max(left_required, right_required, outside_min)
        outside_min = 7.0 if self._outside_arrow_mode(state) else 0.0
        return max(left_required, right_required, outside_min)

    def resolve_geometry(self, state):
        basis = self._radial_basis(state)
        if basis is None:
            return None

        center = basis["center"]
        edge = basis["edge"]
        radius = basis["radius"]
        dir_x = basis["dir_x"]
        dir_y = basis["dir_y"]
        normal = basis["normal"]
        base_start = basis["base_start"]
        base_end = basis["base_end"]
        text_point = basis["text_point"]
        dim_style_name = self._effective_dim_line_style_name(state)
        text_height = basis["text_height"]
        requested_extension = self._requested_dim_line_extension_mm(state)
        left_required, right_required, _ = self._text_extension_requirements(state)
        outside_mode = self._outside_arrow_mode(state)

        if self.prefix == "⌀":
            outside_left = 7.0 if outside_mode else 0.0
            outside_right = 7.0 if outside_mode else 0.0
            left_extension = max(requested_extension, outside_left, left_required)
            right_extension = max(requested_extension, outside_right, right_required)
            dim_start = Point(base_start.x - dir_x * left_extension, base_start.y - dir_y * left_extension)
            dim_end = Point(base_end.x + dir_x * right_extension, base_end.y + dir_y * right_extension)
            if outside_mode:
                arrow_points = [
                    {"point": base_start, "direction": Point(-dir_x, -dir_y)},
                    {"point": base_end, "direction": Point(dir_x, dir_y)},
                ]
            else:
                arrow_points = [
                    {"point": base_start, "direction": Point(dir_x, dir_y)},
                    {"point": base_end, "direction": Point(-dir_x, -dir_y)},
                ]
        else:
            outside_left = 0.0
            outside_right = 7.0 if outside_mode else 0.0
            left_extension = max(requested_extension, outside_left, left_required)
            right_extension = max(requested_extension, outside_right, right_required)
            dim_start = Point(base_start.x - dir_x * left_extension, base_start.y - dir_y * left_extension)
            dim_end = Point(base_end.x + dir_x * right_extension, base_end.y + dir_y * right_extension)
            arrow_points = [
                {"point": edge, "direction": Point(dir_x, dir_y) if outside_mode else Point(-dir_x, -dir_y)},
            ]

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
            "text_angle": basis["text_angle"],
            "text_height_mm": text_height,
            "arrow_points": arrow_points,
            "grips": {
                "line": edge,
                "text": text_point,
            },
        }

    def move_grip(self, grip_name, new_point: Point, state=None):
        if grip_name == "line":
            old_edge = self.edge_ref.resolve()
            old_basis = self._radial_basis(state) if state is not None else None
            text_coord = None
            if old_basis is not None and self.manual_text_position is not None:
                text_coord = (
                    (self.manual_text_position.x - old_basis["base_start"].x) * old_basis["dir_x"]
                    + (self.manual_text_position.y - old_basis["base_start"].y) * old_basis["dir_y"]
                )
            edge_object = self.edge_ref.source_object
            if isinstance(edge_object, (Circle, Arc)):
                projected = _project_point_to_radial_object(edge_object, new_point)
                self.edge_ref.kind = "associative"
                self.edge_ref.point = projected
                self.edge_ref.ref_kind = "circle_angle" if isinstance(edge_object, Circle) else "arc_angle"
                self.edge_ref.source_object = edge_object
                self.leader_ref.break_associativity(projected)
                new_point = projected
            elif isinstance(edge_object, Rectangle) and self.edge_ref.ref_kind == "rectangle_fillet_angle":
                arcs = edge_object.fillet_arcs()
                idx = int(self.edge_ref.ref_index if self.edge_ref.ref_index is not None else -1)
                if 0 <= idx < len(arcs):
                    projected = _project_point_to_radial_object(arcs[idx], new_point)
                    self.edge_ref.kind = "associative"
                    self.edge_ref.point = projected
                    self.edge_ref.ref_kind = "rectangle_fillet_angle"
                    self.edge_ref.source_object = edge_object
                    self.edge_ref.ref_index = idx
                    self.leader_ref.break_associativity(projected)
                    new_point = projected
                else:
                    self.edge_ref.break_associativity(new_point)
                    self.leader_ref.break_associativity(new_point)
            else:
                self.edge_ref.break_associativity(new_point)
                self.leader_ref.break_associativity(new_point)

            if self.manual_text_position is not None:
                if state is not None and text_coord is not None:
                    new_basis = self._radial_basis(state)
                    if new_basis is not None:
                        self.manual_text_position = Point(
                            new_basis["base_start"].x + new_basis["dir_x"] * text_coord,
                            new_basis["base_start"].y + new_basis["dir_y"] * text_coord,
                        )
                        return
                self.manual_text_position = Point(
                    self.manual_text_position.x + (new_point.x - old_edge.x),
                    self.manual_text_position.y + (new_point.y - old_edge.y),
                )
        elif grip_name == "text":
            if state is not None:
                geometry = self.resolve_geometry(state)
                if geometry and geometry["dimension_segments"]:
                    dim_segment = geometry["dimension_segments"][0]
                    self.manual_text_position = _translate_text_along_line(
                        new_point,
                        geometry["text_point"],
                        dim_segment.p1,
                        dim_segment.p2,
                    )
                    return
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

    def _text_extension_requirements(self, state):
        p1, vertex, p2, arc_point, start, end = self._angles()
        style = self._style(state)
        text_height = self._effective_text_height_mm(state)
        radial_offset = (style.text_gap_mm + text_height * 0.5) * self._text_offset_factor(state)
        radius = math.hypot(arc_point.x - vertex.x, arc_point.y - vertex.y)
        if radius < 1e-9:
            return 0.0, 0.0, None

        bisector = start + _ccw_delta(start, end) / 2.0
        text_point = Point(
            vertex.x + (radius + radial_offset) * math.cos(bisector),
            vertex.y + (radius + radial_offset) * math.sin(bisector),
        )
        if self.manual_text_position is not None:
            manual_angle = math.atan2(self.manual_text_position.y - vertex.y, self.manual_text_position.x - vertex.x)
            text_point = Point(
                vertex.x + (radius + radial_offset) * math.cos(manual_angle),
                vertex.y + (radius + radial_offset) * math.sin(manual_angle),
            )

        text_angle = math.atan2(text_point.y - vertex.y, text_point.x - vertex.x)
        half_span_angle = (self._approx_text_width_mm(state, text_height=text_height) / 2.0) / radius
        left_required = max(0.0, -_signed_angle_delta(start, text_angle) + half_span_angle)
        right_required = max(0.0, _signed_angle_delta(end, text_angle) + half_span_angle)
        return left_required * radius, right_required * radius, {
            "vertex": vertex,
            "radius": radius,
            "text_point": text_point,
            "text_angle": text_angle,
            "text_height": text_height,
            "start": start,
            "end": end,
            "p1": p1,
            "p2": p2,
            "arc_point": arc_point,
        }

    def _minimum_dim_line_extension_mm(self, state):
        left_required, right_required, _ = self._text_extension_requirements(state)
        return max(7.0, left_required, right_required)

    def resolve_geometry(self, state):
        p1, vertex, p2, arc_point, start, end = self._angles()
        style = self._style(state)
        extension_overrun = self._effective_extension_overrun_mm(state)
        ext_style_name = self._effective_extension_line_style_name(state)
        dim_style_name = self._effective_dim_line_style_name(state)
        text_height = self._effective_text_height_mm(state)
        radial_offset = (style.text_gap_mm + text_height * 0.5) * self._text_offset_factor(state)
        radius = math.hypot(arc_point.x - vertex.x, arc_point.y - vertex.y)
        if radius < 1e-9:
            return None

        requested_extension = self._requested_dim_line_extension_mm(state)
        left_required, right_required, basis = self._text_extension_requirements(state)
        left_extension = max(requested_extension, 7.0, left_required)
        right_extension = max(requested_extension, 7.0, right_required)
        dim_start = start - (left_extension / radius if radius > 1e-9 else 0.0)
        dim_end = end + (right_extension / radius if radius > 1e-9 else 0.0)

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
            manual_angle = math.atan2(self.manual_text_position.y - vertex.y, self.manual_text_position.x - vertex.x)
            text_point = Point(
                vertex.x + (radius + radial_offset) * math.cos(manual_angle),
                vertex.y + (radius + radial_offset) * math.sin(manual_angle),
            )

        text_angle_at_arc = basis["text_angle"] if basis is not None else bisector
        tangent_angle = _normalized_text_angle(text_angle_at_arc + math.pi / 2.0)

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

    def move_grip(self, grip_name, new_point: Point, state=None):
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
            if state is not None:
                geometry = self.resolve_geometry(state)
                if geometry and geometry["dimension_arcs"]:
                    vertex = self.vertex_ref.resolve()
                    current_text = geometry["text_point"]
                    radius = math.hypot(current_text.x - vertex.x, current_text.y - vertex.y)
                    angle = math.atan2(new_point.y - vertex.y, new_point.x - vertex.x)
                    self.manual_text_position = Point(
                        vertex.x + radius * math.cos(angle),
                        vertex.y + radius * math.sin(angle),
                    )
                    return
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

    if isinstance(obj, Rectangle):
        arcs = obj.fillet_arcs()
        if not arcs:
            return None

        arc_index, arc = min(
            enumerate(arcs),
            key=lambda item: item[1].distance_to_point(leader_point.x, leader_point.y),
        )
        angle = math.atan2(leader_point.y - arc.center.y, leader_point.x - arc.center.x)
        angle = _clamp_angle_to_arc(angle, arc)
        edge_point = Point(
            arc.center.x + arc.radius * math.cos(angle),
            arc.center.y + arc.radius * math.sin(angle),
        )
        center_ref = GeometryReference(
            "associative",
            _point_from(arc.center),
            source_object=obj,
            ref_kind="rectangle_fillet_center",
            ref_index=arc_index,
        )
        edge_ref = GeometryReference(
            "associative",
            _point_from(edge_point),
            source_object=obj,
            ref_kind="rectangle_fillet_angle",
            ref_index=arc_index,
        )
        leader_ref = GeometryReference.static(_point_from(leader_point))
        return RadialDimension(center_ref, edge_ref, leader_ref, prefix=prefix, **kwargs)

    return None
