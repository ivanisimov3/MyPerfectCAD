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

        corners = [
            self.converter.screen_to_world(0, 0),
            self.converter.screen_to_world(w, 0),
            self.converter.screen_to_world(w, h),
            self.converter.screen_to_world(0, h)
        ]
        
        min_wx = min(p[0] for p in corners); max_wx = max(p[0] for p in corners)
        min_wy = min(p[1] for p in corners); max_wy = max(p[1] for p in corners)

        step = self.state.grid_step
        infinity = max(max_wx - min_wx, max_wy - min_wy) * 2 + 1000

        # Вертикальные
        start_x = math.floor(min_wx / step) * step
        curr_x = start_x
        while curr_x <= max_wx:
            p1 = self.converter.world_to_screen(curr_x, -infinity)
            p2 = self.converter.world_to_screen(curr_x, infinity)
            color = 'black' if abs(curr_x) < 1e-9 else self.state.grid_color
            width = 2 if abs(curr_x) < 1e-9 else 1
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=width)
            curr_x += step

        # Горизонтальные
        start_y = math.floor(min_wy / step) * step
        curr_y = start_y
        while curr_y <= max_wy:
            p1 = self.converter.world_to_screen(-infinity, curr_y)
            p2 = self.converter.world_to_screen(infinity, curr_y)
            color = 'black' if abs(curr_y) < 1e-9 else self.state.grid_color
            width = 2 if abs(curr_y) < 1e-9 else 1
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=color, width=width)
            curr_y += step
            
        # Оси
        x_pos = self.converter.world_to_screen(step * 3, 0)
        y_pos = self.converter.world_to_screen(0, step * 3)
        font_style = ("Arial", 10, "bold")
        world_width = max_wx - min_wx
        world_height = max_wy - min_wy
        pad_x = world_width * 0.05
        pad_y = world_height * 0.05

        if min_wy < 0 < max_wy:
            if max_wx > 0:
                lbl_x_pos = max_wx - pad_x
                lbl_x_pos = max(lbl_x_pos, step * 2)
                sx, sy = self.converter.world_to_screen(lbl_x_pos, 0)
                self.canvas.create_text(sx, sy + 5, text="X", font=font_style, fill="red", anchor="nw")

        if min_wx < 0 < max_wx:
            if max_wy > 0:
                lbl_y_pos = max_wy - pad_y
                lbl_y_pos = max(lbl_y_pos, step * 2)
                sx, sy = self.converter.world_to_screen(0, lbl_y_pos)
                self.canvas.create_text(sx + 5, sy, text="Y", font=font_style, fill="green", anchor="nw")

    # Генератор для ПУНКТИРНЫХ линий
    def _generate_dashed_coords(self, x1, y1, x2, y2, pattern):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return []
        
        ux, uy = dx/length, dy/length
        
        # Масштабируем паттерн по зуму
        zoom = self.state.zoom
        scaled_pattern = [float(val) * zoom for val in pattern]
        
        lines = []
        current_dist = 0
        pat_idx = 0
        
        while current_dist < length:
            segment_len = scaled_pattern[pat_idx % len(scaled_pattern)]
            
            # Логика: Четные индексы (0, 2, 4...) - РИСУЕМ
            # Нечетные индексы (1, 3, 5...) - ПРОПУСКАЕМ (пробел)
            is_draw = (pat_idx % 2 == 0)
            
            draw_len = min(segment_len, length - current_dist)
            
            if is_draw:
                px_start = x1 + ux * current_dist
                py_start = y1 + uy * current_dist
                px_end = x1 + ux * (current_dist + draw_len)
                py_end = y1 + uy * (current_dist + draw_len)
                lines.append((px_start, py_start, px_end, py_end))
            
            current_dist += segment_len
            pat_idx += 1
            
        return lines

    def _generate_wave_coords(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = []
        zoom = self.state.zoom
        step = 5 * (zoom / 5.0)
        amplitude = 3 * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0)
        if step < 0.1: step = 0.1
        
        t = 0
        while t < length:
            offset = amplitude * math.sin(t * freq)
            bx = x1 + ux * t
            by = y1 + uy * t
            px = bx + nx * offset
            py = by + ny * offset
            points.extend([px, py])
            t += step
            
        points.extend([x2, y2])
        return points

    def _generate_zigzag_coords(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = [x1, y1]
        zoom = self.state.zoom
        period = 40 * (zoom / 5.0)
        kink_len = 12 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)
        
        current_dist = 0
        while current_dist < length:
            dist_to_next_kink = min(length, current_dist + period)
            bx = x1 + ux * dist_to_next_kink
            by = y1 + uy * dist_to_next_kink
            points.extend([bx, by])
            current_dist = dist_to_next_kink
            
            if current_dist + kink_len <= length:
                d1 = current_dist + kink_len * 0.25
                px1 = x1 + ux * d1 - nx * amplitude
                py1 = y1 + uy * d1 - ny * amplitude
                d2 = current_dist + kink_len * 0.75
                px2 = x1 + ux * d2 + nx * amplitude
                py2 = y1 + uy * d2 + ny * amplitude
                d3 = current_dist + kink_len
                px3 = x1 + ux * d3
                py3 = y1 + uy * d3
                points.extend([px1, py1, px2, py2, px3, py3])
                current_dist += kink_len
            else:
                points.extend([x2, y2])
                break
        return points

    def draw_segment(self, segment, override_color=None, override_width=None):
        draw_color = override_color if override_color else segment.color
        style = self.state.line_styles.get(segment.style_name)
        
        line_width = 1
        dash_pattern = None
        is_complex_geo = False
        
        if style:
            if style.is_main:
                line_width = self.state.base_thickness_s
            else:
                line_width = max(1, int(self.state.base_thickness_s / 2))
            
            # --- ЛОГИКА РАСШИФРОВКИ ПАТТЕРНА ---
            if style.dash_pattern:
                main_dash = style.dash_pattern[0]
                main_gap = style.dash_pattern[1]
                
                # 1. Штрих-пунктир (2 точки) - ПРОВЕРЯЕМ ПЕРВЫМ!
                if style.name == 'dash_dot_dot':
                    part = main_gap / 5.0
                    # Dash, Space, Dot, Space, Dot, Space
                    dash_pattern = [main_dash, part, part, part, part, part]

                # 2. Штрих-пунктир (1 точка) - остальные, начинающиеся на dash_dot_
                elif style.name.startswith('dash_dot_'):
                    part = main_gap / 3.0
                    # Dash, Space, Dot, Space
                    dash_pattern = [main_dash, part, part, part]
                
                # 3. Обычная штриховая
                elif style.name == 'dashed':
                    dash_pattern = [main_dash, main_gap]
            
            if style.name in ['solid_wave', 'solid_zigzag']:
                is_complex_geo = True

        if override_width:
            line_width = override_width
            dash_pattern = None
            is_complex_geo = False

        sx1, sy1 = self.converter.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.converter.world_to_screen(segment.p2.x, segment.p2.y)

        # 1. ВОЛНЫ/ЗИГЗАГИ
        if is_complex_geo:
            coords = []
            smooth_flag = False
            if style.name == 'solid_wave':
                coords = self._generate_wave_coords(sx1, sy1, sx2, sy2)
                smooth_flag = True
            elif style.name == 'solid_zigzag':
                coords = self._generate_zigzag_coords(sx1, sy1, sx2, sy2)
                smooth_flag = False
            
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill=draw_color, width=line_width, capstyle=tk.ROUND, smooth=smooth_flag)
                return 

        # 2. ПУНКТИРЫ (Умная генерация)
        if dash_pattern:
            segments_list = self._generate_dashed_coords(sx1, sy1, sx2, sy2, dash_pattern)
            for seg in segments_list:
                self.canvas.create_line(seg[0], seg[1], seg[2], seg[3], 
                                      fill=draw_color, width=line_width, capstyle=tk.ROUND)
        
        # 3. СПЛОШНАЯ
        else:
            self.canvas.create_line(sx1, sy1, sx2, sy2, 
                                  fill=draw_color, width=line_width, capstyle=tk.ROUND)

    def draw_point(self, point, size=4, color='black'):
        x, y = self.converter.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def render_scene(self):
        self.clear()
        self.draw_grid_and_axes()
        for seg in self.state.selected_segments:
            self.draw_segment(seg, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_s + 6))
        for segment in self.state.segments:
            self.draw_segment(segment)
        if self.state.preview_segment:
            self.draw_segment(self.state.preview_segment, override_color='blue')
        if self.state.active_p1: self.draw_point(self.state.active_p1)
        if self.state.active_p2: self.draw_point(self.state.active_p2)