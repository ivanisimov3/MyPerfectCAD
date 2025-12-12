# ui/renderer.py

'''
Отвечает за низкоуровневую отрисовку графики.
Реализует паттерн "Отрисовщик": отделяет логику хранения данных от логики их отображения.
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

    # Генератор для пунктирных линий
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

    def _generate_wave_coords(self, x1, y1, x2, y2, fixed_count=None):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = []
        zoom = self.state.zoom
        
        # Базовые параметры (если авто)
        step = 5 * (zoom / 5.0)
        amplitude = 3 * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0) # Частота по умолчанию
        
        # Если задано конкретное число волн
        if fixed_count is not None and fixed_count > 0:
            # Чтобы уместить ровно N волн в длину L:
            # Период синуса T = Length / N
            # Частота в формуле sin(t * freq) -> freq = 2*pi / T
            # freq = 2*pi * N / Length
            freq = (2 * math.pi * fixed_count) / length
        
        if step < 0.1: step = 0.1
        
        t = 0
        while t < length:
            offset = amplitude * math.sin(t * freq)
            px = x1 + ux * t + nx * offset
            py = y1 + uy * t + ny * offset
            points.extend([px, py])
            t += step
            
        points.extend([x2, y2])
        return points

    def _generate_zigzag_coords(self, x1, y1, x2, y2, fixed_count=None):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        points = [x1, y1]
        
        zoom = self.state.zoom
        # Базовые параметры (если fixed_count не задан)
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)
        
        # ЛОГИКА ФИКСИРОВАННОГО КОЛИЧЕСТВА
        if fixed_count is not None and fixed_count > 0:
            # Считаем суммарную длину всех изломов
            total_kinks_len = fixed_count * kink_len
            
            # Если изломы влезают в длину линии
            if total_kinks_len < length:
                # Оставшееся место делим поровну на промежутки
                # Промежутков всегда N + 1 (начало...излом...конец)
                gap = (length - total_kinks_len) / (fixed_count + 1)
                
                current_dist = 0
                for _ in range(fixed_count):
                    # 1. Прямой участок (Gap)
                    current_dist += gap
                    bx = x1 + ux * current_dist
                    by = y1 + uy * current_dist
                    points.extend([bx, by])
                    
                    # 2. Рисуем излом
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
                
                # Дорисовываем конец
                points.extend([x2, y2])
                return points
            
            # Если не влезают - рисуем как обычный (фолбэк)
        
        # СТАНДАРТНАЯ ЛОГИКА (АВТОМАТИЧЕСКАЯ)
        current_dist = 0
        while current_dist < length:
            dist_to_next_kink = min(length, current_dist + period)
            bx = x1 + ux * dist_to_next_kink
            by = y1 + uy * dist_to_next_kink
            points.extend([bx, by])
            current_dist = dist_to_next_kink
            
            if current_dist + kink_len <= length:
                d1 = current_dist + kink_len * 0.25; px1 = x1 + ux * d1 - nx * amplitude; py1 = y1 + uy * d1 - ny * amplitude
                d2 = current_dist + kink_len * 0.75; px2 = x1 + ux * d2 + nx * amplitude; py2 = y1 + uy * d2 + ny * amplitude
                d3 = current_dist + kink_len; px3 = x1 + ux * d3; py3 = y1 + uy * d3
                points.extend([px1, py1, px2, py2, px3, py3])
                current_dist += kink_len
            else:
                points.extend([x2, y2])
                break
        return points

    def draw_circle(self, circle, override_color=None, override_width=None):
        # Отрисовывает окружность на холсте
        # override_color, override_width - используются для выделения или других спецэффектов

        # Выбираем цвет (переопределенный или из окружности)
        draw_color = override_color if override_color else circle.color

        # Получаем стиль линии из state
        style = self.state.line_styles.get(circle.style_name)

        # Дефолтные значения
        line_width = 1

        # Если стиль найден, обработаем его свойства
        if style:
            # Вычисляем толщину линии на основе базовой толщины
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio

            # Основная линия толще, тонкая - в 2 раза тоньше
            if style.is_main:
                line_width = max(1, int(s_px))
            else:
                line_width = max(1, int(s_px / 2))

        if override_width:
            line_width = override_width

        # Конвертируем мировые координаты в экранные
        cx, cy = self.converter.world_to_screen(circle.center.x, circle.center.y)
        radius_px = circle.radius * self.state.zoom

        # Проверяем тип стиля
        base_type = 'solid'
        dash_pattern = None
        is_complex_style = False

        if style:
            base_type = getattr(style, 'base_type', 'solid')
            is_complex_style = base_type in ['wave', 'zigzag']

            # Обработка штриховых стилей
            if style.dash_pattern:
                main_dash = style.dash_pattern[0]
                main_gap = style.dash_pattern[1]

                # Определяем тип штриховки
                if base_type == 'dash_dot_dot':
                    # Штрих-пунктир-пунктир (две точки)
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base_type == 'dash_dot':
                    # Штрих-пунктир (одна точка)
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    # Просто штриховая
                    dash_pattern = [main_dash, main_gap]

        if dash_pattern:
            # Для штриховых стилей
            self._draw_dashed_circle(circle, cx, cy, radius_px, draw_color, line_width, dash_pattern)
        elif base_type in ['wave', 'zigzag']:
            # Для сложных стилей создаем эффект через серию дуг или линий
            self._draw_styled_circle(circle, cx, cy, radius_px, draw_color, line_width, base_type)
        else:
            # Обычная окружность
            x1 = cx - radius_px
            y1 = cy - radius_px
            x2 = cx + radius_px
            y2 = cy + radius_px
            self.canvas.create_oval(x1, y1, x2, y2, outline=draw_color, width=line_width, fill='')

    def _draw_dashed_circle(self, circle, cx, cy, radius_px, draw_color, line_width, dash_pattern):
        """Отрисовка штриховой окружности"""
        # Вычисляем общую длину окружности
        circumference = 2 * math.pi * radius_px

        # Масштабируем паттерн под длину окружности
        zoom = self.state.zoom
        scaled_pattern = [float(val) * zoom for val in dash_pattern]

        # Создаем точки окружности с учетом штриховки
        current_angle = 0
        pat_idx = 0
        is_drawing = True  # Начинаем с рисования

        while current_angle < 2 * math.pi:
            # Длина текущего сегмента паттерна
            segment_length = scaled_pattern[pat_idx % len(scaled_pattern)]
            segment_angle = segment_length / radius_px  # Угол соответствующего сегменту

            # Ограничиваем угол оставшейся частью окружности
            actual_angle = min(segment_angle, 2 * math.pi - current_angle)

            if is_drawing and actual_angle > 0.01:  # Минимальный угол для отрисовки
                # Рисуем дугу
                start_angle = math.degrees(current_angle)
                extent = math.degrees(actual_angle)

                x1 = cx - radius_px
                y1 = cy - radius_px
                x2 = cx + radius_px
                y2 = cy + radius_px

                self.canvas.create_arc(x1, y1, x2, y2,
                                     start=start_angle, extent=extent,
                                     outline=draw_color, width=line_width,
                                     style=tk.ARC)

            current_angle += actual_angle
            pat_idx += 1
            is_drawing = not is_drawing  # Чередуем рисование/пропуск

    def _draw_styled_circle(self, circle, cx, cy, radius_px, draw_color, line_width, style_type):
        """Отрисовка окружности со стилевыми эффектами (волна, зигзаг)"""
        # Для очень маленьких окружностей рисуем обычную линию
        if radius_px < 4:
            x1 = cx - radius_px
            y1 = cy - radius_px
            x2 = cx + radius_px
            y2 = cy + radius_px
            self.canvas.create_oval(x1, y1, x2, y2, outline=draw_color, width=line_width, fill='')
            return

        if style_type == 'wave':
            coords = self._generate_circle_wave_coords(cx, cy, radius_px)
            smooth = True
        else:  # zigzag
            coords = self._generate_circle_zigzag_coords(cx, cy, radius_px)
            smooth = False

        if len(coords) >= 4:
            self.canvas.create_line(*coords, fill=draw_color, width=line_width, smooth=smooth)

    def draw_arc(self, arc, override_color=None, override_width=None):
        """Отрисовывает дугу с учетом стиля."""
        draw_color = override_color if override_color else arc.color
        style = self.state.line_styles.get(arc.style_name)

        line_width = 1
        dash_pattern = None
        is_complex_style = False

        if style:
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
            line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))

            if style.dash_pattern:
                main_dash, main_gap = style.dash_pattern
                base = getattr(style, 'base_type', 'solid')
                if base == 'dash_dot_dot':
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base == 'dash_dot':
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    dash_pattern = [main_dash, main_gap]

            if getattr(style, 'base_type', 'solid') in ['wave', 'zigzag']:
                is_complex_style = True

        if override_width:
            line_width = override_width
            dash_pattern = None
            is_complex_style = False

        cx, cy = self.converter.world_to_screen(arc.center.x, arc.center.y)
        radius_px = arc.radius * self.state.zoom
        # Ограничиваем sweep, чтобы не превращался визуально в полную окружность
        sweep = min(arc.sweep_angle, 2 * math.pi - 1e-4)
        start_deg = math.degrees(arc.start_angle)
        extent_deg = min(359.999, math.degrees(sweep))

        x1 = cx - radius_px
        y1 = cy - radius_px
        x2 = cx + radius_px
        y2 = cy + radius_px

        if dash_pattern:
            self._draw_dashed_arc(arc, cx, cy, radius_px, draw_color, line_width, dash_pattern)
        elif is_complex_style:
            self._draw_styled_arc(arc, cx, cy, radius_px, draw_color, line_width, getattr(style, 'base_type', 'solid'))
        else:
            self.canvas.create_arc(x1, y1, x2, y2,
                                   start=start_deg,
                                   extent=extent_deg,
                                   outline=draw_color,
                                   width=line_width,
                                   style=tk.ARC)

    def _draw_dashed_arc(self, arc, cx, cy, radius_px, draw_color, line_width, dash_pattern):
        """Отрисовка штриховой дуги."""
        if radius_px <= 0:
            return

        sweep = min(arc.sweep_angle, 2 * math.pi - 1e-4)
        start = arc.start_angle
        zoom = self.state.zoom
        scaled_pattern = [float(val) * zoom for val in dash_pattern]

        current_angle = 0.0
        pat_idx = 0
        is_drawing = True

        x1 = cx - radius_px
        y1 = cy - radius_px
        x2 = cx + radius_px
        y2 = cy + radius_px

        while current_angle < sweep - 1e-6:
            seg_len = scaled_pattern[pat_idx % len(scaled_pattern)]
            seg_angle = seg_len / radius_px
            actual_angle = min(seg_angle, sweep - current_angle)

            if is_drawing and actual_angle > 0.01:
                start_deg = math.degrees(start + current_angle)
                extent_deg = math.degrees(actual_angle)
                self.canvas.create_arc(x1, y1, x2, y2,
                                       start=start_deg,
                                       extent=extent_deg,
                                       outline=draw_color,
                                       width=line_width,
                                       style=tk.ARC)

            current_angle += actual_angle
            pat_idx += 1
            is_drawing = not is_drawing

    def _draw_styled_arc(self, arc, cx, cy, radius_px, draw_color, line_width, style_type):
        """Отрисовка дуги со стилем волна/зигзаг (с учётом текущего преобразования координат)."""
        sweep = min(arc.sweep_angle, 2 * math.pi - 1e-4)
        if sweep < 1e-6 or radius_px <= 0:
            return

        if style_type == 'wave':
            coords = self._generate_arc_wave_coords(arc, sweep)
            smooth_flag = True
        else:
            coords = self._generate_arc_zigzag_coords(arc, sweep)
            smooth_flag = False

        if len(coords) >= 4:
            self.canvas.create_line(*coords, fill=draw_color, width=line_width, smooth=smooth_flag)

    def _compute_screen_point_and_tangent(self, center, radius, angle_world):
        """Возвращает экранную точку на дуге и касательный вектор в экранных координатах."""
        # Точка в мировых
        wx = center.x + radius * math.cos(angle_world)
        wy = center.y + radius * math.sin(angle_world)
        sx, sy = self.converter.world_to_screen(wx, wy)

        # Касательный вектор в мировых (до поворота вида)
        tx_w = -math.sin(angle_world)
        ty_w = math.cos(angle_world)

        # Учитываем поворот вида
        rot = self.state.rotation
        tx_r = tx_w * math.cos(rot) - ty_w * math.sin(rot)
        ty_r = tx_w * math.sin(rot) + ty_w * math.cos(rot)

        # Масштаб и инверсию Y, как в world_to_screen
        tx_s = tx_r * self.state.zoom
        ty_s = -ty_r * self.state.zoom

        return sx, sy, tx_s, ty_s

    def _generate_arc_wave_coords(self, arc, sweep_limit):
        zoom = self.state.zoom
        amplitude = 3 * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0)

        radius_px = arc.radius * zoom
        arc_length_px = radius_px * sweep_limit
        num_points = max(60, int(arc_length_px / 4))
        angle_step = sweep_limit / num_points if num_points else sweep_limit

        coords = []
        arc_len = 0.0
        prev_base = None

        for i in range(num_points + 1):
            ang = arc.start_angle + i * angle_step
            sx, sy, tx, ty = self._compute_screen_point_and_tangent(arc.center, arc.radius, ang)

            if prev_base:
                arc_len += math.sqrt((sx - prev_base[0]) ** 2 + (sy - prev_base[1]) ** 2)

            # Нормаль к касательной (в экранных координатах)
            n_len = math.sqrt(tx * tx + ty * ty)
            if n_len < 1e-9:
                nx, ny = 0.0, 0.0
            else:
                nx, ny = -ty / n_len, tx / n_len

            offset = amplitude * math.sin(arc_len * freq)
            coords.extend([sx + nx * offset, sy + ny * offset])
            prev_base = (sx, sy)

        return coords

    def _generate_arc_zigzag_coords(self, arc, sweep_limit):
        zoom = self.state.zoom
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        radius_px = arc.radius * zoom
        arc_length_px = radius_px * sweep_limit
        coords = []
        s = 0.0

        def point_at_length(length_px):
            ang = arc.start_angle + (length_px / radius_px)
            sx, sy, tx, ty = self._compute_screen_point_and_tangent(arc.center, arc.radius, ang)
            # Нормаль к касательной
            n_len = math.sqrt(tx * tx + ty * ty)
            nx, ny = (0.0, 0.0) if n_len < 1e-9 else (-ty / n_len, tx / n_len)
            return sx, sy, nx, ny

        x0, y0, _, _ = point_at_length(0.0)
        coords.extend([x0, y0])

        while s < arc_length_px - 1e-6:
            next_s = min(s + period, arc_length_px)
            x_end, y_end, nx_end, ny_end = point_at_length(next_s)
            coords.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= arc_length_px:
                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, nx1, ny1 = point_at_length(d1)
                x2, y2, nx2, ny2 = point_at_length(d2)
                x3, y3, _, _ = point_at_length(d3)

                coords.extend([
                    x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                    x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                    x3, y3
                ])
                s = d3
            else:
                break

        return coords

    def _generate_circle_wave_coords(self, cx, cy, radius_px):
        """Генерация координат волнистой окружности по тем же параметрам, что и для отрезка."""
        zoom = self.state.zoom
        amplitude = 3 * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0)

        circumference = 2 * math.pi * radius_px
        # Шаг дискретизации ~ 4px
        num_points = max(120, int(circumference / 4))
        angle_step = 2 * math.pi / num_points

        coords = []
        arc_len = 0.0
        prev_x = prev_y = None

        for i in range(num_points + 1):
            ang = i * angle_step
            x = cx + radius_px * math.cos(ang)
            y = cy + radius_px * math.sin(ang)

            if prev_x is not None:
                arc_len += math.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)

            # Радиальная нормаль (совпадает с направлением радиуса)
            nx = math.cos(ang)
            ny = math.sin(ang)

            offset = amplitude * math.sin(arc_len * freq)
            coords.extend([x + nx * offset, y + ny * offset])

            prev_x, prev_y = x, y

        return coords

    def _generate_circle_zigzag_coords(self, cx, cy, radius_px):
        """Генерация координат зигзагообразной окружности по параметрам отрезка."""
        zoom = self.state.zoom
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        circumference = 2 * math.pi * radius_px

        coords = []
        s = 0.0

        def point_on_circle(arc_len):
            ang = arc_len / radius_px
            return cx + radius_px * math.cos(ang), cy + radius_px * math.sin(ang), ang

        # Стартовая точка
        x0, y0, ang0 = point_on_circle(0.0)
        coords.extend([x0, y0])

        while s < circumference:
            next_s = min(s + period, circumference)
            x_end, y_end, ang_end = point_on_circle(next_s)
            coords.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= circumference:
                # Нормаль (радиальная) в точке начала излома
                # Используем направление радиуса (внутрь/наружу)
                ncos = math.cos(ang_end)
                nsin = math.sin(ang_end)

                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, a1 = point_on_circle(d1)
                x2, y2, a2 = point_on_circle(d2)
                x3, y3, a3 = point_on_circle(d3)

                coords.extend([
                    x1 - ncos * amplitude, y1 - nsin * amplitude,
                    x2 + ncos * amplitude, y2 + nsin * amplitude,
                    x3, y3
                ])

                s = d3
            else:
                # Завершаем окружность
                break

        return coords

    def draw_segment(self, segment, override_color=None, override_width=None):
        # Отрисовывает один отрезок (линию) на холсте
        # override_color, override_width - используются для выделения или других спецэффектов
        
        # Выбираем цвет (переопределенный или из сегмента)
        draw_color = override_color if override_color else segment.color
        
        # Получаем стиль линии из state
        style = self.state.line_styles.get(segment.style_name)
        
        # Дефолтные значения
        line_width = 1
        dash_pattern = None
        is_complex_geo = False
        
        # Если стиль найден, обработаем его свойства
        if style:
            # Вычисляем толщину линии на основе базовой толщины
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
            
            # Основная линия толще, тонкая - в 2 раза тоньше
            if style.is_main:
                line_width = max(1, int(s_px))
            else:
                line_width = max(1, int(s_px / 2))
            
            # === ОБРАБОТКА ПАТТЕРНА ШТРИХОВКИ ===
            if style.dash_pattern:
                main_dash = style.dash_pattern[0]
                main_gap = style.dash_pattern[1]
                
                # Определяем тип штриховки (обычная, пунктир или штрих-пунктир)
                base = getattr(style, 'base_type', 'solid')
                
                if base == 'dash_dot_dot':
                    # Штрих-пунктир-пунктир (две точки)
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base == 'dash_dot':
                    # Штрих-пунктир (одна точка)
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    # Просто штриховая
                    dash_pattern = [main_dash, main_gap]
            
            # === ПРОВЕРКА СЛОЖНЫХ ГЕОМЕТРИЙ (волна, изогнутая) ===
            if getattr(style, 'base_type', 'solid') in ['wave', 'zigzag']:
                is_complex_geo = True
        
        if override_width:
            line_width = override_width
            dash_pattern = None
            is_complex_geo = False 
        
        # Конвертируем мировые координаты в экранные
        sx1, sy1 = self.converter.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.converter.world_to_screen(segment.p2.x, segment.p2.y)
        
        # === РИСОВАНИЕ СЛОЖНЫХ ГЕОМЕТРИЙ (волна или изогнутая) ===
        if is_complex_geo:
            coords = []
            smooth_flag = False
            
            base_type = getattr(style, 'base_type', 'solid')
            
            if base_type == 'wave':
                # Волнистая линия с фиксированным количеством волн (если задано)
                coords = self._generate_wave_coords(sx1, sy1, sx2, sy2, fixed_count=segment.waves_count)
                smooth_flag = True
            elif base_type == 'zigzag':
                # Зубчатая линия с фиксированным количеством зубьев
                # ПЕРЕДАЕМ KINKS_COUNT из сегмента
                coords = self._generate_zigzag_coords(sx1, sy1, sx2, sy2, fixed_count=segment.kinks_count)
                smooth_flag = False
            
            # Если координаты успешно сгенерированы, рисуем сложную линию
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill=draw_color, width=line_width, capstyle=tk.ROUND, smooth=smooth_flag)
            return
        
        # === РИСОВАНИЕ ПРЕРЫВИСТОЙ ЛИНИИ ===
        if dash_pattern:
            # Генерируем сегменты и рисуем каждый отдельно
            segments_list = self._generate_dashed_coords(sx1, sy1, sx2, sy2, dash_pattern)
            for seg in segments_list:
                self.canvas.create_line(seg[0], seg[1], seg[2], seg[3], fill=draw_color, width=line_width, capstyle=tk.ROUND)
        else:
            # === РИСОВАНИЕ ОБЫЧНОЙ СПЛОШНОЙ ЛИНИИ ===
            self.canvas.create_line(sx1, sy1, sx2, sy2, fill=draw_color, width=line_width, capstyle=tk.ROUND)

    def draw_rectangle(self, rectangle, override_color=None, override_width=None):
        """Отрисовка прямоугольника через набор сегментов и дуг."""
        segments, arcs = rectangle.build_edges()
        for seg in segments:
            self.draw_segment(seg, override_color=override_color, override_width=override_width)
        for arc in arcs:
            self.draw_arc(arc, override_color=override_color, override_width=override_width)

    def draw_point(self, point, size=4, color='black'):
        x, y = self.converter.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def render_scene(self):
        # Главный метод отрисовки всей сцены
        # Вызывается при каждом обновлении (например, при движении мыши или изменении зума)
        
        # 1. Очищаем холст
        self.clear()
        
        # 2. Рисуем сетку и оси
        self.draw_grid_and_axes()
        
        # 3. Рисуем выделенные сегменты (с голубым цветом и увеличенной толщиной)
        for seg in self.state.selected_segments:
            self.draw_segment(seg, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))

        # 4. Рисуем выделенные окружности (с голубым цветом и увеличенной толщиной)
        for circle in self.state.selected_circles:
            self.draw_circle(circle, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))

        # 5. Рисуем выделенные дуги
        for arc in self.state.selected_arcs:
            self.draw_arc(arc, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))
        # 5.1 Рисуем выделенные прямоугольники
        for rect in self.state.selected_rectangles:
            self.draw_rectangle(rect, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))

        # 5. Рисуем все остальные сегменты
        for segment in self.state.segments:
            self.draw_segment(segment)

        # 6. Рисуем все остальные окружности
        for circle in self.state.circles:
            self.draw_circle(circle)

        # 7. Рисуем все дуги
        for arc in self.state.arcs:
            self.draw_arc(arc)

        # 7.1 Рисуем все прямоугольники
        for rect in self.state.rectangles:
            self.draw_rectangle(rect)

        # 8. Рисуем превью сегмента (синяя пунктирная линия при рисовании нового отрезка)
        if self.state.preview_segment:
            self.draw_segment(self.state.preview_segment, override_color='blue')

        # 9. Рисуем превью окружности (синяя окружность при рисовании новой окружности)
        if self.state.preview_circle:
            self.draw_circle(self.state.preview_circle, override_color='blue')

        # 10. Рисуем превью дуги
        if self.state.preview_arc:
            self.draw_arc(self.state.preview_arc, override_color='blue')

        # 10.1 Рисуем превью прямоугольника
        if self.state.preview_rectangle:
            self.draw_rectangle(self.state.preview_rectangle, override_color='blue')

        # 11. Рисуем активные точки (начало и конец текущего отрезка/окружности)
        if self.state.active_p1:
            self.draw_point(self.state.active_p1)
        if self.state.active_p2:
            self.draw_point(self.state.active_p2)
        if self.state.active_p3:
            self.draw_point(self.state.active_p3)
        if self.state.active_p4:
            self.draw_point(self.state.active_p4)