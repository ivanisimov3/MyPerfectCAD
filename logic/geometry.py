# Мозг нашего приложения. Вся математика, не связанная с отображением, будет здесь. 
# Это соответствует принципу разделения логики и представления.

# logic/geometry.py

import math

class Point:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def set_from_polar(self, r, theta_rad):
        self.x = r * math.cos(theta_rad)
        self.y = r * math.sin(theta_rad)

    def get_polar_coords(self):
        r = math.sqrt(self.x**2 + self.y**2)
        theta_rad = math.atan2(self.y, self.x)
        return r, theta_rad

    def __repr__(self):
        return f"Point(x={self.x:.2f}, y={self.y:.2f})"

class Segment:
    def __init__(self, p1: Point, p2: Point):
        self.p1 = p1
        self.p2 = p2

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