# ui/renderer.py
import math

class Renderer:
    def __init__(self, canvas, state, converter):
        self.canvas = canvas
        self.state = state
        self.converter = converter

    def clear(self):
        self.canvas.delete("all")

    def draw_grid_and_axes(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 2 or h < 2: return
        
        # Получаем границы видимой области в мировых координатах
        world_tl_x, world_tl_y = self.converter.screen_to_world(0, 0)
        world_br_x, world_br_y = self.converter.screen_to_world(w, h)
        
        # Рисуем вертикальные линии
        start_x = math.ceil(world_tl_x / self.state.grid_step) * self.state.grid_step
        # range не работает с float, используем while или адаптацию
        wx = start_x
        while wx < world_br_x:
            sx, _ = self.converter.world_to_screen(wx, 0)
            color = 'black' if abs(wx) < 1e-9 else self.state.grid_color
            width = 2 if abs(wx) < 1e-9 else 1
            self.canvas.create_line(sx, 0, sx, h, fill=color, width=width)
            wx += self.state.grid_step
            
        # Рисуем горизонтальные линии
        start_y = math.ceil(world_br_y / self.state.grid_step) * self.state.grid_step
        wy = start_y
        while wy < world_tl_y:
            _, sy = self.converter.world_to_screen(0, wy)
            color = 'black' if abs(wy) < 1e-9 else self.state.grid_color
            width = 2 if abs(wy) < 1e-9 else 1
            self.canvas.create_line(0, sy, w, sy, fill=color, width=width)
            wy += self.state.grid_step
        
        # Подписи осей
        sx, sy = self.converter.world_to_screen(0,0)
        if 0 < sx < w: self.canvas.create_text(sx + 10, 10, text="Y", font=("Arial", 10), anchor='nw', fill='gray')
        if 0 < sy < h: self.canvas.create_text(w - 10, sy - 10, text="X", font=("Arial", 10), anchor='se', fill='gray')

    def draw_segment(self, segment, width=4, color=None):
        draw_color = color if color else segment.color
        sx1, sy1 = self.converter.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.converter.world_to_screen(segment.p2.x, segment.p2.y)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=draw_color, width=width)

    def draw_point(self, point, size=4, color='black'):
        x, y = self.converter.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def render_scene(self):
        self.clear()
        self.draw_grid_and_axes()
        
        # Рисуем готовые сегменты
        for segment in self.state.segments:
            self.draw_segment(segment)
            
        # Рисуем превью (если есть)
        if self.state.preview_segment:
            self.draw_segment(self.state.preview_segment, width=2, color='blue')
            
        # Рисуем активные точки (маркеры редактирования)
        if self.state.active_p1: self.draw_point(self.state.active_p1)
        if self.state.active_p2: self.draw_point(self.state.active_p2)