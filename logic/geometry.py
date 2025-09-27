# Мозг нашего приложения. Вся математика, не связанная с отображением, будет здесь. 
# Это соответствует принципу разделения логики и представления.

# logic/geometry.py

import math

class Point:
    def __init__(self, x=0.0, y=0.0):
        """
        Конструктор точки. По умолчанию создается в начале координат (0,0).
        Хранит координаты всегда в декартовой системе.
        """
        self.x = float(x)
        self.y = float(y)

    def set_from_polar(self, r, theta_rad):
        """
        Устанавливает декартовы координаты точки, принимая на вход полярные.
        r: расстояние от начала координат (радиус).
        theta_rad: угол в радианах.
        """
        self.x = r * math.cos(theta_rad)
        self.y = r * math.sin(theta_rad)

    def get_polar_coords(self):
        """
        Возвращает полярные координаты точки, вычисленные из декартовых.
        Возвращает кортеж (r, theta_rad).
        """
        r = math.sqrt(self.x**2 + self.y**2)
        # atan2 - более "умный" арктангенс, который правильно определяет четверть
        theta_rad = math.atan2(self.y, self.x)
        return r, theta_rad

    def __repr__(self):
        """
        Строковое представление объекта. Полезно для отладки.
        Вызывается, когда мы делаем print(my_point_object).
        """
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"

# Класс для отрезка пока будет простым хранилищем двух точек.
# В будущем мы добавим сюда вычисление длины, угла и т.д.
class Segment:
    def __init__(self, p1: Point, p2: Point):
        """
        Конструктор отрезка. Принимает два объекта класса Point.
        """
        self.p1 = p1
        self.p2 = p2
        
    #Этот декоратор превращает метод в "умное" свойство. 
    # Мы можем обращаться к my_segment.length как к обычной переменной, а код внутри метода будет выполняться каждый раз при обращении.
    @property 
    def length(self):
        """Вычисляет и возвращает длину отрезка."""
        return math.sqrt((self.p2.x - self.p1.x)**2 + (self.p2.y - self.p1.y)**2)

    @property
    def angle(self):
        """Вычисляет и возвращает угол наклона отрезка в радианах."""
        return math.atan2(self.p2.y - self.p1.y, self.p2.x - self.p1.x)

    def __repr__(self):
        return f"Segment({self.p1}, {self.p2})"