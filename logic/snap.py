# logic/snap.py

'''
Модуль системы привязок (Object Snaps / OSNAP).
Реализует поиск характерных точек примитивов для точного позиционирования курсора.

Типы привязок:
- Обязательные: Конец (Endpoint), Середина (Midpoint), Центр (Center)
- Дополнительные: Пересечение (Intersection), Перпендикуляр (Perpendicular), Касательная (Tangent)
'''

import math
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Tuple
from logic.geometry import Point, Segment, Circle, Arc, Rectangle, Ellipse, RegularPolygon, Spline


class SnapType(Enum):
    """Типы привязок."""
    ENDPOINT = auto()      # Конец (концевые точки отрезков, вершины и т.д.)
    MIDPOINT = auto()      # Середина (середина отрезка, ребра)
    CENTER = auto()        # Центр (центр окружности, эллипса, прямоугольника)
    INTERSECTION = auto()  # Пересечение (точка пересечения двух объектов)
    PERPENDICULAR = auto() # Перпендикуляр (точка на объекте, перпендикулярная к заданной точке)
    TANGENT = auto()       # Касательная (точка касания к окружности/эллипсу)
    NEAREST = auto()       # Ближайшая точка на объекте
    GRID = auto()          # Привязка к сетке


@dataclass
class SnapPoint:
    """Представляет точку привязки."""
    x: float
    y: float
    snap_type: SnapType
    source_object: object = None  # Объект-источник привязки
    priority: int = 0  # Приоритет привязки (меньше = выше приоритет)
    
    def distance_to(self, px: float, py: float) -> float:
        """Расстояние от точки привязки до заданной точки."""
        return math.sqrt((self.x - px)**2 + (self.y - py)**2)
    
    def to_point(self) -> Point:
        """Конвертирует в объект Point."""
        return Point(self.x, self.y)


