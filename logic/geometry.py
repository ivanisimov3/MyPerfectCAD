import math
from abc import ABC, abstractmethod

class GeometryPrimitive(ABC):

    def __init__(self, style_name='solid_main', color='black'):
        self.style_name = style_name
        self.color = color
        self.layer = "0"

    @abstractmethod
    def distance_to_point(self, mx, my):    # Для выделения объектов

        raise NotImplementedError

    @property
    def primitive_type(self):

        return self.__class__.__name__.lower()

class Point:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def get_polar_coords(self):
        r = math.sqrt(self.x**2 + self.y**2)
        theta_rad = math.atan2(self.y, self.x)
        return r, theta_rad

    def set_from_polar(self, r, theta_rad):
        self.x = r * math.cos(theta_rad)
        self.y = r * math.sin(theta_rad)

    def __repr__(self):
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"

class Segment(GeometryPrimitive):
    def __init__(self, p1: Point, p2: Point, style_name = 'solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.p1 = p1
        self.p2 = p2

    @property
    def length(self):
        return math.sqrt((self.p2.x - self.p1.x)**2 + (self.p2.y - self.p1.y)**2)

    @property
    def angle(self):
        return math.atan2(self.p2.y - self.p1.y, self.p2.x - self.p1.x)

    def distance_to_point(self, mx, my):
        x1, y1 = self.p1.x, self.p1.y
        x2, y2 = self.p2.x, self.p2.y

        l2 = (x1 - x2)**2 + (y1 - y2)**2
        if l2 == 0:
            return math.sqrt((mx - x1)**2 + (my - y1)**2)

        t = ((mx - x1) * (x2 - x1) + (my - y1) * (y2 - y1)) / l2
        t = max(0, min(1, t))

        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)

        return math.sqrt((mx - proj_x)**2 + (my - proj_y)**2)

    def __repr__(self):
        return f"Segment({self.p1}, {self.p2}, style='{self.style_name}')"

class Spline(GeometryPrimitive):

    def __init__(self, control_points, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.control_points = list(control_points)

    def _catmull_rom_point(self, p0, p1, p2, p3, t):    # Алгоритм Катмулла-Рома для плавной кривой

        t2 = t * t
        t3 = t2 * t
        x = 0.5 * (
            (2 * p1.x)
            + (-p0.x + p2.x) * t
            + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2
            + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3
        )
        y = 0.5 * (
            (2 * p1.y)
            + (-p0.y + p2.y) * t
            + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2
            + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3
        )
        return Point(x, y)

    def sample_points(self, samples_per_segment=20):

        pts = self.control_points
        if not pts:
            return []
        if len(pts) == 1:
            return [Point(pts[0].x, pts[0].y)]

        ext = [pts[0]] + pts + [pts[-1]]
        result = []
        segs = len(pts) - 1

        for i in range(segs):
            p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
            for j in range(samples_per_segment + 1):
                if result and j == 0:
                    continue
                t = j / samples_per_segment
                result.append(self._catmull_rom_point(p0, p1, p2, p3, t))
        return result

    def distance_to_point(self, mx, my):

        pts = self.sample_points()
        if not pts:
            return float('inf')
        if len(pts) == 1:
            return math.sqrt((mx - pts[0].x) ** 2 + (my - pts[0].y) ** 2)

        def _seg_dist(ax, ay, bx, by, px, py):
            l2 = (bx - ax) ** 2 + (by - ay) ** 2
            if l2 == 0:
                return math.sqrt((px - ax) ** 2 + (py - ay) ** 2)
            t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / l2
            t = max(0.0, min(1.0, t))
            proj_x = ax + t * (bx - ax)
            proj_y = ay + t * (by - ay)
            return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)

        min_dist = float('inf')
        for a, b in zip(pts[:-1], pts[1:]):
            min_dist = min(min_dist, _seg_dist(a.x, a.y, b.x, b.y, mx, my))
        return min_dist

    def approximate_length(self):

        pts = self.sample_points()
        if len(pts) < 2:
            return 0.0
        length = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            length += math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2)
        return length

    def __repr__(self):
        return f"Spline(points={len(self.control_points)}, style='{self.style_name}')"

