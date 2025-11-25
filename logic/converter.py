# logic/converter.py

'''
Мост между бесконечным миром и экраном монитора.
Он содержит математику преобразования координат.
world_to_screen: 
    Превращает математические координаты (например, x=50, y=50) в пиксели на экране с учетом зума, сдвига и поворота.
screen_to_world: 
    Наоборот, переводит клик мыши в пикселях в реальные координаты чертежа.
'''

import math

class CoordinateConverter:
    def __init__(self, state, canvas):
        self.state = state
        self.canvas = canvas

    # Из мировых (World) в экранные (Screen)
    def world_to_screen(self, world_x, world_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        
        # 1. Поворот (Rotation)
        # Формула поворота точки (wx, wy) вокруг (0,0)
        angle = self.state.rotation
        rx = world_x * math.cos(angle) - world_y * math.sin(angle)
        ry = world_x * math.sin(angle) + world_y * math.cos(angle)
        
        # 2. Масштабирование (Scale) и перевод в экранные (инверсия Y)
        screen_x = cx + self.state.pan_x + (rx * self.state.zoom)
        screen_y = cy + self.state.pan_y - (ry * self.state.zoom)
        
        return screen_x, screen_y

    # Из экранных (Screen) в мировые (World) - ОБРАТНОЕ ПРЕОБРАЗОВАНИЕ
    def screen_to_world(self, screen_x, screen_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        
        # 1. Убираем сдвиг и масштаб (обратный порядок)
        # (screen_x - cx - pan) / zoom
        unscaled_x = (screen_x - cx - self.state.pan_x) / self.state.zoom
        unscaled_y = -(screen_y - cy - self.state.pan_y) / self.state.zoom # минус из-за инверсии Y
        
        # 2. Обратный поворот (Rotate back)
        # Чтобы повернуть обратно, используем тот же угол со знаком минус
        # cos(-a) = cos(a), sin(-a) = -sin(a)
        angle = -self.state.rotation
        world_x = unscaled_x * math.cos(angle) - unscaled_y * math.sin(angle)
        world_y = unscaled_x * math.sin(angle) + unscaled_y * math.cos(angle)
        
        return world_x, world_y