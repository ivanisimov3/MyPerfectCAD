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

    # Перевод из декартовых в полярные координаты
    def get_polar_coords(self):
        r = math.sqrt(self.x**2 + self.y**2)
        theta_rad = math.atan2(self.y, self.x)
        return r, theta_rad

    # Перевод из полярных в декартовы координаты
    def set_from_polar(self, r, theta_rad):
        self.x = r * math.cos(theta_rad)
        self.y = r * math.sin(theta_rad)

    def __repr__(self):
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"

class Segment:
    # Инициализация отрезка по умолчанию
    def __init__(self, p1: Point, p2: Point, style_name = 'solid_main', color='black'):
        self.p1 = p1
        self.p2 = p2
        self.style_name = style_name # Ссылка на ключ в словаре стилей
        self.color = color

    # @property - декоратор для обращения к методу объекта без ()
    
    # Метод вычисляет и возвращает длину отрезка
    @property
    def length(self):
        return math.sqrt((self.p2.x - self.p1.x)**2 + (self.p2.y - self.p1.y)**2)

    # Метод вычисляет и возвращает угол наклона отрезка в радианах
    @property
    def angle(self):
        return math.atan2(self.p2.y - self.p1.y, self.p2.x - self.p1.x)
    
    def __repr__(self):
        return f"Segment({self.p1}, {self.p2}, style='{self.style_name}')"