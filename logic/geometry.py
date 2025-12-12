# logic/geometry.py

'''
Этот файл отвечает за геометрию: вычисление длины, углов, перевод из полярных координат в декартовы и обратно. 
Он ничего не знает о том, как это рисуется на экране, он работает только с числами.
'''

import math
from abc import ABC, abstractmethod


class GeometryPrimitive(ABC):
    """Базовый класс для всех геометрических примитивов."""

    def __init__(self, style_name='solid_main', color='black'):
        self.style_name = style_name
        self.color = color

    @abstractmethod
    def distance_to_point(self, mx, my):
        """Кратчайшее расстояние от произвольной точки до примитива."""
        raise NotImplementedError

    @property
    def primitive_type(self):
        """Читаемое имя примитива, пригодное для логов/UI."""
        return self.__class__.__name__.lower()

class Point:
    # Устанавливаем точку в декартовых по умолчанию
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    # Используется для отображения координат в полярной системе
    def get_polar_coords(self):
        r = math.sqrt(self.x**2 + self.y**2)
        theta_rad = math.atan2(self.y, self.x)
        return r, theta_rad

    # Используется при вводе координат в полярной системе
    def set_from_polar(self, r, theta_rad):
        self.x = r * math.cos(theta_rad)
        self.y = r * math.sin(theta_rad)

    def __repr__(self):
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"

class Segment(GeometryPrimitive):
    # Инициализация отрезка по умолчанию
    def __init__(self, p1: Point, p2: Point, style_name = 'solid_main', color='black', kinks_count=None, waves_count=None):
        super().__init__(style_name=style_name, color=color)
        self.p1 = p1
        self.p2 = p2
        # Храним только ID стиля (ссылку), а не параметры.
        # Это позволяет менять стиль централизованно в Менеджере.
        self.kinks_count = kinks_count
        self.waves_count = waves_count

    # @property - декоратор для обращения к методу объекта без ()
    # Метод вычисляет и возвращает длину отрезка
    @property
    def length(self):
        return math.sqrt((self.p2.x - self.p1.x)**2 + (self.p2.y - self.p1.y)**2)

    # Метод вычисляет и возвращает угол наклона отрезка в радианах
    @property
    def angle(self):
        return math.atan2(self.p2.y - self.p1.y, self.p2.x - self.p1.x)

    # Вычисляет кратчайшее расстояние от точки (курсора) до отрезка.
    # Используется контроллером для определения клика по линии.
    def distance_to_point(self, mx, my):
        x1, y1 = self.p1.x, self.p1.y
        x2, y2 = self.p2.x, self.p2.y

        l2 = (x1 - x2)**2 + (y1 - y2)**2
        if l2 == 0:
            return math.sqrt((mx - x1)**2 + (my - y1)**2)

        # Проекция точки на прямую (параметр t от 0 до 1)
        t = ((mx - x1) * (x2 - x1) + (my - y1) * (y2 - y1)) / l2
        t = max(0, min(1, t))

        proj_x = x1 + t * (x2 - x1)
        proj_y = y1 + t * (y2 - y1)

        return math.sqrt((mx - proj_x)**2 + (my - proj_y)**2)

    def __repr__(self):
        return f"Segment({self.p1}, {self.p2}, style='{self.style_name}')"


