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

    def _generate_wave_coords(self, x1, y1, x2, y2):
        # Вектор линии
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        # Нормализуем вектор направления
        ux, uy = dx/length, dy/length
        # Нормаль (перпендикуляр) к вектору (-uy, ux)
        nx, ny = -uy, ux
        
        points = []
        step = 5  # Шаг в пикселях
        amplitude = 3 # Высота волны в пикселях
        freq = 0.2    # Частота волны
        
        # Генерируем точки вдоль линии
        for t in range(0, int(length), step):
            # Смещение по синусоиде перпендикулярно линии
            offset = amplitude * math.sin(t * freq)
            
            # Координата на прямой
            bx = x1 + ux * t
            by = y1 + uy * t
            
            # Добавляем смещение
            px = bx + nx * offset
            py = by + ny * offset
            points.extend([px, py])
            
        points.extend([x2, y2]) # Обязательно добавляем конец
        return points

    def _generate_zigzag_coords(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        # Единичные векторы направления (ux, uy) и нормали (nx, ny)
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = [x1, y1]
        
        # Настройки "пульса"
        period = 40       # Длина прямого участка между изломами
        kink_len = 12     # Длина самого излома вдоль линии
        amplitude = 5     # Высота излома
        
        current_dist = 0
        
        while current_dist < length:
            # 1. Рисуем прямой участок до начала следующего излома
            # Оставляем место под излом, но если это конец линии - идем до конца
            dist_to_next_kink = min(length, current_dist + period)
            
            bx = x1 + ux * dist_to_next_kink
            by = y1 + uy * dist_to_next_kink
            points.extend([bx, by])
            
            current_dist = dist_to_next_kink
            
            # 2. Если осталось место для излома, рисуем "пульс"
            if current_dist + kink_len <= length:
                # Точка 1: Вверх (на 1/4 длины излома)
                d1 = current_dist + kink_len * 0.25
                px1 = x1 + ux * d1 - nx * amplitude
                py1 = y1 + uy * d1 - ny * amplitude
                
                # Точка 2: Вниз (на 3/4 длины излома)
                d2 = current_dist + kink_len * 0.75
                px2 = x1 + ux * d2 + nx * amplitude
                py2 = y1 + uy * d2 + ny * amplitude
                
                # Точка 3: Возврат на ось (конец излома)
                d3 = current_dist + kink_len
                px3 = x1 + ux * d3
                py3 = y1 + uy * d3
                
                points.extend([px1, py1, px2, py2, px3, py3])
                current_dist += kink_len
            else:
                # Если места на полный излом нет, просто дорисовываем прямую до конца
                points.extend([x2, y2])
                break
                
        return points

    def draw_segment(self, segment, override_color=None, override_width=None):
        # 1. Определяем цвет
        draw_color = override_color if override_color else segment.color
        
        # 2. Ищем стиль в state
        style = self.state.line_styles.get(segment.style_name)

        line_width = 1
        dash_pattern = None
        is_complex = False # Флаг: сложная геометрия?
        
        # 3. Вычисляем толщину и пунктир
        if style:
            # Если стиль найден, считаем толщину по ГОСТ
            if style.is_main:
                line_width = self.state.base_thickness_s
            else:
                # Тонкая линия = s / 2 (округляем до целого, т.к. пиксели)
                line_width = max(1, int(self.state.base_thickness_s / 2))
            
            dash_pattern = style.dash_pattern

            # Проверяем на спец. стили
            if style.name in ['solid_wave', 'solid_zigzag']:
                is_complex = True

        if override_width:
            line_width = override_width

        # Экранные координаты начала и конца
        sx1, sy1 = self.converter.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.converter.world_to_screen(segment.p2.x, segment.p2.y)

        if is_complex and not dash_pattern:
            # Генерация сложной геометрии
            coords = []
            smooth_flag = False
            
            if style.name == 'solid_wave':
                coords = self._generate_wave_coords(sx1, sy1, sx2, sy2)
                smooth_flag = True # Tkinter умеет сглаживать ломаные в кривые (B-spline)
            elif style.name == 'solid_zigzag':
                coords = self._generate_zigzag_coords(sx1, sy1, sx2, sy2)
                smooth_flag = False
            
            # Рисуем полилинию (много точек)
            # *coords распаковывает список в аргументы (x1, y1, x2, y2...)
            if len(coords) >= 4:
                self.canvas.create_line(
                    *coords,
                    fill=draw_color,
                    width=line_width,
                    capstyle=tk.ROUND,
                    smooth=smooth_flag 
                )
        else:
            # Обычная прямая (сплошная или штриховая)
            self.canvas.create_line(
                sx1, sy1, sx2, sy2, 
                fill=draw_color, 
                width=line_width, 
                dash=dash_pattern,
                capstyle=tk.ROUND
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