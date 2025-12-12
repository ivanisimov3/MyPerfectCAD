# logic/geometry.py

'''
Этот файл отвечает за геометрию: вычисление длины, углов, перевод из полярных координат в декартовы и обратно. 
Он ничего не знает о том, как это рисуется на экране, он работает только с числами.
'''

import math

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

class Segment:
    # Инициализация отрезка по умолчанию
    def __init__(self, p1: Point, p2: Point, style_name = 'solid_main', color='black', kinks_count=None, waves_count=None):
        self.p1 = p1
        self.p2 = p2
        # Храним только ID стиля (ссылку), а не параметры.
        # Это позволяет менять стиль централизованно в Менеджере.
        self.style_name = style_name
        self.color = color
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


class Circle:
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
        self.center = center
        self.radius = abs(radius)  # Радиус всегда положительный
        self.style_name = style_name
        self.color = color

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


class Arc:
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
        self.center = center
        self.radius = abs(radius)
        self.start_angle = self._normalize_angle(start_angle_rad)
        self.end_angle = self._normalize_angle(end_angle_rad)
        self.style_name = style_name
        self.color = color

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