class Spline(GeometryPrimitive):
    """Гладкий сплайн по набору контрольных точек (Catmull-Rom)."""

    def __init__(self, control_points, style_name='solid_main', color='black', kinks_count=None, waves_count=None):
        super().__init__(style_name=style_name, color=color)
        self.control_points = list(control_points)
        # Поддержка параметров для зигзага/волны, как у отрезков
        self.kinks_count = kinks_count
        self.waves_count = waves_count

    def _catmull_rom_point(self, p0, p1, p2, p3, t):
        """Возвращает точку кривой Catmull-Rom для параметра t ∈ [0,1]."""
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
        """Возвращает дискретизацию сплайна в виде списка точек."""
        pts = self.control_points
        if not pts:
            return []
        if len(pts) == 1:
            return [Point(pts[0].x, pts[0].y)]

        # Дублируем крайние точки для устойчивости
        ext = [pts[0]] + pts + [pts[-1]]
        result = []
        segs = len(pts) - 1

        for i in range(segs):
            p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
            for j in range(samples_per_segment + 1):
                # избегаем дублирования стыков
                if result and j == 0:
                    continue
                t = j / samples_per_segment
                result.append(self._catmull_rom_point(p0, p1, p2, p3, t))
        return result

    def distance_to_point(self, mx, my):
        """Минимальное расстояние до сплайна (по дискретизации)."""
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
        """Оценка длины сплайна по дискретизации."""
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
    # Создание окружности различными способами
    @classmethod
    def from_center_radius(cls, center: Point, radius: float, style_name='solid_main', color='black'):
        """Создание окружности по центру и радиусу"""
        return cls(center, radius, style_name, color)

    @classmethod
    def from_center_diameter(cls, center: Point, diameter: float, style_name='solid_main', color='black'):
        """Создание окружности по центру и диаметру"""
        radius = diameter / 2.0
        return cls(center, radius, style_name, color)

    @classmethod
    def from_two_points(cls, p1: Point, p2: Point, style_name='solid_main', color='black'):
        """Создание окружности по двум точкам (диаметр)"""
        # Центр - середина отрезка между точками
        center_x = (p1.x + p2.x) / 2.0
        center_y = (p1.y + p2.y) / 2.0
        center = Point(center_x, center_y)
        # Радиус - половина расстояния между точками
        radius = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2) / 2.0
        return cls(center, radius, style_name, color)

    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point, style_name='solid_main', color='black'):
        """Создание окружности по трем точкам на окружности"""
        # Используем формулы для вычисления окружности по трем точкам
        # Матричный метод для решения системы уравнений

        # Уравнения окружности: (x - h)^2 + (y - k)^2 = r^2
        # Раскрываем: x^2 - 2hx + h^2 + y^2 - 2ky + k^2 = r^2
        # Для трех точек получаем систему:
        # x1^2 - 2h x1 + h^2 + y1^2 - 2k y1 + k^2 = r^2
        # x2^2 - 2h x2 + h^2 + y2^2 - 2k y2 + k^2 = r^2
        # x3^2 - 2h x3 + h^2 + y3^2 - 2k y3 + k^2 = r^2

        # Вычитаем первое уравнение из второго и третьего:
        # (x2^2 - x1^2) - 2h(x2 - x1) + (y2^2 - y1^2) - 2k(y2 - y1) = 0
        # (x3^2 - x1^2) - 2h(x3 - x1) + (y3^2 - y1^2) - 2k(y3 - y1) = 0

        # Обозначим:
        # A = 2(x2 - x1), B = 2(y2 - y1), C = x2^2 - x1^2 + y2^2 - y1^2
        # D = 2(x3 - x1), E = 2(y3 - y1), F = x3^2 - x1^2 + y3^2 - y1^2

        A = 2 * (p2.x - p1.x)
        B = 2 * (p2.y - p1.y)
        C = p2.x**2 - p1.x**2 + p2.y**2 - p1.y**2

        D = 2 * (p3.x - p1.x)
        E = 2 * (p3.y - p1.y)
        F = p3.x**2 - p1.x**2 + p3.y**2 - p1.y**2

        # Решаем систему:
        # A*h + B*k = C
        # D*h + E*k = F

        # Используем метод Крамера
        det = A * E - B * D
        if abs(det) < 1e-10:  # Проверка на вырожденность
            raise ValueError("Три точки лежат на одной прямой")

        h = (C * E - B * F) / det
        k = (A * F - C * D) / det

        center = Point(h, k)
        radius = math.sqrt((p1.x - h)**2 + (p1.y - k)**2)

        return cls(center, radius, style_name, color)

    def __init__(self, center: Point, radius: float, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.radius = abs(radius)  # Радиус всегда положительный

    # Свойства окружности
    @property
    def diameter(self):
        """Диаметр окружности"""
        return 2 * self.radius

    @property
    def circumference(self):
        """Длина окружности"""
        return 2 * math.pi * self.radius

    @property
    def area(self):
        """Площадь окружности"""
        return math.pi * self.radius**2

    def distance_to_point(self, mx, my):
        """Расстояние от точки до окружности (до ближайшей точки на окружности)"""
        # Расстояние от точки до центра
        dist_to_center = math.sqrt((mx - self.center.x)**2 + (my - self.center.y)**2)

        # Расстояние до окружности = |dist_to_center - radius|
        return abs(dist_to_center - self.radius)

    def contains_point(self, point: Point, tolerance=1e-6):
        """Проверяет, находится ли точка на окружности"""
        dist = math.sqrt((point.x - self.center.x)**2 + (point.y - self.center.y)**2)
        return abs(dist - self.radius) < tolerance

    def __repr__(self):
        return f"Circle(center={self.center}, radius={self.radius:.2f}, style='{self.style_name}')"


class Arc(GeometryPrimitive):
    """Дуга окружности."""

    @staticmethod
    def _normalize_angle(angle_rad):
        """Нормализует угол в диапазон [0, 2*pi)."""
        two_pi = 2 * math.pi
        angle_rad = angle_rad % two_pi
        return angle_rad

    @staticmethod
    def _is_angle_between_ccw(test_angle, start_angle, end_angle):
        """Проверяет, лежит ли угол test_angle на дуге от start_angle до end_angle против часовой стрелки."""
        test_angle = Arc._normalize_angle(test_angle)
        start_angle = Arc._normalize_angle(start_angle)
        end_angle = Arc._normalize_angle(end_angle)

        if start_angle <= end_angle:
            return start_angle - 1e-9 <= test_angle <= end_angle + 1e-9
        return test_angle >= start_angle - 1e-9 or test_angle <= end_angle + 1e-9

    @classmethod
    def from_three_points(cls, p1: Point, p2: Point, p3: Point, style_name='solid_main', color='black'):
        """Строит дугу по трем точкам: начало, точка на дуге, конец."""
        circle = Circle.from_three_points(p1, p2, p3, style_name=style_name, color=color)
        # Вычисляем углы относительно центра окружности
        start_ang = math.atan2(p1.y - circle.center.y, p1.x - circle.center.x)
        mid_ang = math.atan2(p2.y - circle.center.y, p2.x - circle.center.x)
        end_ang = math.atan2(p3.y - circle.center.y, p3.x - circle.center.x)

        def _ccw_delta(a, b):
            return (b - a) % (2 * math.pi)

        # Проверяем, лежит ли mid на дуге от start к end против часовой стрелки
        mid_on_ccw = _ccw_delta(start_ang, mid_ang) <= _ccw_delta(start_ang, end_ang) + 1e-9

        if mid_on_ccw:
            final_start, final_end = start_ang, end_ang
        else:
            # Идем от end к start, чтобы включить mid
            final_start, final_end = start_ang, end_ang
            final_start, final_end = final_end, final_start

        return cls(circle.center, circle.radius, final_start, final_end, style_name, color)

    @classmethod
    def from_center_angles(cls, center: Point, radius: float, start_angle_rad: float, end_angle_rad: float, style_name='solid_main', color='black'):
        """Строит дугу по центру, радиусу и нач/кон углам."""
        return cls(center, abs(radius), start_angle_rad, end_angle_rad, style_name, color)

    def __init__(self, center: Point, radius: float, start_angle_rad: float, end_angle_rad: float, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.radius = abs(radius)
        self.start_angle = self._normalize_angle(start_angle_rad)
        self.end_angle = self._normalize_angle(end_angle_rad)

    @property
    def sweep_angle(self):
        """Полный угол дуги (0..2π) против часовой стрелки."""
        delta = self.end_angle - self.start_angle
        if delta < 0:
            delta += 2 * math.pi
        if abs(delta) < 1e-9:
            return 2 * math.pi
        return delta

    def distance_to_point(self, mx, my):
        """Кратчайшее расстояние от точки до дуги."""
        dx = mx - self.center.x
        dy = my - self.center.y
        dist_to_center = math.sqrt(dx * dx + dy * dy)
        angle = math.atan2(dy, dx)

        # Если проекция лежит на дуге, расстояние до окружности
        if self._is_angle_between_ccw(angle, self.start_angle, self.end_angle):
            return abs(dist_to_center - self.radius)

        # Иначе расстояние до ближайшего конца дуги
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
    """Осьориентированный прямоугольник с опциональными фасками или скруглениями."""

    def __init__(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        style_name: str = 'solid_main',
        color: str = 'black',
        corner_type: str = 'none',  # none | chamfer | fillet
        corner_value: float = 0.0
    ):
        super().__init__(style_name=style_name, color=color)
        self.min_x = min(min_x, max_x)
        self.max_x = max(min_x, max_x)
        self.min_y = min(min_y, max_y)
        self.max_y = max(min_y, max_y)
        self.corner_type = corner_type
        self.corner_value = max(0.0, float(corner_value))

    # ---- КЛАСС-МЕТОДЫ СОЗДАНИЯ ----
    @classmethod
    def from_two_points(cls, p1: Point, p2: Point, **kwargs):
        """Строит прямоугольник по двум противоположным вершинам."""
        return cls(p1.x, p1.y, p2.x, p2.y, **kwargs)

    @classmethod
    def from_corner_size(cls, corner: Point, width: float, height: float, **kwargs):
        """Строит прямоугольник от заданной вершины по ширине и высоте."""
        dx = float(width)
        dy = float(height)
        return cls(corner.x, corner.y, corner.x + dx, corner.y + dy, **kwargs)

    @classmethod
    def from_center_size(cls, center: Point, width: float, height: float, **kwargs):
        """Строит прямоугольник по центру, ширине и высоте."""
        w2 = float(width) / 2.0
        h2 = float(height) / 2.0
        return cls(center.x - w2, center.y - h2, center.x + w2, center.y + h2, **kwargs)

    # ---- СВОЙСТВА ----
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
        """Возвращает вершины в порядке: BL, BR, TR, TL."""
        return [
            Point(self.min_x, self.min_y),
            Point(self.max_x, self.min_y),
            Point(self.max_x, self.max_y),
            Point(self.min_x, self.max_y),
        ]

    # ---- ГЕОМЕТРИЯ ДЛЯ ОТРИСОВКИ ----
    def _clamped_corner_value(self):
        return min(self.corner_value, self.width / 2.0, self.height / 2.0)

    def build_edges(self):
        """
        Генерирует список примитивов для отрисовки:
        - segments: прямые отрезки
        - arcs: дуги скруглений (если corner_type == fillet)
        """
        cv = self._clamped_corner_value()
        corners = self.corners()

        segments = []
        arcs = []

        if self.corner_type == 'none' or cv <= 0:
            # Обычный прямоугольник
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                segments.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
            return segments, arcs

        if self.corner_type == 'chamfer':
            # Раскладываем фаски. Используем фиксированные координаты по осям.
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

            # Стороны
            segments.extend([
                Segment(bottom_start, bottom_end, style_name=self.style_name, color=self.color),
                Segment(right_start, right_end, style_name=self.style_name, color=self.color),
                Segment(top_start, top_end, style_name=self.style_name, color=self.color),
                Segment(left_start, left_end, style_name=self.style_name, color=self.color),
                # Фаски
                Segment(bottom_end, right_start, style_name=self.style_name, color=self.color),
                Segment(right_end, top_start, style_name=self.style_name, color=self.color),
                Segment(top_end, left_start, style_name=self.style_name, color=self.color),
                Segment(left_end, bottom_start, style_name=self.style_name, color=self.color),
            ])
            return segments, arcs

        if self.corner_type == 'fillet':
            r = cv
            bl, br, tr, tl = corners
            # Прямые участки
            segments.extend([
                Segment(Point(bl.x + r, bl.y), Point(br.x - r, br.y), style_name=self.style_name, color=self.color),
                Segment(Point(br.x, br.y + r), Point(tr.x, tr.y - r), style_name=self.style_name, color=self.color),
                Segment(Point(tr.x - r, tr.y), Point(tl.x + r, tl.y), style_name=self.style_name, color=self.color),
                Segment(Point(tl.x, tl.y - r), Point(bl.x, bl.y + r), style_name=self.style_name, color=self.color),
            ])

            # Дуги по углам (CCW)
            arcs.extend([
                Arc.from_center_angles(Point(bl.x + r, bl.y + r), r, math.pi, 1.5 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(br.x - r, br.y + r), r, 1.5 * math.pi, 2 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(tr.x - r, tr.y - r), r, 0.0, 0.5 * math.pi, style_name=self.style_name, color=self.color),
                Arc.from_center_angles(Point(tl.x + r, tl.y - r), r, 0.5 * math.pi, math.pi, style_name=self.style_name, color=self.color),
            ])
            return segments, arcs

        # Фолбэк: обычный прямоугольник
        for i in range(4):
            p1 = corners[i]
            p2 = corners[(i + 1) % 4]
            segments.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
        return segments, arcs

    def distance_to_point(self, mx, my):
        """Кратчайшее расстояние от точки до прямоугольника (учитывая фаски/скругления)."""
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
    """Правильный многоугольник, задаваемый центром, радиусом и количеством сторон."""

    @classmethod
    def from_center_radius(cls, center: Point, radius: float, sides: int, variant: str = 'inscribed', start_angle: float = 0.0, style_name='solid_main', color='black'):
        """Создает многоугольник по центру, радиусу и числу сторон."""
        return cls(center, radius, sides, variant=variant, start_angle=start_angle, style_name=style_name, color=color)

    def __init__(self, center: Point, radius: float, sides: int, variant: str = 'inscribed', start_angle: float = 0.0, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.base_radius = abs(radius)
        self.sides = max(3, int(sides))
        self.variant = variant if variant in ('inscribed', 'circumscribed') else 'inscribed'
        self.start_angle = float(start_angle)

    def _circumradius(self):
        """Возвращает радиус описанной окружности для текущего варианта построения."""
        if self.variant == 'circumscribed':
            # Переданный радиус считается вписанным (окружность касается сторон).
            return self.base_radius / math.cos(math.pi / self.sides)
        return self.base_radius

    def vertices(self):
        """Список вершин в порядке обхода CCW."""
        r = self._circumradius()
        # Для описанного варианта немного смещаем фазу, чтобы сторона лежала горизонтально.
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
        """Возвращает список отрезков-сторон многоугольника."""
        verts = self.vertices()
        segs = []
        n = len(verts)
        for i in range(n):
            p1 = verts[i]
            p2 = verts[(i + 1) % n]
            segs.append(Segment(p1, p2, style_name=self.style_name, color=self.color))
        return segs

    def distance_to_point(self, mx, my):
        """Минимальное расстояние от точки до многоугольника (по его сторонам)."""
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
    """Обобщенный эллипс, заданный центром и концами полуосей."""

    @classmethod
    def from_center_axes(cls, center: Point, axis_point_a: Point, axis_point_b: Point, style_name='solid_main', color='black'):
        """Создает эллипс по центру и двум конечным точкам осей."""
        return cls(center, axis_point_a, axis_point_b, style_name, color)

    def __init__(self, center: Point, axis_point_a: Point, axis_point_b: Point, style_name='solid_main', color='black'):
        super().__init__(style_name=style_name, color=color)
        self.center = center
        self.axis_point_a = axis_point_a
        self.axis_point_b = axis_point_b

    def _basis(self):
        """Возвращает ортонормированный базис (e1, e2) и длины полуосей (a, b)."""
        v1x = self.axis_point_a.x - self.center.x
        v1y = self.axis_point_a.y - self.center.y
        v2x = self.axis_point_b.x - self.center.x
        v2y = self.axis_point_b.y - self.center.y

        a = math.sqrt(v1x * v1x + v1y * v1y)
        b_raw = math.sqrt(v2x * v2x + v2y * v2y)

        # Если оси вырожденные, подставляем минимальные значения, чтобы не падать
        if a < 1e-9:
            a = 1e-6
            v1x, v1y = 1.0, 0.0
        if b_raw < 1e-9:
            b_raw = 1e-6
            v2x, v2y = 0.0, 1.0

        e1x, e1y = v1x / a, v1y / a
        # Ортогонализуем второй вектор относительно первого
        proj = e1x * v2x + e1y * v2y
        ortho_x = v2x - proj * e1x
        ortho_y = v2y - proj * e1y
        ortho_len = math.sqrt(ortho_x * ortho_x + ortho_y * ortho_y)
        if ortho_len < 1e-9:
            # Если оси почти коллинеарны, берем перпендикуляр к первой оси
            ortho_x, ortho_y = -e1y, e1x
            ortho_len = 1.0
        e2x, e2y = ortho_x / ortho_len, ortho_y / ortho_len
        b = ortho_len
        return e1x, e1y, a, e2x, e2y, b

    def sample_points(self, num_points=180):
        """Возвращает список точек вдоль периметра эллипса."""
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
        """Оценка ограничивающего прямоугольника эллипса."""
        e1x, e1y, a, e2x, e2y, b = self._basis()
        dx = abs(e1x) * a + abs(e2x) * b
        dy = abs(e1y) * a + abs(e2y) * b
        return (
            self.center.x - dx,
            self.center.x + dx,
            self.center.y - dy,
            self.center.y + dy,
        )

    def perimeter_approx(self):
        """Аппроксимация периметра (формула Рамануджана)."""
        _, _, a, _, _, b = self._basis()
        h = ((a - b) ** 2) / ((a + b) ** 2 + 1e-12)
        return math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))

    def distance_to_point(self, mx, my):
        """Оценка расстояния от точки до границы эллипса."""
        e1x, e1y, a, e2x, e2y, b = self._basis()
        rx = mx - self.center.x
        ry = my - self.center.y

        local_x = rx * e1x + ry * e1y
        local_y = rx * e2x + ry * e2y

        # Нормированная величина: (x/a)^2 + (y/b)^2
        q = (local_x / a) ** 2 + (local_y / b) ** 2

        if q < 1e-12:
            # Точка в центре
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