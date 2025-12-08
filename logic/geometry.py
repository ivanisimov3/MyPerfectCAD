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