import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Tuple
from logic.geometry import Point, Segment, Circle, Arc, Rectangle, Ellipse, RegularPolygon, Spline

class SnapType(Enum):

    ENDPOINT = auto()
    MIDPOINT = auto()
    CENTER = auto()
    INTERSECTION = auto()
    PERPENDICULAR = auto()
    TANGENT = auto()
    NEAREST = auto()
    GRID = auto()

@dataclass
class SnapPoint:

    x: float
    y: float
    snap_type: SnapType
    source_object: object = None
    priority: int = 0
    
    def distance_to(self, px: float, py: float) -> float:

        return math.sqrt((self.x - px)**2 + (self.y - py)**2)
    
    def to_point(self) -> Point:

        return Point(self.x, self.y)

class SnapManager:

    PRIORITY = {
        SnapType.ENDPOINT: 1,
        SnapType.CENTER: 2,
        SnapType.MIDPOINT: 3,
        SnapType.INTERSECTION: 4,
        SnapType.PERPENDICULAR: 5,
        SnapType.TANGENT: 6,
        SnapType.NEAREST: 7,
        SnapType.GRID: 8,
    }
    
    def __init__(self, state):

        self.state = state
    
    def find_snap_point(
        self,
        cursor_x: float,
        cursor_y: float,
        snap_radius: float,
        from_point: Optional[Point] = None
    ) -> Optional[SnapPoint]:

        if not self.state.snap_enabled:
            return None
        
        candidates: List[SnapPoint] = []
        
        if self.state.snap_endpoint:
            candidates.extend(self._find_endpoints(cursor_x, cursor_y, snap_radius))
        
        if self.state.snap_midpoint:
            candidates.extend(self._find_midpoints(cursor_x, cursor_y, snap_radius))
        
        if self.state.snap_center:
            candidates.extend(self._find_centers(cursor_x, cursor_y, snap_radius))
        
        if self.state.snap_intersection:
            candidates.extend(self._find_intersections(cursor_x, cursor_y, snap_radius))
        
        if self.state.snap_perpendicular and from_point:
            candidates.extend(self._find_perpendiculars(cursor_x, cursor_y, snap_radius, from_point))
        
        if self.state.snap_tangent and from_point:
            candidates.extend(self._find_tangents(cursor_x, cursor_y, snap_radius, from_point))
        
        if self.state.snap_grid:
            grid_snap = self._find_grid_snap(cursor_x, cursor_y, snap_radius)
            if grid_snap:
                candidates.append(grid_snap)
        
        if not candidates:
            return None
        
        valid_candidates = [c for c in candidates if c.distance_to(cursor_x, cursor_y) <= snap_radius]
        
        if not valid_candidates:
            return None
        
        valid_candidates.sort(key=lambda c: (c.priority, c.distance_to(cursor_x, cursor_y)))
        
        return valid_candidates[0]
    
    def _find_endpoints(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.ENDPOINT]
        
        for seg in self.state.segments:
            for p in [seg.p1, seg.p2]:
                if self._in_range(p.x, p.y, cx, cy, radius):
                    points.append(SnapPoint(p.x, p.y, SnapType.ENDPOINT, seg, priority))
        
        for arc in self.state.arcs:
            start_x = arc.center.x + arc.radius * math.cos(arc.start_angle)
            start_y = arc.center.y + arc.radius * math.sin(arc.start_angle)
            if self._in_range(start_x, start_y, cx, cy, radius):
                points.append(SnapPoint(start_x, start_y, SnapType.ENDPOINT, arc, priority))
            
            end_x = arc.center.x + arc.radius * math.cos(arc.end_angle)
            end_y = arc.center.y + arc.radius * math.sin(arc.end_angle)
            if self._in_range(end_x, end_y, cx, cy, radius):
                points.append(SnapPoint(end_x, end_y, SnapType.ENDPOINT, arc, priority))
        
        for rect in self.state.rectangles:
            corners = rect.corners()
            for corner in corners:
                if self._in_range(corner.x, corner.y, cx, cy, radius):
                    points.append(SnapPoint(corner.x, corner.y, SnapType.ENDPOINT, rect, priority))
        
        for poly in self.state.polygons:
            vertices = poly.vertices()
            for v in vertices:
                if self._in_range(v.x, v.y, cx, cy, radius):
                    points.append(SnapPoint(v.x, v.y, SnapType.ENDPOINT, poly, priority))
        
        for spline in self.state.splines:
            for p in spline.control_points:
                if self._in_range(p.x, p.y, cx, cy, radius):
                    points.append(SnapPoint(p.x, p.y, SnapType.ENDPOINT, spline, priority))
        
        return points
    
    def _find_midpoints(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.MIDPOINT]
        
        for seg in self.state.segments:
            mid_x = (seg.p1.x + seg.p2.x) / 2
            mid_y = (seg.p1.y + seg.p2.y) / 2
            if self._in_range(mid_x, mid_y, cx, cy, radius):
                points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, seg, priority))
        
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                mid_x = (edge.p1.x + edge.p2.x) / 2
                mid_y = (edge.p1.y + edge.p2.y) / 2
                if self._in_range(mid_x, mid_y, cx, cy, radius):
                    points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, rect, priority))
        
        for poly in self.state.polygons:
            edges = poly.edges()
            for edge in edges:
                mid_x = (edge.p1.x + edge.p2.x) / 2
                mid_y = (edge.p1.y + edge.p2.y) / 2
                if self._in_range(mid_x, mid_y, cx, cy, radius):
                    points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, poly, priority))
        
        for arc in self.state.arcs:
            mid_angle = arc.start_angle + arc.sweep_angle / 2
            mid_x = arc.center.x + arc.radius * math.cos(mid_angle)
            mid_y = arc.center.y + arc.radius * math.sin(mid_angle)
            if self._in_range(mid_x, mid_y, cx, cy, radius):
                points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, arc, priority))
        
        return points
    
    def _find_centers(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.CENTER]
        
        for circle in self.state.circles:
            if self._in_range(circle.center.x, circle.center.y, cx, cy, radius):
                points.append(SnapPoint(circle.center.x, circle.center.y, SnapType.CENTER, circle, priority))
        
        for arc in self.state.arcs:
            if self._in_range(arc.center.x, arc.center.y, cx, cy, radius):
                points.append(SnapPoint(arc.center.x, arc.center.y, SnapType.CENTER, arc, priority))
        
        for ellipse in self.state.ellipses:
            if self._in_range(ellipse.center.x, ellipse.center.y, cx, cy, radius):
                points.append(SnapPoint(ellipse.center.x, ellipse.center.y, SnapType.CENTER, ellipse, priority))
        
        for rect in self.state.rectangles:
            center = rect.center
            if self._in_range(center.x, center.y, cx, cy, radius):
                points.append(SnapPoint(center.x, center.y, SnapType.CENTER, rect, priority))
        
        for poly in self.state.polygons:
            if self._in_range(poly.center.x, poly.center.y, cx, cy, radius):
                points.append(SnapPoint(poly.center.x, poly.center.y, SnapType.CENTER, poly, priority))
        
        return points
    
    def _find_intersections(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.INTERSECTION]
        
        all_objects = []
        all_objects.extend([(seg, 'segment') for seg in self.state.segments])
        all_objects.extend([(circle, 'circle') for circle in self.state.circles])
        all_objects.extend([(arc, 'arc') for arc in self.state.arcs])
        all_objects.extend([(ellipse, 'ellipse') for ellipse in self.state.ellipses])
        
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                all_objects.append((edge, 'segment'))
        
        for poly in self.state.polygons:
            for edge in poly.edges():
                all_objects.append((edge, 'segment'))
        
        for i, (obj1, type1) in enumerate(all_objects):
            for obj2, type2 in all_objects[i+1:]:
                intersections = self._intersect_objects(obj1, type1, obj2, type2)
                for ix, iy in intersections:
                    if self._in_range(ix, iy, cx, cy, radius):
                        points.append(SnapPoint(ix, iy, SnapType.INTERSECTION, (obj1, obj2), priority))
        
        return points
    
    def _intersect_objects(self, obj1, type1: str, obj2, type2: str) -> List[Tuple[float, float]]:

        if type1 == 'segment' and type2 == 'segment':
            return self._intersect_segment_segment(obj1, obj2)
        elif type1 == 'segment' and type2 == 'circle':
            return self._intersect_segment_circle(obj1, obj2)
        elif type1 == 'circle' and type2 == 'segment':
            return self._intersect_segment_circle(obj2, obj1)
        elif type1 == 'circle' and type2 == 'circle':
            return self._intersect_circle_circle(obj1, obj2)
        elif type1 == 'segment' and type2 == 'arc':
            return self._intersect_segment_arc(obj1, obj2)
        elif type1 == 'arc' and type2 == 'segment':
            return self._intersect_segment_arc(obj2, obj1)
        elif type1 == 'circle' and type2 == 'arc':
            return self._intersect_circle_arc(obj1, obj2)
        elif type1 == 'arc' and type2 == 'circle':
            return self._intersect_circle_arc(obj2, obj1)
        elif type1 == 'arc' and type2 == 'arc':
            return self._intersect_arc_arc(obj1, obj2)
        elif type1 == 'segment' and type2 == 'ellipse':
            return self._intersect_segment_ellipse(obj1, obj2)
        elif type1 == 'ellipse' and type2 == 'segment':
            return self._intersect_segment_ellipse(obj2, obj1)
        elif type1 == 'circle' and type2 == 'ellipse':
            return self._intersect_circle_ellipse(obj1, obj2)
        elif type1 == 'ellipse' and type2 == 'circle':
            return self._intersect_circle_ellipse(obj2, obj1)
        elif type1 == 'arc' and type2 == 'ellipse':
            return self._intersect_arc_ellipse(obj1, obj2)
        elif type1 == 'ellipse' and type2 == 'arc':
            return self._intersect_arc_ellipse(obj2, obj1)
        elif type1 == 'ellipse' and type2 == 'ellipse':
            return self._intersect_ellipse_ellipse(obj1, obj2)
        return []
    
    def _intersect_segment_segment(self, seg1: Segment, seg2: Segment) -> List[Tuple[float, float]]:

        x1, y1 = seg1.p1.x, seg1.p1.y
        x2, y2 = seg1.p2.x, seg1.p2.y
        x3, y3 = seg2.p1.x, seg2.p1.y
        x4, y4 = seg2.p2.x, seg2.p2.y
        
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return []
        
        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            return [(ix, iy)]
        return []
    
    def _intersect_segment_circle(self, seg: Segment, circle: Circle) -> List[Tuple[float, float]]:

        dx = seg.p2.x - seg.p1.x
        dy = seg.p2.y - seg.p1.y
        fx = seg.p1.x - circle.center.x
        fy = seg.p1.y - circle.center.y
        
        a = dx*dx + dy*dy
        b = 2 * (fx*dx + fy*dy)
        c = fx*fx + fy*fy - circle.radius*circle.radius
        
        discriminant = b*b - 4*a*c
        if discriminant < 0 or a < 1e-10:
            return []
        
        points = []
        sqrt_disc = math.sqrt(discriminant)
        
        for sign in [-1, 1]:
            t = (-b + sign * sqrt_disc) / (2*a)
            if 0 <= t <= 1:
                ix = seg.p1.x + t * dx
                iy = seg.p1.y + t * dy
                points.append((ix, iy))
        
        return points
    
    def _intersect_segment_arc(self, seg: Segment, arc: Arc) -> List[Tuple[float, float]]:

        circle = Circle(arc.center, arc.radius)
        intersections = self._intersect_segment_circle(seg, circle)
        
        result = []
        for ix, iy in intersections:
            angle = math.atan2(iy - arc.center.y, ix - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((ix, iy))
        
        return result
    
    def _intersect_circle_circle(self, c1: Circle, c2: Circle) -> List[Tuple[float, float]]:

        dx = c2.center.x - c1.center.x
        dy = c2.center.y - c1.center.y
        d = math.sqrt(dx*dx + dy*dy)
        
        if d > c1.radius + c2.radius or d < abs(c1.radius - c2.radius) or d < 1e-10:
            return []
        
        a = (c1.radius*c1.radius - c2.radius*c2.radius + d*d) / (2*d)
        h_sq = c1.radius*c1.radius - a*a
        if h_sq < 0:
            return []
        h = math.sqrt(h_sq)
        
        px = c1.center.x + a * dx / d
        py = c1.center.y + a * dy / d
        
        points = []
        if h < 1e-10:
            points.append((px, py))
        else:
            points.append((px + h * dy / d, py - h * dx / d))
            points.append((px - h * dy / d, py + h * dx / d))
        
        return points
    
    def _intersect_circle_arc(self, circle: Circle, arc: Arc) -> List[Tuple[float, float]]:

        arc_circle = Circle(arc.center, arc.radius)
        intersections = self._intersect_circle_circle(circle, arc_circle)
        
        result = []
        for ix, iy in intersections:
            angle = math.atan2(iy - arc.center.y, ix - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((ix, iy))
        
        return result
    
    def _intersect_arc_arc(self, arc1: Arc, arc2: Arc) -> List[Tuple[float, float]]:

        c1 = Circle(arc1.center, arc1.radius)
        c2 = Circle(arc2.center, arc2.radius)
        intersections = self._intersect_circle_circle(c1, c2)
        
        result = []
        for ix, iy in intersections:
            angle1 = math.atan2(iy - arc1.center.y, ix - arc1.center.x)
            angle2 = math.atan2(iy - arc2.center.y, ix - arc2.center.x)
            if self._angle_on_arc(angle1, arc1) and self._angle_on_arc(angle2, arc2):
                result.append((ix, iy))
        
        return result
    
    def _intersect_segment_ellipse(self, seg: Segment, ellipse: Ellipse) -> List[Tuple[float, float]]:
        """Аналитическое пересечение отрезка и эллипса через аффинное преобразование к единичной окружности."""
        e1x, e1y, a, e2x, e2y, b = ellipse._basis()
        if a < 1e-12 or b < 1e-12:
            return []

        # Переводим концы отрезка в локальную систему эллипса
        def to_local(px, py):
            rx = px - ellipse.center.x
            ry = py - ellipse.center.y
            lx = (rx * e1x + ry * e1y) / a
            ly = (rx * e2x + ry * e2y) / b
            return lx, ly

        lx1, ly1 = to_local(seg.p1.x, seg.p1.y)
        lx2, ly2 = to_local(seg.p2.x, seg.p2.y)

        # В локальных координатах эллипс — единичная окружность
        dx = lx2 - lx1
        dy = ly2 - ly1
        a_coef = dx * dx + dy * dy
        b_coef = 2 * (lx1 * dx + ly1 * dy)
        c_coef = lx1 * lx1 + ly1 * ly1 - 1.0

        if a_coef < 1e-15:
            return []

        discriminant = b_coef * b_coef - 4 * a_coef * c_coef
        if discriminant < 0:
            return []

        points = []
        sqrt_disc = math.sqrt(discriminant)
        for sign in [-1, 1]:
            t = (-b_coef + sign * sqrt_disc) / (2 * a_coef)
            if 0 <= t <= 1:
                ix = seg.p1.x + t * (seg.p2.x - seg.p1.x)
                iy = seg.p1.y + t * (seg.p2.y - seg.p1.y)
                points.append((ix, iy))
        return points

    def _intersect_circle_ellipse(self, circle: Circle, ellipse: Ellipse) -> List[Tuple[float, float]]:
        """Пересечение окружности и эллипса через семплирование контура эллипса."""
        pts = ellipse.sample_points(360)
        results = []
        r = circle.radius
        cx, cy = circle.center.x, circle.center.y
        for i in range(len(pts) - 1):
            ax, ay = pts[i].x, pts[i].y
            bx, by = pts[i + 1].x, pts[i + 1].y
            # Проверяем пересечение отрезка (a, b) с окружностью
            dx = bx - ax
            dy = by - ay
            fx = ax - cx
            fy = ay - cy
            a_c = dx * dx + dy * dy
            b_c = 2 * (fx * dx + fy * dy)
            c_c = fx * fx + fy * fy - r * r
            if a_c < 1e-15:
                continue
            disc = b_c * b_c - 4 * a_c * c_c
            if disc < 0:
                continue
            sqrt_d = math.sqrt(disc)
            for sign in [-1, 1]:
                t = (-b_c + sign * sqrt_d) / (2 * a_c)
                if 0 <= t <= 1:
                    ix = ax + t * dx
                    iy = ay + t * dy
                    # Исключаем дубликаты
                    dup = False
                    for ex, ey in results:
                        if (ix - ex) ** 2 + (iy - ey) ** 2 < 1e-6:
                            dup = True
                            break
                    if not dup:
                        results.append((ix, iy))
        return results

    def _intersect_arc_ellipse(self, arc: Arc, ellipse: Ellipse) -> List[Tuple[float, float]]:
        """Пересечение дуги и эллипса: через circle-ellipse + фильтр по дуге."""
        circle = Circle(arc.center, arc.radius)
        intersections = self._intersect_circle_ellipse(circle, ellipse)
        result = []
        for ix, iy in intersections:
            angle = math.atan2(iy - arc.center.y, ix - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((ix, iy))
        return result

    def _intersect_ellipse_ellipse(self, e1: Ellipse, e2: Ellipse) -> List[Tuple[float, float]]:
        """Пересечение двух эллипсов через семплирование обоих контуров."""
        pts1 = e1.sample_points(360)
        pts2 = e2.sample_points(360)
        results = []

        for i in range(len(pts1) - 1):
            ax1, ay1 = pts1[i].x, pts1[i].y
            bx1, by1 = pts1[i + 1].x, pts1[i + 1].y
            for j in range(len(pts2) - 1):
                ax2, ay2 = pts2[j].x, pts2[j].y
                bx2, by2 = pts2[j + 1].x, pts2[j + 1].y
                # Пересечение двух отрезков
                d1x = bx1 - ax1
                d1y = by1 - ay1
                d2x = bx2 - ax2
                d2y = by2 - ay2
                denom = d1x * d2y - d1y * d2x
                if abs(denom) < 1e-12:
                    continue
                t = ((ax2 - ax1) * d2y - (ay2 - ay1) * d2x) / denom
                u = ((ax2 - ax1) * d1y - (ay2 - ay1) * d1x) / denom
                if 0 <= t <= 1 and 0 <= u <= 1:
                    ix = ax1 + t * d1x
                    iy = ay1 + t * d1y
                    dup = False
                    for ex, ey in results:
                        if (ix - ex) ** 2 + (iy - ey) ** 2 < 1e-6:
                            dup = True
                            break
                    if not dup:
                        results.append((ix, iy))
        return results

    def _find_perpendiculars(self, cx: float, cy: float, radius: float, from_point: Point) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.PERPENDICULAR]
        
        for seg in self.state.segments:
            perp = self._perpendicular_to_segment(from_point, seg)
            if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, seg, priority))
        
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                perp = self._perpendicular_to_segment(from_point, edge)
                if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                    points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, rect, priority))
        
        for poly in self.state.polygons:
            for edge in poly.edges():
                perp = self._perpendicular_to_segment(from_point, edge)
                if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                    points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, poly, priority))
        
        for circle in self.state.circles:
            perp = self._perpendicular_to_circle(from_point, circle)
            if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, circle, priority))
        
        for arc in self.state.arcs:
            perp = self._perpendicular_to_circle(from_point, Circle(arc.center, arc.radius))
            if perp:
                angle = math.atan2(perp[1] - arc.center.y, perp[0] - arc.center.x)
                if self._angle_on_arc(angle, arc) and self._in_range(perp[0], perp[1], cx, cy, radius):
                    points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, arc, priority))

        for ellipse in self.state.ellipses:
            perp = self._perpendicular_to_ellipse(from_point, ellipse)
            if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, ellipse, priority))
        
        return points
    
    def _perpendicular_to_segment(self, point: Point, seg: Segment) -> Optional[Tuple[float, float]]:

        dx = seg.p2.x - seg.p1.x
        dy = seg.p2.y - seg.p1.y
        len_sq = dx*dx + dy*dy
        
        if len_sq < 1e-10:
            return None
        
        t = ((point.x - seg.p1.x) * dx + (point.y - seg.p1.y) * dy) / len_sq
        
        if 0 <= t <= 1:
            px = seg.p1.x + t * dx
            py = seg.p1.y + t * dy
            return (px, py)
        
        return None
    
    def _perpendicular_to_circle(self, point: Point, circle: Circle) -> Optional[Tuple[float, float]]:

        dx = point.x - circle.center.x
        dy = point.y - circle.center.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 1e-10:
            return (circle.center.x + circle.radius, circle.center.y)
        
        px = circle.center.x + circle.radius * dx / dist
        py = circle.center.y + circle.radius * dy / dist
        
        return (px, py)
    
    def _find_tangents(self, cx: float, cy: float, radius: float, from_point: Point) -> List[SnapPoint]:

        points = []
        priority = self.PRIORITY[SnapType.TANGENT]
        
        for circle in self.state.circles:
            tangent_points = self._tangent_to_circle(from_point, circle)
            for tx, ty in tangent_points:
                if self._in_range(tx, ty, cx, cy, radius):
                    points.append(SnapPoint(tx, ty, SnapType.TANGENT, circle, priority))
        
        for arc in self.state.arcs:
            tangent_points = self._tangent_to_arc(from_point, arc)
            for tx, ty in tangent_points:
                if self._in_range(tx, ty, cx, cy, radius):
                    points.append(SnapPoint(tx, ty, SnapType.TANGENT, arc, priority))
        
        for ellipse in self.state.ellipses:
            tangent_points = self._tangent_to_ellipse(from_point, ellipse)
            for tx, ty in tangent_points:
                if self._in_range(tx, ty, cx, cy, radius):
                    points.append(SnapPoint(tx, ty, SnapType.TANGENT, ellipse, priority))
        
        return points
    
    def _tangent_to_circle(self, point: Point, circle: Circle) -> List[Tuple[float, float]]:

        dx = point.x - circle.center.x
        dy = point.y - circle.center.y
        d = math.sqrt(dx*dx + dy*dy)
        
        if d <= circle.radius:
            return []
        
        angle_to_point = math.atan2(dy, dx)
        
        alpha = math.acos(circle.radius / d)
        
        points = []
        for sign in [-1, 1]:
            theta = angle_to_point + sign * alpha
            tx = circle.center.x + circle.radius * math.cos(theta)
            ty = circle.center.y + circle.radius * math.sin(theta)
            points.append((tx, ty))
        
        return points
    
    def _tangent_to_arc(self, point: Point, arc: Arc) -> List[Tuple[float, float]]:

        circle = Circle(arc.center, arc.radius)
        tangent_points = self._tangent_to_circle(point, circle)
        
        result = []
        for tx, ty in tangent_points:
            angle = math.atan2(ty - arc.center.y, tx - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((tx, ty))
        
        return result
    
    def _perpendicular_to_ellipse(self, point: Point, ellipse: Ellipse) -> Optional[Tuple[float, float]]:
        """Ближайшая точка на эллипсе (перпендикулярная проекция) — итерационный метод."""
        e1x, e1y, a, e2x, e2y, b = ellipse._basis()
        if a < 1e-12 or b < 1e-12:
            return None

        # Переводим точку в локальную систему эллипса
        rx = point.x - ellipse.center.x
        ry = point.y - ellipse.center.y
        local_x = rx * e1x + ry * e1y
        local_y = rx * e2x + ry * e2y

        # Начальное приближение угла
        theta = math.atan2(local_y / b if abs(b) > 1e-12 else 0,
                           local_x / a if abs(a) > 1e-12 else 0)

        # Итерационное уточнение (метод Ньютона для минимизации расстояния)
        for _ in range(50):
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            ex = a * cos_t
            ey = b * sin_t
            # Производная расстояния^2 по theta
            dx = local_x - ex
            dy = local_y - ey
            # d(dist^2)/dtheta = 2 * (dx * a * sin_t - dy * b * cos_t)
            deriv = dx * a * sin_t - dy * b * cos_t
            # d2(dist^2)/dtheta^2
            deriv2 = (dx * a * cos_t + dy * b * sin_t +
                      a * a * sin_t * sin_t + b * b * cos_t * cos_t)
            if abs(deriv2) < 1e-15:
                break
            delta = deriv / deriv2
            theta -= delta
            if abs(delta) < 1e-12:
                break

        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        # Обратная трансформация в мировые координаты
        wx = ellipse.center.x + a * cos_t * e1x + b * sin_t * e2x
        wy = ellipse.center.y + a * cos_t * e1y + b * sin_t * e2y
        return (wx, wy)

    def _tangent_to_ellipse(self, point: Point, ellipse: Ellipse) -> List[Tuple[float, float]]:
        """Точки касания из внешней точки к эллипсу (аналитическое решение)."""
        e1x, e1y, a, e2x, e2y, b = ellipse._basis()
        if a < 1e-12 or b < 1e-12:
            return []

        # Переводим точку в локальную систему эллипса
        rx = point.x - ellipse.center.x
        ry = point.y - ellipse.center.y
        px = rx * e1x + ry * e1y
        py = rx * e2x + ry * e2y

        # Проверяем, находится ли точка внутри эллипса
        if (px / a) ** 2 + (py / b) ** 2 <= 1.0 + 1e-6:
            return []

        # Касательная к эллипсу в точке E(t) = (a cos t, b sin t):
        #   x·cos(t)/a + y·sin(t)/b = 1
        # Точка (px, py) лежит на этой касательной, если:
        #   (px/a)·cos(t) + (py/b)·sin(t) = 1
        # Это уравнение вида A·cos(t) + B·sin(t) = 1,
        # решение: t = φ ± arccos(1/R), где R = √(A²+B²), φ = atan2(B, A)

        A = px / a
        B = py / b
        R = math.sqrt(A * A + B * B)

        if R < 1.0 + 1e-9:
            return []

        phi = math.atan2(B, A)
        delta = math.acos(max(-1.0, min(1.0, 1.0 / R)))

        results = []
        for sign in [-1, 1]:
            t = phi + sign * delta
            ct = math.cos(t)
            st = math.sin(t)
            # Обратная трансформация в мировые координаты
            wx = ellipse.center.x + a * ct * e1x + b * st * e2x
            wy = ellipse.center.y + a * ct * e1y + b * st * e2y
            results.append((wx, wy))
        return results

    def _find_grid_snap(self, cx: float, cy: float, radius: float) -> Optional[SnapPoint]:

        step = self.state.grid_step
        if step <= 0:
            return None
        
        grid_x = round(cx / step) * step
        grid_y = round(cy / step) * step
        
        if self._in_range(grid_x, grid_y, cx, cy, radius):
            return SnapPoint(grid_x, grid_y, SnapType.GRID, None, self.PRIORITY[SnapType.GRID])
        
        return None
    
    def _in_range(self, px: float, py: float, cx: float, cy: float, radius: float) -> bool:

        return (px - cx)**2 + (py - cy)**2 <= radius**2
    
    def _angle_on_arc(self, angle: float, arc: Arc) -> bool:

        angle = angle % (2 * math.pi)
        if angle < 0:
            angle += 2 * math.pi
        
        start = arc.start_angle % (2 * math.pi)
        if start < 0:
            start += 2 * math.pi
        
        end = arc.end_angle % (2 * math.pi)
        if end < 0:
            end += 2 * math.pi
        
        sweep = arc.sweep_angle
        
        delta = (angle - start) % (2 * math.pi)
        return delta <= sweep + 1e-6

SNAP_SYMBOLS = {
    SnapType.ENDPOINT: "□",
    SnapType.MIDPOINT: "△",
    SnapType.CENTER: "○",
    SnapType.INTERSECTION: "×",
    SnapType.PERPENDICULAR: "⊥",
    SnapType.TANGENT: "◇",
    SnapType.NEAREST: "∞",
    SnapType.GRID: "+",
}

SNAP_NAMES = {
    SnapType.ENDPOINT: "Конец",
    SnapType.MIDPOINT: "Середина",
    SnapType.CENTER: "Центр",
    SnapType.INTERSECTION: "Пересечение",
    SnapType.PERPENDICULAR: "Перпендикуляр",
    SnapType.TANGENT: "Касательная",
    SnapType.NEAREST: "Ближайшая",
    SnapType.GRID: "Сетка",
}
