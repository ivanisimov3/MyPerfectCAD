# ui/renderer.py

'''
Этот класс умеет брать данные из state (точки, линии) и физически рисовать их на tkinter.Canvas. 
Он рисует сетку, оси координат и сами отрезки. 
Он знает, как нарисовать линию определенного цвета и толщины, но не решает когда это делать.
'''

import math
import tkinter as tk

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

        # Определяем видимую область, чтобы не рисовать лишнего
        # Берем 4 угла экрана и переводим их в мир
        corners = [
            self.converter.screen_to_world(0, 0),
            self.converter.screen_to_world(w, 0),
            self.converter.screen_to_world(w, h),
            self.converter.screen_to_world(0, h)
        ]
        
        # Находим min/max координаты, которые сейчас видны
        min_wx = min(p[0] for p in corners)
        max_wx = max(p[0] for p in corners)
        min_wy = min(p[1] for p in corners)
        max_wy = max(p[1] for p in corners)

        step = self.state.grid_step
        
        # "Бесконечные" границы для линий (чтобы при повороте они не обрывались на экране)
        # Берем с запасом, превышающим размер экрана
        infinity = max(max_wx - min_wx, max_wy - min_wy) * 2 + 1000

        # 1. Вертикальные линии (шагаем по X)
        start_x = math.floor(min_wx / step) * step
        curr_x = start_x
        while curr_x <= max_wx:
            # Линия идет от (x, -inf) до (x, +inf)
            p1 = self.converter.world_to_screen(curr_x, -infinity)
            p2 = self.converter.world_to_screen(curr_x, infinity)
            
            color = 'black' if abs(curr_x) < 1e-9 else self.state.grid_color
            width = 2 if abs(curr_x) < 1e-9 else 1
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=width)
            curr_x += step

        # 2. Горизонтальные линии (шагаем по Y)
        start_y = math.floor(min_wy / step) * step
        curr_y = start_y
        while curr_y <= max_wy:
            # Линия идет от (-inf, y) до (+inf, y)
            p1 = self.converter.world_to_screen(-infinity, curr_y)
            p2 = self.converter.world_to_screen(infinity, curr_y)
            
            color = 'black' if abs(curr_y) < 1e-9 else self.state.grid_color
            width = 2 if abs(curr_y) < 1e-9 else 1
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=width)
            curr_y += step
            
        # Подписи осей (X и Y)
        x_pos = self.converter.world_to_screen(step * 3, 0)
        y_pos = self.converter.world_to_screen(0, step * 3)
        
        font_style = ("Arial", 10, "bold")
        
        # Определяем размер видимой области в мире, чтобы знать, сколько отступить от края
        world_width = max_wx - min_wx
        world_height = max_wy - min_wy
        
        # Отступ от края экрана (5% от ширины/высоты видимой области)
        pad_x = world_width * 0.05
        pad_y = world_height * 0.05

        # --- РИСУЕМ X ---
        # Ось X (линия y=0) видна, если видимый диапазон Y включает 0
        if min_wy < 0 < max_wy:
            if max_wx > 0:
                lbl_x_pos = max_wx - pad_x
                
                lbl_x_pos = max(lbl_x_pos, step * 2)
                
                sx, sy = self.converter.world_to_screen(lbl_x_pos, 0)
                
                self.canvas.create_text(sx, sy + 5, text="X", font=font_style, 
                                      fill="red", anchor="nw")

        # --- РИСУЕМ Y ---
        # Ось Y (линия x=0) видна, если видимый диапазон X включает 0
        if min_wx < 0 < max_wx:
            if max_wy > 0:
                lbl_y_pos = max_wy - pad_y
                lbl_y_pos = max(lbl_y_pos, step * 2)
                
                sx, sy = self.converter.world_to_screen(0, lbl_y_pos)
                
                self.canvas.create_text(sx + 5, sy, text="Y", font=font_style, 
                                      fill="green", anchor="nw")

    def draw_segment(self, segment, override_color=None, override_width=None):
        # 1. Определяем цвет
        draw_color = override_color if override_color else segment.color
        
        # 2. Ищем стиль в state
        style = self.state.line_styles.get(segment.style_name)
        
        # 3. Вычисляем толщину и пунктир
        if style:
            # Если стиль найден, считаем толщину по ГОСТ
            if style.is_main:
                line_width = self.state.base_thickness_s
            else:
                # Тонкая линия = s / 2 (округляем до целого, т.к. пиксели)
                line_width = max(1, int(self.state.base_thickness_s / 2))
            
            dash_pattern = style.dash_pattern
        else:
            # Фолбэк (если вдруг стиль удалили или имя кривое)
            line_width = 1
            dash_pattern = None

        # Разрешаем принудительно менять толщину (например, для подсветки выделения в будущем)
        if override_width:
            line_width = override_width

        # 4. Перевод координат
        sx1, sy1 = self.converter.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.converter.world_to_screen(segment.p2.x, segment.p2.y)
        
        # 5. Рисуем с учетом dash
        # Параметр dash в Tkinter требует кортежа (5, 2) или None
        self.canvas.create_line(
            sx1, sy1, sx2, sy2, 
            fill=draw_color, 
            width=line_width, 
            dash=dash_pattern,
            capstyle=tk.ROUND # Скругляем концы линий для красоты
        )

    def draw_point(self, point, size=4, color='black'):
        x, y = self.converter.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def render_scene(self):
        self.clear()
        self.draw_grid_and_axes()
        
        # 1. РИСУЕМ ПОДСВЕТКУ ВЫДЕЛЕНИЯ
        # Рисуем её ПОД основными линиями, широкой и полупрозрачной
        for seg in self.state.selected_segments:
            # Рисуем копию линии, но очень толстую и цвета выделения
            self.draw_segment(seg, override_color='#00FFFF', override_width=10) # 10px толщина подсветки

        # Рисуем готовые сегменты
        for segment in self.state.segments:
            self.draw_segment(segment)
            
        # Рисуем превью (если есть)
        if self.state.preview_segment:
            self.draw_segment(self.state.preview_segment, override_color='blue')
            
        # Рисуем активные точки (маркеры редактирования)
        if self.state.active_p1: self.draw_point(self.state.active_p1)
        if self.state.active_p2: self.draw_point(self.state.active_p2)