class Circle(GeometryPrimitive):
    @classmethod
    def from_center_radius(cls, center: Point, radius: float, style_name='solid_main', color='black'):

        circle = cls(center, radius, style_name, color)
        circle.creation_method = 'center_radius'
        circle.creation_data = {'center': Point(center.x, center.y), 'radius': radius}
        return circle

    @classmethod
    def from_center_diameter(cls, center: Point, diameter: float, style_name='solid_main', color='black'):

        radius = diameter / 2.0
        circle = cls(center, radius, style_name, color)
        circle.creation_method = 'center_diameter'
        circle.creation_data = {'center': Point(center.x, center.y), 'diameter': diameter}
        return circle

    @classmethod
    def from_two_points(cls, p1: Point, p2: Point, style_name='solid_main', color='black'):

        center_x = (p1.x + p2.x) / 2.0
        center_y = (p1.y + p2.y) / 2.0
        center = Point(center_x, center_y)
        radius = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2) / 2.0
        circle = cls(center, radius, style_name, color)
        circle.creation_method = 'two_points'
        circle.creation_data = {'p1': Point(p1.x, p1.y), 'p2': Point(p2.x, p2.y)}
        return circle

    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point, style_name='solid_main', color='black'):

        A = 2 * (p2.x - p1.x)
        B = 2 * (p2.y - p1.y)
        C = p2.x**2 - p1.x**2 + p2.y**2 - p1.y**2

        D = 2 * (p3.x - p1.x)
        E = 2 * (p3.y - p1.y)
        F = p3.x**2 - p1.x**2 + p3.y**2 - p1.y**2

        det = A * E - B * D
        if abs(det) < 1e-10:
            raise ValueError("Три точки лежат на одной прямой")

        h = (C * E - B * F) / det
        k = (A * F - C * D) / det

        center = Point(h, k)
        radius = math.sqrt((p1.x - h)**2 + (p1.y - k)**2)

        circle = cls(center, radius, style_name, color)
        circle.creation_method = 'three_points'
        circle.creation_data = {'p1': Point(p1.x, p1.y), 'p2': Point(p2.x, p2.y), 'p3': Point(p3.x, p3.y)}
        return circle

    def __init__(self, center: Point, radius: float, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.radius = abs(radius)
        self.creation_method = 'center_radius'
        self.creation_data = {'center': Point(center.x, center.y), 'radius': radius}

    @property
    def diameter(self):

        return 2 * self.radius

    @property
    def circumference(self):

        return 2 * math.pi * self.radius

    @property
    def area(self):

        return math.pi * self.radius**2

    def distance_to_point(self, mx, my):

        dist_to_center = math.sqrt((mx - self.center.x)**2 + (my - self.center.y)**2)

        return abs(dist_to_center - self.radius)

    def contains_point(self, point: Point, tolerance=1e-6):

        dist = math.sqrt((point.x - self.center.x)**2 + (point.y - self.center.y)**2)
        return abs(dist - self.radius) < tolerance

    def __repr__(self):
        return f"Circle(center={self.center}, radius={self.radius:.2f}, style='{self.style_name}')"

class Arc(GeometryPrimitive):

    @staticmethod
    def _normalize_angle(angle_rad):

        two_pi = 2 * math.pi
        angle_rad = angle_rad % two_pi
        return angle_rad

    @staticmethod
    def _is_angle_between_ccw(test_angle, start_angle, end_angle):

        test_angle = Arc._normalize_angle(test_angle)
        start_angle = Arc._normalize_angle(start_angle)
        end_angle = Arc._normalize_angle(end_angle)

        if start_angle <= end_angle:
            return start_angle - 1e-9 <= test_angle <= end_angle + 1e-9
        return test_angle >= start_angle - 1e-9 or test_angle <= end_angle + 1e-9

    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point, style_name='solid_main', color='black'):

        circle = Circle.from_three_points(p1, p2, p3, style_name=style_name, color=color)
        start_ang = math.atan2(p1.y - circle.center.y, p1.x - circle.center.x)
        mid_ang = math.atan2(p2.y - circle.center.y, p2.x - circle.center.x)
        end_ang = math.atan2(p3.y - circle.center.y, p3.x - circle.center.x)

        def _ccw_delta(a, b):
            return (b - a) % (2 * math.pi)

        mid_on_ccw = _ccw_delta(start_ang, mid_ang) <= _ccw_delta(start_ang, end_ang) + 1e-9

        if mid_on_ccw:
            final_start, final_end = start_ang, end_ang
        else:
            final_start, final_end = start_ang, end_ang
            final_start, final_end = final_end, final_start

        arc = cls(circle.center, circle.radius, final_start, final_end, style_name, color)
        arc.creation_method = 'three_points'
        arc.creation_data = {'p1': Point(p1.x, p1.y), 'p2': Point(p2.x, p2.y), 'p3': Point(p3.x, p3.y)}
        return arc

    @classmethod
    def from_center_angles(cls, center: Point, radius: float, start_angle_rad: float, end_angle_rad: float, style_name='solid_main', color='black'):

        arc = cls(center, abs(radius), start_angle_rad, end_angle_rad, style_name, color)
        arc.creation_method = 'center_angles'
        arc.creation_data = {
            'center': Point(center.x, center.y), 
            'radius': abs(radius), 
            'start_angle': start_angle_rad, 
            'end_angle': end_angle_rad
        }
        return arc

    def __init__(self, center: Point, radius: float, start_angle_rad: float, end_angle_rad: float, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.radius = abs(radius)
        self.start_angle = self._normalize_angle(start_angle_rad)
        self.end_angle = self._normalize_angle(end_angle_rad)
        self.creation_method = 'center_angles'
        self.creation_data = {
            'center': Point(center.x, center.y),
            'radius': abs(radius),
            'start_angle': start_angle_rad,
            'end_angle': end_angle_rad
        }

    @property
    def sweep_angle(self):

        delta = self.end_angle - self.start_angle
        if delta < 0:
            delta += 2 * math.pi
        if abs(delta) < 1e-9:
            return 2 * math.pi
        return delta

    def distance_to_point(self, mx, my):

        dx = mx - self.center.x
        dy = my - self.center.y
        dist_to_center = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)

        if self._is_angle_between_ccw(angle, self.start_angle, self.end_angle):
            return abs(dist_to_center - self.radius)

        p_start = Point(
            self.center.x + self.radius * math.cos(self.start_angle),
            self.center.y + self.radius * math.sin(self.start_angle)
        )
        p_end = Point(
            self.center.x + self.radius * math.cos(self.end_angle),
            self.center.y + self.radius * math.sin(self.end_angle)
        )

        dist_start = math.sqrt((mx - p_start.x) ** 2 + (my - p_start.y) ** 2)
        dist_end = math.sqrt((mx - p_end.x) ** 2 + (my - p_end.y) ** 2)
        return min(dist_start, dist_end)

    def __repr__(self):
        sa_deg = math.degrees(self.start_angle)
        ea_deg = math.degrees(self.end_angle)
        return f"Arc(center={self.center}, radius={self.radius:.2f}, start={sa_deg:.1f}°, end={ea_deg:.1f}°, style='{self.style_name}')"