class SnapManager:
    """
    Менеджер привязок. Ищет точки привязок на всех объектах сцены.
    """
    
    # Приоритеты привязок (меньше = выше приоритет)
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
        """
        Args:
            state: AppState - состояние приложения с настройками привязок
        """
        self.state = state
    
    def find_snap_point(
        self,
        cursor_x: float,
        cursor_y: float,
        snap_radius: float,
        from_point: Optional[Point] = None
    ) -> Optional[SnapPoint]:
        """
        Ищет ближайшую точку привязки в радиусе snap_radius от курсора.
        
        Args:
            cursor_x, cursor_y: Координаты курсора в мировых координатах
            snap_radius: Радиус поиска привязки в мировых координатах
            from_point: Точка начала построения (для перпендикуляра/касательной)
        
        Returns:
            SnapPoint или None, если привязка не найдена
        """
        if not self.state.snap_enabled:
            return None
        
        candidates: List[SnapPoint] = []
        
        # Собираем все потенциальные точки привязок
        
        # 1. ENDPOINT - концевые точки
        if self.state.snap_endpoint:
            candidates.extend(self._find_endpoints(cursor_x, cursor_y, snap_radius))
        
        # 2. MIDPOINT - середины
        if self.state.snap_midpoint:
            candidates.extend(self._find_midpoints(cursor_x, cursor_y, snap_radius))
        
        # 3. CENTER - центры
        if self.state.snap_center:
            candidates.extend(self._find_centers(cursor_x, cursor_y, snap_radius))
        
        # 4. INTERSECTION - пересечения
        if self.state.snap_intersection:
            candidates.extend(self._find_intersections(cursor_x, cursor_y, snap_radius))
        
        # 6. PERPENDICULAR - перпендикуляры
        if self.state.snap_perpendicular and from_point:
            candidates.extend(self._find_perpendiculars(cursor_x, cursor_y, snap_radius, from_point))
        
        # 7. TANGENT - касательные
        if self.state.snap_tangent and from_point:
            candidates.extend(self._find_tangents(cursor_x, cursor_y, snap_radius, from_point))
        
        # 8. GRID - привязка к сетке
        if self.state.snap_grid:
            grid_snap = self._find_grid_snap(cursor_x, cursor_y, snap_radius)
            if grid_snap:
                candidates.append(grid_snap)
        
        if not candidates:
            return None
        
        # Фильтруем кандидатов по расстоянию
        valid_candidates = [c for c in candidates if c.distance_to(cursor_x, cursor_y) <= snap_radius]
        
        if not valid_candidates:
            return None
        
        # Сортируем по приоритету, затем по расстоянию
        valid_candidates.sort(key=lambda c: (c.priority, c.distance_to(cursor_x, cursor_y)))
        
        return valid_candidates[0]
    
    # ==================== ENDPOINT - Концевые точки ====================
    
    def _find_endpoints(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:
        """Находит концевые точки примитивов."""
        points = []
        priority = self.PRIORITY[SnapType.ENDPOINT]
        
        # Отрезки - концы
        for seg in self.state.segments:
            for p in [seg.p1, seg.p2]:
                if self._in_range(p.x, p.y, cx, cy, radius):
                    points.append(SnapPoint(p.x, p.y, SnapType.ENDPOINT, seg, priority))
        
        # Дуги - концы
        for arc in self.state.arcs:
            # Начальная точка дуги
            start_x = arc.center.x + arc.radius * math.cos(arc.start_angle)
            start_y = arc.center.y + arc.radius * math.sin(arc.start_angle)
            if self._in_range(start_x, start_y, cx, cy, radius):
                points.append(SnapPoint(start_x, start_y, SnapType.ENDPOINT, arc, priority))
            
            # Конечная точка дуги
            end_x = arc.center.x + arc.radius * math.cos(arc.end_angle)
            end_y = arc.center.y + arc.radius * math.sin(arc.end_angle)
            if self._in_range(end_x, end_y, cx, cy, radius):
                points.append(SnapPoint(end_x, end_y, SnapType.ENDPOINT, arc, priority))
        
        # Прямоугольники - вершины
        for rect in self.state.rectangles:
            corners = rect.corners()
            for corner in corners:
                if self._in_range(corner.x, corner.y, cx, cy, radius):
                    points.append(SnapPoint(corner.x, corner.y, SnapType.ENDPOINT, rect, priority))
        
        # Многоугольники - вершины
        for poly in self.state.polygons:
            vertices = poly.vertices()
            for v in vertices:
                if self._in_range(v.x, v.y, cx, cy, radius):
                    points.append(SnapPoint(v.x, v.y, SnapType.ENDPOINT, poly, priority))
        
        # Сплайны - контрольные точки
        for spline in self.state.splines:
            for p in spline.control_points:
                if self._in_range(p.x, p.y, cx, cy, radius):
                    points.append(SnapPoint(p.x, p.y, SnapType.ENDPOINT, spline, priority))
        
        return points
    
    # ==================== MIDPOINT - Середины ====================
    
    def _find_midpoints(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:
        """Находит середины отрезков и рёбер."""
        points = []
        priority = self.PRIORITY[SnapType.MIDPOINT]
        
        # Отрезки
        for seg in self.state.segments:
            mid_x = (seg.p1.x + seg.p2.x) / 2
            mid_y = (seg.p1.y + seg.p2.y) / 2
            if self._in_range(mid_x, mid_y, cx, cy, radius):
                points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, seg, priority))
        
        # Прямоугольники - середины рёбер
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                mid_x = (edge.p1.x + edge.p2.x) / 2
                mid_y = (edge.p1.y + edge.p2.y) / 2
                if self._in_range(mid_x, mid_y, cx, cy, radius):
                    points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, rect, priority))
        
        # Многоугольники - середины рёбер
        for poly in self.state.polygons:
            edges = poly.edges()
            for edge in edges:
                mid_x = (edge.p1.x + edge.p2.x) / 2
                mid_y = (edge.p1.y + edge.p2.y) / 2
                if self._in_range(mid_x, mid_y, cx, cy, radius):
                    points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, poly, priority))
        
        # Дуги - середина дуги
        for arc in self.state.arcs:
            mid_angle = arc.start_angle + arc.sweep_angle / 2
            mid_x = arc.center.x + arc.radius * math.cos(mid_angle)
            mid_y = arc.center.y + arc.radius * math.sin(mid_angle)
            if self._in_range(mid_x, mid_y, cx, cy, radius):
                points.append(SnapPoint(mid_x, mid_y, SnapType.MIDPOINT, arc, priority))
        
        return points
    
    # ==================== CENTER - Центры ====================
    
    def _find_centers(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:
        """Находит центры окружностей, дуг, эллипсов, прямоугольников."""
        points = []
        priority = self.PRIORITY[SnapType.CENTER]
        
        # Окружности
        for circle in self.state.circles:
            if self._in_range(circle.center.x, circle.center.y, cx, cy, radius):
                points.append(SnapPoint(circle.center.x, circle.center.y, SnapType.CENTER, circle, priority))
        
        # Дуги
        for arc in self.state.arcs:
            if self._in_range(arc.center.x, arc.center.y, cx, cy, radius):
                points.append(SnapPoint(arc.center.x, arc.center.y, SnapType.CENTER, arc, priority))
        
        # Эллипсы
        for ellipse in self.state.ellipses:
            if self._in_range(ellipse.center.x, ellipse.center.y, cx, cy, radius):
                points.append(SnapPoint(ellipse.center.x, ellipse.center.y, SnapType.CENTER, ellipse, priority))
        
        # Прямоугольники
        for rect in self.state.rectangles:
            center = rect.center
            if self._in_range(center.x, center.y, cx, cy, radius):
                points.append(SnapPoint(center.x, center.y, SnapType.CENTER, rect, priority))
        
        # Многоугольники
        for poly in self.state.polygons:
            if self._in_range(poly.center.x, poly.center.y, cx, cy, radius):
                points.append(SnapPoint(poly.center.x, poly.center.y, SnapType.CENTER, poly, priority))
        
        return points
    
    # ==================== INTERSECTION - Пересечения ====================
    
    def _find_intersections(self, cx: float, cy: float, radius: float) -> List[SnapPoint]:
        """Находит точки пересечения объектов."""
        points = []
        priority = self.PRIORITY[SnapType.INTERSECTION]
        
        # Собираем все объекты для проверки пересечений
        all_objects = []
        all_objects.extend([(seg, 'segment') for seg in self.state.segments])
        all_objects.extend([(circle, 'circle') for circle in self.state.circles])
        all_objects.extend([(arc, 'arc') for arc in self.state.arcs])
        
        # Добавляем рёбра прямоугольников
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                all_objects.append((edge, 'segment'))
        
        # Добавляем рёбра многоугольников
        for poly in self.state.polygons:
            for edge in poly.edges():
                all_objects.append((edge, 'segment'))
        
        # Проверяем все пары объектов
        for i, (obj1, type1) in enumerate(all_objects):
            for obj2, type2 in all_objects[i+1:]:
                intersections = self._intersect_objects(obj1, type1, obj2, type2)
                for ix, iy in intersections:
                    if self._in_range(ix, iy, cx, cy, radius):
                        points.append(SnapPoint(ix, iy, SnapType.INTERSECTION, (obj1, obj2), priority))
        
        return points
    
    def _intersect_objects(self, obj1, type1: str, obj2, type2: str) -> List[Tuple[float, float]]:
        """Находит точки пересечения двух объектов."""
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
        return []
    
    def _intersect_segment_segment(self, seg1: Segment, seg2: Segment) -> List[Tuple[float, float]]:
        """Пересечение двух отрезков."""
        x1, y1 = seg1.p1.x, seg1.p1.y
        x2, y2 = seg1.p2.x, seg1.p2.y
        x3, y3 = seg2.p1.x, seg2.p1.y
        x4, y4 = seg2.p2.x, seg2.p2.y
        
        denom = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
        if abs(denom) < 1e-10:
            return []  # Параллельные или совпадающие
        
        t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / denom
        u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / denom
        
        if 0 <= t <= 1 and 0 <= u <= 1:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            return [(ix, iy)]
        return []
    
    def _intersect_segment_circle(self, seg: Segment, circle: Circle) -> List[Tuple[float, float]]:
        """Пересечение отрезка и окружности."""
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
        """Пересечение отрезка и дуги."""
        # Сначала находим пересечения с полной окружностью
        circle = Circle(arc.center, arc.radius)
        intersections = self._intersect_segment_circle(seg, circle)
        
        # Фильтруем только те, что лежат на дуге
        result = []
        for ix, iy in intersections:
            angle = math.atan2(iy - arc.center.y, ix - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((ix, iy))
        
        return result
    
    def _intersect_circle_circle(self, c1: Circle, c2: Circle) -> List[Tuple[float, float]]:
        """Пересечение двух окружностей."""
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
            # Одна точка касания
            points.append((px, py))
        else:
            # Две точки пересечения
            points.append((px + h * dy / d, py - h * dx / d))
            points.append((px - h * dy / d, py + h * dx / d))
        
        return points
    
    def _intersect_circle_arc(self, circle: Circle, arc: Arc) -> List[Tuple[float, float]]:
        """Пересечение окружности и дуги."""
        arc_circle = Circle(arc.center, arc.radius)
        intersections = self._intersect_circle_circle(circle, arc_circle)
        
        # Фильтруем только те, что лежат на дуге
        result = []
        for ix, iy in intersections:
            angle = math.atan2(iy - arc.center.y, ix - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((ix, iy))
        
        return result
    
    def _intersect_arc_arc(self, arc1: Arc, arc2: Arc) -> List[Tuple[float, float]]:
        """Пересечение двух дуг."""
        c1 = Circle(arc1.center, arc1.radius)
        c2 = Circle(arc2.center, arc2.radius)
        intersections = self._intersect_circle_circle(c1, c2)
        
        # Фильтруем только те, что лежат на обеих дугах
        result = []
        for ix, iy in intersections:
            angle1 = math.atan2(iy - arc1.center.y, ix - arc1.center.x)
            angle2 = math.atan2(iy - arc2.center.y, ix - arc2.center.x)
            if self._angle_on_arc(angle1, arc1) and self._angle_on_arc(angle2, arc2):
                result.append((ix, iy))
        
        return result
    
    # ==================== PERPENDICULAR - Перпендикуляры ====================
    
    def _find_perpendiculars(self, cx: float, cy: float, radius: float, from_point: Point) -> List[SnapPoint]:
        """Находит точки перпендикуляра к объектам из заданной точки."""
        points = []
        priority = self.PRIORITY[SnapType.PERPENDICULAR]
        
        # Перпендикуляр к отрезкам
        for seg in self.state.segments:
            perp = self._perpendicular_to_segment(from_point, seg)
            if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, seg, priority))
        
        # Перпендикуляр к рёбрам прямоугольников
        for rect in self.state.rectangles:
            edges, _ = rect.build_edges()
            for edge in edges:
                perp = self._perpendicular_to_segment(from_point, edge)
                if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                    points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, rect, priority))
        
        # Перпендикуляр к рёбрам многоугольников
        for poly in self.state.polygons:
            for edge in poly.edges():
                perp = self._perpendicular_to_segment(from_point, edge)
                if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                    points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, poly, priority))
        
        # Перпендикуляр к окружностям (ближайшая точка на окружности)
        for circle in self.state.circles:
            perp = self._perpendicular_to_circle(from_point, circle)
            if perp and self._in_range(perp[0], perp[1], cx, cy, radius):
                points.append(SnapPoint(perp[0], perp[1], SnapType.PERPENDICULAR, circle, priority))
        
        return points
    
    def _perpendicular_to_segment(self, point: Point, seg: Segment) -> Optional[Tuple[float, float]]:
        """Находит точку перпендикуляра от точки к отрезку."""
        dx = seg.p2.x - seg.p1.x
        dy = seg.p2.y - seg.p1.y
        len_sq = dx*dx + dy*dy
        
        if len_sq < 1e-10:
            return None
        
        t = ((point.x - seg.p1.x) * dx + (point.y - seg.p1.y) * dy) / len_sq
        
        # Проверяем, что точка проекции лежит на отрезке
        if 0 <= t <= 1:
            px = seg.p1.x + t * dx
            py = seg.p1.y + t * dy
            return (px, py)
        
        return None
    
    def _perpendicular_to_circle(self, point: Point, circle: Circle) -> Optional[Tuple[float, float]]:
        """Находит ближайшую точку на окружности (перпендикуляр из центра через точку)."""
        dx = point.x - circle.center.x
        dy = point.y - circle.center.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist < 1e-10:
            # Точка в центре - выбираем произвольное направление
            return (circle.center.x + circle.radius, circle.center.y)
        
        px = circle.center.x + circle.radius * dx / dist
        py = circle.center.y + circle.radius * dy / dist
        
        return (px, py)
    
    # ==================== TANGENT - Касательные ====================
    
    def _find_tangents(self, cx: float, cy: float, radius: float, from_point: Point) -> List[SnapPoint]:
        """Находит точки касания к окружностям и дугам из заданной точки."""
        points = []
        priority = self.PRIORITY[SnapType.TANGENT]
        
        # Касательные к окружностям
        for circle in self.state.circles:
            tangent_points = self._tangent_to_circle(from_point, circle)
            for tx, ty in tangent_points:
                if self._in_range(tx, ty, cx, cy, radius):
                    points.append(SnapPoint(tx, ty, SnapType.TANGENT, circle, priority))
        
        # Касательные к дугам
        for arc in self.state.arcs:
            tangent_points = self._tangent_to_arc(from_point, arc)
            for tx, ty in tangent_points:
                if self._in_range(tx, ty, cx, cy, radius):
                    points.append(SnapPoint(tx, ty, SnapType.TANGENT, arc, priority))
        
        return points
    
    def _tangent_to_circle(self, point: Point, circle: Circle) -> List[Tuple[float, float]]:
        """Находит точки касания к окружности из внешней точки."""
        dx = point.x - circle.center.x
        dy = point.y - circle.center.y
        d = math.sqrt(dx*dx + dy*dy)
        
        if d <= circle.radius:
            # Точка внутри или на окружности - касательных нет
            return []
        
        # Угол от центра до точки
        angle_to_point = math.atan2(dy, dx)
        
        # Угол касательной
        alpha = math.acos(circle.radius / d)
        
        points = []
        for sign in [-1, 1]:
            theta = angle_to_point + sign * alpha
            tx = circle.center.x + circle.radius * math.cos(theta)
            ty = circle.center.y + circle.radius * math.sin(theta)
            points.append((tx, ty))
        
        return points
    
    def _tangent_to_arc(self, point: Point, arc: Arc) -> List[Tuple[float, float]]:
        """Находит точки касания к дуге из внешней точки."""
        circle = Circle(arc.center, arc.radius)
        tangent_points = self._tangent_to_circle(point, circle)
        
        # Фильтруем только те, что лежат на дуге
        result = []
        for tx, ty in tangent_points:
            angle = math.atan2(ty - arc.center.y, tx - arc.center.x)
            if self._angle_on_arc(angle, arc):
                result.append((tx, ty))
        
        return result
    
    # ==================== GRID - Привязка к сетке ====================
    
    def _find_grid_snap(self, cx: float, cy: float, radius: float) -> Optional[SnapPoint]:
        """Находит ближайшую точку сетки."""
        step = self.state.grid_step
        if step <= 0:
            return None
        
        # Округляем до ближайшей точки сетки
        grid_x = round(cx / step) * step
        grid_y = round(cy / step) * step
        
        if self._in_range(grid_x, grid_y, cx, cy, radius):
            return SnapPoint(grid_x, grid_y, SnapType.GRID, None, self.PRIORITY[SnapType.GRID])
        
        return None
    
    # ==================== Вспомогательные методы ====================
    
    def _in_range(self, px: float, py: float, cx: float, cy: float, radius: float) -> bool:
        """Проверяет, находится ли точка в радиусе от курсора."""
        return (px - cx)**2 + (py - cy)**2 <= radius**2
    
    def _angle_on_arc(self, angle: float, arc: Arc) -> bool:
        """Проверяет, лежит ли угол на дуге."""
        # Нормализуем угол в диапазон [0, 2π)
        angle = angle % (2 * math.pi)
        if angle < 0:
            angle += 2 * math.pi
        
        start = arc.start_angle % (2 * math.pi)
        if start < 0:
            start += 2 * math.pi
        
        end = arc.end_angle % (2 * math.pi)
        if end < 0:
            end += 2 * math.pi
        
        # Вычисляем sweep angle
        sweep = arc.sweep_angle
        
        # Проверяем, лежит ли угол на дуге
        delta = (angle - start) % (2 * math.pi)
        return delta <= sweep + 1e-6


# Символы для отображения разных типов привязок в UI
SNAP_SYMBOLS = {
    SnapType.ENDPOINT: "□",       # Квадрат
    SnapType.MIDPOINT: "△",       # Треугольник
    SnapType.CENTER: "○",         # Круг
    SnapType.INTERSECTION: "×",   # Крестик
    SnapType.PERPENDICULAR: "⊥",  # Перпендикуляр
    SnapType.TANGENT: "◇",        # Ромб
    SnapType.NEAREST: "∞",        # Бесконечность
    SnapType.GRID: "+",           # Плюс
}

# Названия привязок для UI
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