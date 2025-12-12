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