class Rectangle(GeometryPrimitive):

    def __init__(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        style_name: str = 'solid_main',
        color: str = 'black',
        corner_type: str = 'none',
        corner_value: float = 0.0
    ):
        super().__init__(style_name=style_name, color=color)
        self.min_x = min(min_x, max_x)
        self.max_x = max(min_x, max_x)
        self.min_y = min(min_y, max_y)
        self.max_y = max(min_y, max_y)
        self.corner_type = corner_type
        self.corner_value = max(0.0, float(corner_value))
        self.creation_method = 'two_points'
        self.creation_data = {
            'p1': Point(self.min_x, self.min_y),
            'p2': Point(self.max_x, self.max_y)
        }

    @classmethod
    def from_two_points(cls, p1: Point, p2: Point, **kwargs):

        rect = cls(p1.x, p1.y, p2.x, p2.y, **kwargs)
        rect.creation_method = 'two_points'
        rect.creation_data = {'p1': Point(p1.x, p1.y), 'p2': Point(p2.x, p2.y)}
        return rect

    @classmethod
    def from_corner_size(cls, corner: Point, width: float, height: float, **kwargs):

        dx = float(width)
        dy = float(height)
        rect = cls(corner.x, corner.y, corner.x + dx, corner.y + dy, **kwargs)
        rect.creation_method = 'corner_size'
        rect.creation_data = {'corner': Point(corner.x, corner.y), 'width': width, 'height': height}
        return rect

    @classmethod
    def from_center_size(cls, center: Point, width: float, height: float, **kwargs):

        w2 = float(width) / 2.0
        h2 = float(height) / 2.0
        rect = cls(center.x - w2, center.y - h2, center.x + w2, center.y + h2, **kwargs)
        rect.creation_method = 'center_size'
        rect.creation_data = {'center': Point(center.x, center.y), 'width': width, 'height': height}
        return rect

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center(self) -> Point:
        return Point((self.min_x + self.max_x) / 2.0, (self.min_y + self.max_y) / 2.0)

    def corners(self):

        return [
            Point(self.min_x, self.min_y),
            Point(self.max_x, self.min_y),
            Point(self.max_x, self.max_y),
            Point(self.min_x, self.max_y),
        ]

    def _clamped_corner_value(self):
        return min(self.corner_value, self.width / 2.0, self.height / 2.0)

    def build_edges(self):

        cv = self._clamped_corner_value()
        corners = self.corners()

        segments = []
        arcs = []

        if self.corner_type == 'none' or cv <= 0:
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                segments.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
            return segments, arcs

        if self.corner_type == 'chamfer':   # Фаски
            d = cv
            bl, br, tr, tl = corners

            bottom_start = Point(bl.x + d, bl.y)
            bottom_end = Point(br.x - d, br.y)
            right_start = Point(br.x, br.y + d)
            right_end = Point(tr.x, tr.y - d)
            top_start = Point(tr.x - d, tr.y)
            top_end = Point(tl.x + d, tl.y)
            left_start = Point(tl.x, tl.y - d)
            left_end = Point(bl.x, bl.y + d)

            segments.extend([
                Segment(bottom_start, bottom_end, style_name=self.style_name, color=self.color),
                Segment(bottom_end, right_start, style_name=self.style_name, color=self.color),
                Segment(right_start, right_end, style_name=self.style_name, color=self.color),
                Segment(right_end, top_start, style_name=self.style_name, color=self.color),
                Segment(top_start, top_end, style_name=self.style_name, color=self.color),
                Segment(top_end, left_start, style_name=self.style_name, color=self.color),
                Segment(left_start, left_end, style_name=self.style_name, color=self.color),
                Segment(left_end, bottom_start, style_name=self.style_name, color=self.color),
            ])
            return segments, arcs

        if self.corner_type == 'fillet':    # Скругления
            r = cv
            bl, br, tr, tl = corners
            segments.extend([
                Segment(Point(bl.x + r, bl.y), Point(br.x - r, br.y), style_name=self.style_name, color=self.color),
                Segment(Point(br.x, br.y + r), Point(tr.x, tr.y - r), style_name=self.style_name, color=self.color),
                Segment(Point(tr.x - r, tr.y), Point(tl.x + r, tl.y), style_name=self.style_name, color=self.color),
                Segment(Point(tl.x, tl.y - r), Point(bl.x, bl.y + r), style_name=self.style_name, color=self.color),
            ])

            arcs.extend([
                Arc.from_center_angles(Point(bl.x + r, bl.y + r), r, math.pi, 1.5 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(br.x - r, br.y + r), r, 1.5 * math.pi, 2 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(tr.x - r, tr.y - r), r, 0.0, 0.5 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(tl.x + r, tl.y - r), r, 0.5 * math.pi, math.pi, style_name=self.style_name, color=self.color),
            ])
            return segments, arcs

        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
            segments.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
        return segments, arcs

    def distance_to_point(self, mx, my):

        segments, arcs = self.build_edges()
        distances = []
        for seg in segments:
            distances.append(seg.distance_to_point(mx, my))
        for arc in arcs:
            distances.append(arc.distance_to_point(mx, my))
        return min(distances) if distances else 0.0

    def __repr__(self):
        return (
            f"Rectangle([{self.min_x:.2f},{self.min_y:.2f}]→[{self.max_x:.2f},{self.max_y:.2f}], "
            f"corner={self.corner_type}:{self.corner_value:.2f}, style='{self.style_name}')"
        )

class RegularPolygon(GeometryPrimitive):

    @classmethod
    def from_center_radius(cls, center: Point, radius: float, sides: int, variant: str = 'inscribed', start_angle: float = 0.0, style_name='solid_main', color='black'):

        return cls(center, radius, sides, variant=variant, start_angle=start_angle, style_name=style_name, color=color)

    def __init__(self, center: Point, radius: float, sides: int, variant: str = 'inscribed', start_angle: float = 0.0, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.base_radius = abs(radius)
        self.sides = max(3, int(sides))
        self.variant = variant if variant in ('inscribed', 'circumscribed') else 'inscribed'
        self.start_angle = float(start_angle)

    def _circumradius(self):

        if self.variant == 'circumscribed':
            return self.base_radius / math.cos(math.pi / self.sides)
        return self.base_radius

    def vertices(self):

        r = self._circumradius()
        base_angle = self.start_angle
        if self.variant == 'circumscribed':
            base_angle += math.pi / self.sides

        verts = []
        step = 2 * math.pi / self.sides
        for i in range(self.sides):
            ang = base_angle + step * i
            x = self.center.x + r * math.cos(ang)
            y = self.center.y + r * math.sin(ang)
            verts.append(Point(x, y))
        return verts

    def edges(self):

        verts = self.vertices()
        segs = []
        n = len(verts)
        for i in range(n):
            p1 = verts[i]
            p2 = verts[(i + 1) % n]
            segs.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
        return segs

    def distance_to_point(self, mx, my):

        edges = self.edges()
        if not edges:
            return 0.0
        return min(edge.distance_to_point(mx, my) for edge in edges)

    def __repr__(self):
        return (
            f"RegularPolygon(center={self.center}, sides={self.sides}, "
            f"variant={self.variant}, style='{self.style_name}')"
        )

class Ellipse(GeometryPrimitive):

    @classmethod
    def from_center_axes(cls, center: Point, axis_point_a: Point, axis_point_b: Point, style_name='solid_main', color='black'):

        return cls(center, axis_point_a, axis_point_b, style_name, color)

    def __init__(self, center: Point, axis_point_a: Point, axis_point_b: Point, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.axis_point_a = axis_point_a
        self.axis_point_b = axis_point_b

    def _basis(self):

        v1x = self.axis_point_a.x - self.center.x
        v1y = self.axis_point_a.y - self.center.y
        v2x = self.axis_point_b.x - self.center.x
        v2y = self.axis_point_b.y - self.center.y

        a = math.sqrt(v1x * v1x + v1y * v1y)
        b_raw = math.sqrt(v2x * v2x + v2y * v2y)

        if a < 1e-9:
            a = 1e-6
            v1x, v1y = 1.0, 0.0
        if b_raw < 1e-9:
            b_raw = 1e-6
            v2x, v2y = 0.0, 1.0

        e1x, e1y = v1x / a, v1y / a
        proj = e1x * v2x + e1y * v2y
        ortho_x = v2x - proj * e1x
        ortho_y = v2y - proj * e1y
        ortho_len = math.sqrt(ortho_x * ortho_x + ortho_y * ortho_y)
        if ortho_len < 1e-9:
            ortho_x, ortho_y = -e1y, e1x
            ortho_len = 1.0
        e2x, e2y = ortho_x / ortho_len, ortho_y / ortho_len
        b = ortho_len
        return e1x, e1y, a, e2x, e2y, b

    def sample_points(self, num_points=180):

        e1x, e1y, a, e2x, e2y, b = self._basis()
        pts = []
        for i in range(num_points + 1):
            ang = (2 * math.pi * i) / num_points
            cos_a = math.cos(ang)
            sin_a = math.sin(ang)
            x = self.center.x + a * cos_a * e1x + b * sin_a * e2x
            y = self.center.y + a * cos_a * e1y + b * sin_a * e2y
            pts.append(Point(x, y))
        return pts

    def bounding_box(self):

        e1x, e1y, a, e2x, e2y, b = self._basis()
        dx = abs(e1x) * a + abs(e2x) * b
        dy = abs(e1y) * a + abs(e2y) * b
        return (
            self.center.x - dx,
            self.center.x + dx,
            self.center.y - dy,
            self.center.y + dy,
        )

    def perimeter_approx(self): # Формула Рамануджана для периметра

        _, _, a, _, _, b = self._basis()
        h = ((a - b) ** 2) / ((a + b) ** 2 + 1e-12)
        return math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))

    def distance_to_point(self, mx, my):

        e1x, e1y, a, e2x, e2y, b = self._basis()
        rx = mx - self.center.x
        ry = my - self.center.y

        local_x = rx * e1x + ry * e1y
        local_y = rx * e2x + ry * e2y

        q = (local_x / a) ** 2 + (local_y / b) ** 2

        if q < 1e-12:
            return min(a, b)

        scale = 1 / math.sqrt(q)
        nearest_x = local_x * scale
        nearest_y = local_y * scale
        dx = local_x - nearest_x
        dy = local_y - nearest_y
        return math.sqrt(dx * dx + dy * dy)

    def __repr__(self):
        min_x, max_x, min_y, max_y = self.bounding_box()
        return (
            f"Ellipse(center={self.center}, "
            f"box=([{min_x:.2f},{min_y:.2f}]→[{max_x:.2f},{max_y:.2f}]), "
            f"style='{self.style_name}')"
        )
