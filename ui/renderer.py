# ui/renderer.py

'''
Отвечает за низкоуровневую отрисовку графики.
Реализует паттерн "Отрисовщик": отделяет логику хранения данных от логики их отображения.
'''

import math
import tkinter as tk
from logic.geometry import Spline  # for type hints
from logic.snap import SnapType  # for snap indicator rendering

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

    def _generate_wave_coords(self, x1, y1, x2, y2, wave_amplitude=None):
        """Генерирует координаты волнистой линии.
        
        Args:
            wave_amplitude: Амплитуда волны в единицах чертежа (из стиля).
                           Если None - используется значение по умолчанию (3.0).
        """
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = []
        zoom = self.state.zoom
        
        # Базовые параметры
        step = 5 * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0)
        
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        # Ограничение: амплитуда не может быть больше половины длины линии
        max_amp = length / (2 * zoom) if length > 0 else base_amp
        actual_amp = min(base_amp, max_amp)
        amplitude = actual_amp * (zoom / 5.0)
        
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

    def _generate_zigzag_coords(self, x1, y1, x2, y2, kinks_count=None):
        """Генерирует координаты линии с изломами.
        
        Args:
            kinks_count: Количество изломов (из стиля).
                        Если None - используется автоматический режим.
                        Если больше, чем помещается - используется максимум.
        """
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        points = [x1, y1]
        
        zoom = self.state.zoom
        # Базовые параметры
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)
        
        # ЛОГИКА ФИКСИРОВАННОГО КОЛИЧЕСТВА
        if kinks_count is not None and kinks_count >= 1:
            # Максимальное количество изломов, которое может поместиться
            # Минимальный зазор между изломами = kink_len * 0.5
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((length - min_gap) / (kink_len + min_gap)))
            
            # Ограничиваем запрошенное количество
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            # Считаем суммарную длину всех изломов
            total_kinks_len = actual_kinks * kink_len
            
            # Если изломы влезают в длину линии
            if total_kinks_len < length:
                # Оставшееся место делим поровну на промежутки
                # Промежутков всегда N + 1 (начало...излом...конец)
                gap = (length - total_kinks_len) / (actual_kinks + 1)
                
                current_dist = 0
                for _ in range(actual_kinks):
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
        
        # СТАНДАРТНАЯ ЛОГИКА (АВТОМАТИЧЕСКАЯ) - если kinks_count не задан или равен 0
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

    def _circle_polyline(self, circle, num_points=None):
        """Возвращает экранные точки окружности и накопленные длины (аналогично эллипсу).
        
        Точки генерируются в мировых координатах и преобразуются через world_to_screen,
        что обеспечивает правильное поведение при повороте вида.
        """
        radius = circle.radius
        circumference_px = 2 * math.pi * radius * self.state.zoom
        if num_points is None:
            # Оптимизация: ограничиваем максимум 360 точками для производительности
            # ~4 px между точками, min 72, max 360
            num_points = max(72, min(360, int(circumference_px / 4)))

        coords = []
        cum_lengths = [0.0]
        prev = None

        for i in range(num_points + 1):
            ang = (2 * math.pi * i) / num_points
            # Точка в мировых координатах
            wx = circle.center.x + radius * math.cos(ang)
            wy = circle.center.y + radius * math.sin(ang)
            # Преобразуем в экранные
            sx, sy = self.converter.world_to_screen(wx, wy)
            coords.append((sx, sy))
            if prev is not None:
                seg_len = math.sqrt((sx - prev[0]) ** 2 + (sy - prev[1]) ** 2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
            prev = (sx, sy)

        # Замыкаем окружность
        if coords and len(coords) > 1:
            first = coords[0]
            last = coords[-1]
            if abs(first[0] - last[0]) > 0.1 or abs(first[1] - last[1]) > 0.1:
                coords.append(first)
                seg_len = math.sqrt((first[0] - last[0]) ** 2 + (first[1] - last[1]) ** 2)
                cum_lengths.append(cum_lengths[-1] + seg_len)

        return coords, cum_lengths

    def draw_circle(self, circle, override_color=None, override_width=None):
        """Отрисовывает окружность на холсте через полилинию (как эллипс).
        
        Это обеспечивает правильное поведение при повороте вида.
        """
        draw_color = override_color if override_color else circle.color
        style = self.state.line_styles.get(circle.style_name)

        line_width = 1
        dash_pattern = None
        base_type = 'solid'

        if style:
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
            line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))
            base_type = getattr(style, 'base_type', 'solid')
            
            if style.dash_pattern:
                main_dash, main_gap = style.dash_pattern
                if base_type == 'dash_dot_dot':
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base_type == 'dash_dot':
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    dash_pattern = [main_dash, main_gap]

        if override_width:
            line_width = override_width
            dash_pattern = None
            base_type = 'solid'

        # Получаем точки окружности через world_to_screen
        coords, cum_lengths = self._circle_polyline(circle)
        if not coords:
            return

        if dash_pattern:
            # Штриховая окружность
            scaled = [float(v) * self.state.zoom for v in dash_pattern]
            self._draw_dashed_polyline(coords, scaled, draw_color, line_width)
        elif base_type in ['wave', 'zigzag']:
            # Волна или зигзаг
            if base_type == 'wave':
                wave_amp = getattr(style, 'wave_amplitude', None)
                styled = self._generate_ellipse_wave_coords(coords, cum_lengths, wave_amplitude=wave_amp)
                smooth_flag = True
            else:
                kinks = getattr(style, 'kinks_count', None)
                styled = self._generate_ellipse_zigzag_coords(coords, cum_lengths, kinks_count=kinks)
                smooth_flag = False
            if len(styled) >= 4:
                self.canvas.create_line(*styled, fill=draw_color, width=line_width, smooth=smooth_flag)
        else:
            # Сплошная окружность
            # smooth=False для производительности - точки уже плавно расположены по кривой
            flat_coords = []
            for x, y in coords:
                flat_coords.extend([x, y])
            self.canvas.create_line(*flat_coords, fill=draw_color, width=line_width, smooth=False)

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
        # Учитываем поворот вида: базовый угол дуги должен вращаться вместе с остальными координатами
        start_deg = math.degrees(arc.start_angle + self.state.rotation)
        extent_deg = min(359.999, math.degrees(sweep))

        x1 = cx - radius_px
        y1 = cy - radius_px
        x2 = cx + radius_px
        y2 = cy + radius_px

        if dash_pattern:
            self._draw_dashed_arc(arc, cx, cy, radius_px, draw_color, line_width, dash_pattern)
        elif is_complex_style:
            self._draw_styled_arc(arc, cx, cy, radius_px, draw_color, line_width, style)
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
                # Смещаем угол на поворот вида, чтобы штриховые сегменты не "уезжали" при вращении
                start_deg = math.degrees(start + current_angle + self.state.rotation)
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

    def _draw_styled_arc(self, arc, cx, cy, radius_px, draw_color, line_width, style):
        """Отрисовка дуги со стилем волна/зигзаг (с учётом текущего преобразования координат)."""
        sweep = min(arc.sweep_angle, 2 * math.pi - 1e-4)
        if sweep < 1e-6 or radius_px <= 0:
            return

        style_type = getattr(style, 'base_type', 'solid')
        if style_type == 'wave':
            wave_amp = getattr(style, 'wave_amplitude', None)
            coords = self._generate_arc_wave_coords(arc, sweep, wave_amplitude=wave_amp)
            smooth_flag = True
        else:
            kinks = getattr(style, 'kinks_count', None)
            coords = self._generate_arc_zigzag_coords(arc, sweep, kinks_count=kinks)
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

    def _generate_arc_wave_coords(self, arc, sweep_limit, wave_amplitude=None):
        """Генерация координат волнистой дуги.
        
        Args:
            wave_amplitude: Амплитуда волны из стиля.
        """
        zoom = self.state.zoom
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        amplitude = base_amp * (zoom / 5.0)
        freq = 0.2 / (zoom / 5.0)

        radius_px = arc.radius * zoom
        arc_length_px = radius_px * sweep_limit
        num_points = max(60, min(360, int(arc_length_px / 4)))  # max 360 для дуги
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

    def _generate_arc_zigzag_coords(self, arc, sweep_limit, kinks_count=None):
        """Генерация координат дуги с изломами.
        
        Рисует базовую дугу с заданным количеством изломов.
        Между изломами дуга отрисовывается точками вдоль контура.
        
        Args:
            kinks_count: Количество изломов из стиля.
        """
        zoom = self.state.zoom
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        radius_px = arc.radius * zoom
        arc_length_px = radius_px * sweep_limit
        
        # Адаптивный шаг: ограничиваем максимум ~500 точек для дуги
        MAX_POINTS = 500
        arc_step = max(4, arc_length_px / MAX_POINTS) if arc_length_px > 0 else 4
        coords = []

        def point_at_length(length_px):
            ang = arc.start_angle + (length_px / radius_px)
            sx, sy, tx, ty = self._compute_screen_point_and_tangent(arc.center, arc.radius, ang)
            n_len = math.sqrt(tx * tx + ty * ty)
            nx, ny = (0.0, 0.0) if n_len < 1e-9 else (-ty / n_len, tx / n_len)
            return sx, sy, nx, ny

        def add_arc_points(coords, start_s, end_s):
            """Добавляет промежуточные точки дуги от start_s до end_s."""
            s = start_s + arc_step
            while s < end_s - 1e-6:
                x, y, _, _ = point_at_length(s)
                coords.extend([x, y])
                s += arc_step

        x0, y0, _, _ = point_at_length(0.0)
        coords.extend([x0, y0])
        
        # Режим с фиксированным количеством изломов
        if kinks_count is not None and kinks_count >= 1:
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((arc_length_px - min_gap) / (kink_len + min_gap)))
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            total_kinks_len = actual_kinks * kink_len
            if total_kinks_len < arc_length_px:
                gap = (arc_length_px - total_kinks_len) / (actual_kinks + 1)
                
                s = 0.0
                for _ in range(actual_kinks):
                    # Добавляем промежуточные точки до излома
                    kink_start = s + gap
                    add_arc_points(coords, s, kink_start)
                    
                    # Точка перед изломом
                    x_end, y_end, _, _ = point_at_length(kink_start)
                    coords.extend([x_end, y_end])
                    
                    # Рисуем излом
                    d1 = kink_start + kink_len * 0.25
                    d2 = kink_start + kink_len * 0.75
                    d3 = kink_start + kink_len
                    
                    x1, y1, nx1, ny1 = point_at_length(d1)
                    x2, y2, nx2, ny2 = point_at_length(d2)
                    x3, y3, _, _ = point_at_length(d3)
                    
                    coords.extend([
                        x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                        x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                        x3, y3
                    ])
                    s = d3
                
                # Дорисовываем конец дуги
                if s < arc_length_px:
                    add_arc_points(coords, s, arc_length_px)
                    x_end, y_end, _, _ = point_at_length(arc_length_px)
                    coords.extend([x_end, y_end])
                return coords

        # Автоматический режим
        period = 40 * (zoom / 5.0)
        s = 0.0
        
        while s < arc_length_px - 1e-6:
            next_s = min(s + period, arc_length_px)
            
            # Добавляем промежуточные точки
            add_arc_points(coords, s, next_s)
            
            x_end, y_end, _, _ = point_at_length(next_s)
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

    def _generate_circle_wave_coords(self, cx, cy, radius_px, wave_amplitude=None):
        """Генерация координат волнистой окружности.
        
        Корректно замыкает волну, подбирая частоту так, чтобы было целое число периодов.
        Учитывает поворот вида, чтобы паттерн оставался фиксированным после построения.
        
        Args:
            wave_amplitude: Амплитуда волны из стиля (или None для значения по умолчанию).
        """
        zoom = self.state.zoom
        rotation = self.state.rotation  # Учитываем поворот вида
        
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        amplitude = base_amp * (zoom / 5.0)

        circumference = 2 * math.pi * radius_px
        if circumference <= 0:
            return []
        
        # Подбираем частоту так, чтобы волна замкнулась (целое число периодов)
        base_freq = 0.2 / (zoom / 5.0)
        num_periods = max(1, round(circumference * base_freq / (2 * math.pi)))
        freq = num_periods * 2 * math.pi / circumference
        
        # Шаг дискретизации ~ 4px, max 720 точек
        num_points = max(120, min(720, int(circumference / 4)))
        angle_step = 2 * math.pi / num_points

        coords = []
        first_point = None

        for i in range(num_points):
            # Мировой угол (без поворота)
            world_ang = i * angle_step
            # Экранный угол с учетом поворота вида
            screen_ang = world_ang + rotation
            
            x = cx + radius_px * math.cos(screen_ang)
            y = cy + radius_px * math.sin(screen_ang)

            # Длина дуги от начала (в мировых координатах)
            arc_len = world_ang * radius_px

            # Радиальная нормаль в экранных координатах
            nx = math.cos(screen_ang)
            ny = math.sin(screen_ang)

            offset = amplitude * math.sin(arc_len * freq)
            px, py = x + nx * offset, y + ny * offset
            coords.extend([px, py])
            
            if first_point is None:
                first_point = (px, py)

        # Замыкаем окружность - добавляем первую точку в конец
        if first_point:
            coords.extend([first_point[0], first_point[1]])

        return coords

    def _generate_circle_zigzag_coords(self, cx, cy, radius_px, kinks_count=None):
        """Генерация координат окружности с изломами.
        
        Рисует базовую окружность с заданным количеством изломов.
        Между изломами окружность отрисовывается точками вдоль дуги.
        Учитывает поворот вида, чтобы паттерн оставался фиксированным после построения.
        
        Args:
            kinks_count: Количество изломов из стиля (или None для автоматического режима).
        """
        zoom = self.state.zoom
        rotation = self.state.rotation  # Учитываем поворот вида
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        circumference = 2 * math.pi * radius_px
        
        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        arc_step = max(4, circumference / MAX_POINTS) if circumference > 0 else 4

        def point_on_circle(arc_len):
            world_ang = arc_len / radius_px
            # Экранный угол с учетом поворота вида
            screen_ang = world_ang + rotation
            return cx + radius_px * math.cos(screen_ang), cy + radius_px * math.sin(screen_ang), screen_ang
        
        def normal_at_angle(screen_ang):
            return math.cos(screen_ang), math.sin(screen_ang)

        def add_arc_points(coords, start_s, end_s):
            """Добавляет промежуточные точки дуги от start_s до end_s."""
            s = start_s + arc_step
            while s < end_s - 1e-6:
                x, y, _ = point_on_circle(s)
                coords.extend([x, y])
                s += arc_step

        coords = []
        
        # Стартовая точка
        x0, y0, _ = point_on_circle(0.0)
        first_point = (x0, y0)
        coords.extend([x0, y0])
        
        # Режим с фиксированным количеством изломов
        if kinks_count is not None and kinks_count >= 1:
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((circumference - min_gap) / (kink_len + min_gap)))
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            total_kinks_len = actual_kinks * kink_len
            if total_kinks_len < circumference:
                gap = (circumference - total_kinks_len) / actual_kinks
                
                s = 0.0
                for _ in range(actual_kinks):
                    # Добавляем промежуточные точки дуги до излома
                    kink_start = s + gap
                    add_arc_points(coords, s, kink_start)
                    
                    # Точка перед изломом
                    x_end, y_end, ang_end = point_on_circle(kink_start)
                    coords.extend([x_end, y_end])
                    
                    # Рисуем излом
                    d1 = kink_start + kink_len * 0.25
                    d2 = kink_start + kink_len * 0.75
                    d3 = kink_start + kink_len
                    
                    x1, y1, a1 = point_on_circle(d1)
                    x2, y2, a2 = point_on_circle(d2)
                    x3, y3, a3 = point_on_circle(d3)
                    
                    n1cos, n1sin = normal_at_angle(a1)
                    n2cos, n2sin = normal_at_angle(a2)
                    
                    coords.extend([
                        x1 - n1cos * amplitude, y1 - n1sin * amplitude,
                        x2 + n2cos * amplitude, y2 + n2sin * amplitude,
                        x3, y3
                    ])
                    s = d3
                
                # Добавляем оставшуюся дугу до начала
                add_arc_points(coords, s, circumference)
                
                # Замыкаем окружность
                coords.extend([first_point[0], first_point[1]])
                return coords
        
        # Автоматический режим
        period = 40 * (zoom / 5.0)
        s = 0.0
        
        while s < circumference - 1e-6:
            next_s = min(s + period, circumference)
            
            # Добавляем промежуточные точки дуги
            add_arc_points(coords, s, next_s)
            
            x_end, y_end, ang_end = point_on_circle(next_s)
            coords.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= circumference:
                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, a1 = point_on_circle(d1)
                x2, y2, a2 = point_on_circle(d2)
                x3, y3, a3 = point_on_circle(d3)
                
                n1cos, n1sin = normal_at_angle(a1)
                n2cos, n2sin = normal_at_angle(a2)

                coords.extend([
                    x1 - n1cos * amplitude, y1 - n1sin * amplitude,
                    x2 + n2cos * amplitude, y2 + n2sin * amplitude,
                    x3, y3
                ])
                s = d3
            else:
                break

        # Замыкаем окружность
        coords.extend([first_point[0], first_point[1]])
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
                # Волнистая линия - используем амплитуду из стиля
                wave_amp = getattr(style, 'wave_amplitude', None)
                coords = self._generate_wave_coords(sx1, sy1, sx2, sy2, wave_amplitude=wave_amp)
                smooth_flag = True
            elif base_type == 'zigzag':
                # Линия с изломами - используем количество изломов из стиля
                kinks = getattr(style, 'kinks_count', None)
                coords = self._generate_zigzag_coords(sx1, sy1, sx2, sy2, kinks_count=kinks)
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
        
        # Проверяем, нужно ли рисовать как единый контур для zigzag/wave
        style = self.state.line_styles.get(rectangle.style_name)
        base_type = getattr(style, 'base_type', 'solid') if style else 'solid'
        
        if base_type in ['wave', 'zigzag'] and not override_width:
            # Рисуем как единый контур (включая случай со скруглениями)
            self._draw_rectangle_styled(rectangle, segments, arcs, style, override_color)
        else:
            # Рисуем по сегментам (для обычных стилей)
            for seg in segments:
                self.draw_segment(seg, override_color=override_color, override_width=override_width)
            for arc in arcs:
                self.draw_arc(arc, override_color=override_color, override_width=override_width)

    def _draw_rectangle_styled(self, rectangle, segments, arcs, style, override_color=None):
        """Отрисовка прямоугольника с zigzag/wave как единого контура.
        
        Поддерживает прямоугольники с фасками и скруглениями.
        """
        draw_color = override_color if override_color else rectangle.color
        
        s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
        line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))
        
        # Собираем все точки контура прямоугольника
        screen_coords = []
        cum_lengths = [0.0]
        
        if arcs:
            # Прямоугольник со скруглениями - собираем контур в правильном порядке
            # Порядок: bottom, BR_arc, right, TR_arc, top, TL_arc, left, BL_arc
            # segments: [bottom, right, top, left]
            # arcs: [BL, BR, TR, TL]
            arc_order = [1, 2, 3, 0]  # BR, TR, TL, BL
            
            for i, seg in enumerate(segments):
                # Добавляем сегмент
                sx1, sy1 = self.converter.world_to_screen(seg.p1.x, seg.p1.y)
                sx2, sy2 = self.converter.world_to_screen(seg.p2.x, seg.p2.y)
                
                if not screen_coords:
                    screen_coords.append((sx1, sy1))
                screen_coords.append((sx2, sy2))
                
                seg_len = math.sqrt((sx2 - sx1)**2 + (sy2 - sy1)**2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
                
                # Добавляем дугу после сегмента (дискретизируем в точки)
                arc = arcs[arc_order[i]]
                arc_points = self._discretize_arc(arc)
                
                for px, py in arc_points[1:]:  # Пропускаем первую точку (совпадает с концом сегмента)
                    if screen_coords:
                        last = screen_coords[-1]
                        seg_len = math.sqrt((px - last[0])**2 + (py - last[1])**2)
                        cum_lengths.append(cum_lengths[-1] + seg_len)
                    screen_coords.append((px, py))
        else:
            # Обычный прямоугольник (с фасками или без)
            for seg in segments:
                sx1, sy1 = self.converter.world_to_screen(seg.p1.x, seg.p1.y)
                sx2, sy2 = self.converter.world_to_screen(seg.p2.x, seg.p2.y)
                
                if not screen_coords:
                    screen_coords.append((sx1, sy1))
                screen_coords.append((sx2, sy2))
                
                seg_len = math.sqrt((sx2 - sx1)**2 + (sy2 - sy1)**2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
        
        # Замыкаем контур
        if screen_coords and len(screen_coords) > 1:
            first = screen_coords[0]
            last = screen_coords[-1]
            if abs(first[0] - last[0]) > 1 or abs(first[1] - last[1]) > 1:
                screen_coords.append(first)
                seg_len = math.sqrt((first[0] - last[0])**2 + (first[1] - last[1])**2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
        
        base_type = getattr(style, 'base_type', 'solid')
        if base_type == 'wave':
            wave_amp = getattr(style, 'wave_amplitude', None)
            styled = self._generate_polyline_wave_coords_closed(screen_coords, cum_lengths, wave_amplitude=wave_amp)
            smooth_flag = True
        else:  # zigzag
            kinks = getattr(style, 'kinks_count', None)
            styled = self._generate_polyline_zigzag_coords_closed(screen_coords, cum_lengths, kinks_count=kinks)
            smooth_flag = False
        
        if len(styled) >= 4:
            self.canvas.create_line(*styled, fill=draw_color, width=line_width, smooth=smooth_flag)
    
    def _discretize_arc(self, arc, num_points=None):
        """Дискретизирует дугу в список экранных точек."""
        radius_px = arc.radius * self.state.zoom
        arc_length_px = radius_px * arc.sweep_angle
        
        if num_points is None:
            num_points = max(8, min(180, int(arc_length_px / 4)))  # max 180 для дуги
        
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            angle = arc.start_angle + t * arc.sweep_angle
            wx = arc.center.x + arc.radius * math.cos(angle)
            wy = arc.center.y + arc.radius * math.sin(angle)
            sx, sy = self.converter.world_to_screen(wx, wy)
            points.append((sx, sy))
        
        return points

    def draw_polygon(self, polygon, override_color=None, override_width=None):
        """Отрисовывает правильный многоугольник через набор отрезков."""
        edges = polygon.edges()
        
        # Проверяем, нужно ли рисовать как единый контур для zigzag/wave
        style = self.state.line_styles.get(polygon.style_name)
        base_type = getattr(style, 'base_type', 'solid') if style else 'solid'
        
        if base_type in ['wave', 'zigzag'] and not override_width:
            # Рисуем как единый контур
            self._draw_polygon_styled(polygon, edges, style, override_color)
        else:
            # Рисуем по сегментам
            for seg in edges:
                self.draw_segment(seg, override_color=override_color, override_width=override_width)

    def _draw_polygon_styled(self, polygon, edges, style, override_color=None):
        """Отрисовка многоугольника с zigzag/wave как единого контура."""
        draw_color = override_color if override_color else polygon.color
        
        s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
        line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))
        
        # Собираем все точки контура многоугольника
        screen_coords = []
        cum_lengths = [0.0]
        
        for seg in edges:
            sx1, sy1 = self.converter.world_to_screen(seg.p1.x, seg.p1.y)
            sx2, sy2 = self.converter.world_to_screen(seg.p2.x, seg.p2.y)
            
            if not screen_coords:
                screen_coords.append((sx1, sy1))
            screen_coords.append((sx2, sy2))
            
            # Добавляем накопленную длину
            seg_len = math.sqrt((sx2 - sx1)**2 + (sy2 - sy1)**2)
            cum_lengths.append(cum_lengths[-1] + seg_len)
        
        # Замыкаем контур
        if screen_coords and len(screen_coords) > 1:
            first = screen_coords[0]
            last = screen_coords[-1]
            if abs(first[0] - last[0]) > 1 or abs(first[1] - last[1]) > 1:
                screen_coords.append(first)
                seg_len = math.sqrt((first[0] - last[0])**2 + (first[1] - last[1])**2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
        
        base_type = getattr(style, 'base_type', 'solid')
        if base_type == 'wave':
            wave_amp = getattr(style, 'wave_amplitude', None)
            styled = self._generate_polyline_wave_coords_closed(screen_coords, cum_lengths, wave_amplitude=wave_amp)
            smooth_flag = True
        else:  # zigzag
            kinks = getattr(style, 'kinks_count', None)
            styled = self._generate_polyline_zigzag_coords_closed(screen_coords, cum_lengths, kinks_count=kinks)
            smooth_flag = False
        
        if len(styled) >= 4:
            self.canvas.create_line(*styled, fill=draw_color, width=line_width, smooth=smooth_flag)

    # --- ЭЛЛИПСЫ ---

    def _ellipse_polyline(self, ellipse, num_points=None):
        """Возвращает экранные точки эллипса и накопленные длины для последующей стилизации."""
        basis = ellipse._basis()
        perim_px = ellipse.perimeter_approx() * self.state.zoom
        if num_points is None:
            # Оптимизация: ограничиваем максимум 360 точками для производительности
            # ~4 px между точками, min 120, max 360
            num_points = max(120, min(360, int(perim_px / 4)))

        coords = []
        cum_lengths = [0.0]
        prev = None

        for i in range(num_points + 1):
            ang = (2 * math.pi * i) / num_points
            sx, sy = self._ellipse_point_screen(ellipse, ang, basis)
            coords.append((sx, sy))
            if prev is not None:
                seg_len = math.sqrt((sx - prev[0]) ** 2 + (sy - prev[1]) ** 2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
            prev = (sx, sy)

        # Убеждаемся, что путь замкнут
        if coords and (coords[0][0] != coords[-1][0] or coords[0][1] != coords[-1][1]):
            coords.append(coords[0])
            seg_len = math.sqrt((coords[-1][0] - prev[0]) ** 2 + (coords[-1][1] - prev[1]) ** 2)
            cum_lengths.append(cum_lengths[-1] + seg_len)

        return coords, cum_lengths

    def _spline_polyline(self, spline, samples_per_segment=None):
        """Дискретизация сплайна в экранных координатах + накопленные длины.
        
        samples_per_segment: количество точек на сегмент. Если None - вычисляется адаптивно.
        """
        if samples_per_segment is None:
            # Адаптивное количество точек на основе приблизительной длины сплайна
            # Оцениваем длину сплайна в пикселях
            approx_len = spline.approximate_length() * self.state.zoom
            num_segments = max(1, len(spline.control_points) - 1)
            # ~4 пикселя между точками, min 8, max 20 на сегмент
            samples_per_segment = max(8, min(20, int(approx_len / (num_segments * 4))))
        
        pts = spline.sample_points(samples_per_segment)
        coords = []
        cum_lengths = [0.0]
        prev = None
        for pt in pts:
            sx, sy = self.converter.world_to_screen(pt.x, pt.y)
            coords.append((sx, sy))
            if prev is not None:
                seg_len = math.sqrt((sx - prev[0]) ** 2 + (sy - prev[1]) ** 2)
                cum_lengths.append(cum_lengths[-1] + seg_len)
            prev = (sx, sy)
        return coords, cum_lengths

    def _ellipse_point_screen(self, ellipse, angle, basis=None):
        """Экранная точка эллипса по углу параметра."""
        if basis is None:
            basis = ellipse._basis()
        e1x, e1y, a, e2x, e2y, b = basis
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        wx = ellipse.center.x + a * cos_a * e1x + b * sin_a * e2x
        wy = ellipse.center.y + a * cos_a * e1y + b * sin_a * e2y
        return self.converter.world_to_screen(wx, wy)

    def _point_on_polyline(self, coords, cum_lengths, target_len):
        """Интерполяция точки и касательной вдоль полилинии по целевой длине."""
        if not coords or target_len <= 0:
            if len(coords) >= 2:
                dx = coords[1][0] - coords[0][0]
                dy = coords[1][1] - coords[0][1]
                return coords[0][0], coords[0][1], dx, dy
            return 0.0, 0.0, 0.0, 0.0

        total = cum_lengths[-1] if cum_lengths else 0.0
        if target_len >= total:
            if len(coords) >= 2:
                dx = coords[-1][0] - coords[-2][0]
                dy = coords[-1][1] - coords[-2][1]
                return coords[-1][0], coords[-1][1], dx, dy
            return coords[-1][0], coords[-1][1], 0.0, 0.0

        for i in range(1, len(cum_lengths)):
            if cum_lengths[i] >= target_len:
                seg_len = cum_lengths[i] - cum_lengths[i - 1]
                if seg_len < 1e-9:
                    return coords[i][0], coords[i][1], 0.0, 0.0
                t = (target_len - cum_lengths[i - 1]) / seg_len
                x0, y0 = coords[i - 1]
                x1, y1 = coords[i]
                x = x0 + t * (x1 - x0)
                y = y0 + t * (y1 - y0)
                dx = x1 - x0
                dy = y1 - y0
                return x, y, dx, dy
        return coords[-1][0], coords[-1][1], 0.0, 0.0

    def _generate_ellipse_wave_coords(self, coords, cum_lengths, wave_amplitude=None):
        """Генерация координат волнистого эллипса.
        
        Корректно замыкает волну, подбирая частоту так, чтобы было целое число периодов.
        
        Args:
            wave_amplitude: Амплитуда волны из стиля.
        """
        zoom = self.state.zoom
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        amplitude = base_amp * (zoom / 5.0)

        total_len = cum_lengths[-1] if cum_lengths else 0.0
        if total_len <= 0:
            return []
        
        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        step = max(4, total_len / MAX_POINTS)
        
        # Подбираем частоту так, чтобы волна замкнулась (целое число периодов)
        base_freq = 0.2 / (zoom / 5.0)
        num_periods = max(1, round(total_len * base_freq / (2 * math.pi)))
        freq = num_periods * 2 * math.pi / total_len
        
        out = []
        t = 0.0
        first_point = None

        while t < total_len - step * 0.5:
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, t)
            norm_len = math.sqrt(dx * dx + dy * dy)
            if norm_len < 1e-9:
                nx, ny = 0.0, 0.0
            else:
                nx, ny = -dy / norm_len, dx / norm_len
            offset = amplitude * math.sin(t * freq)
            px, py = x + nx * offset, y + ny * offset
            out.extend([px, py])
            
            if first_point is None:
                first_point = (px, py)
            
            t += step

        # Замыкаем эллипс - добавляем первую точку в конец
        if first_point:
            out.extend([first_point[0], first_point[1]])

        return out

    def _generate_polyline_wave_coords(self, coords, cum_lengths, wave_amplitude=None):
        """Стилизация polyline волной (для сплайнов и др.).
        
        Args:
            wave_amplitude: Амплитуда волны в единицах чертежа (из стиля).
        """
        if not coords:
            return []
        zoom = self.state.zoom
        base_freq = 0.2 / (zoom / 5.0)
        
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        total_len = cum_lengths[-1] if cum_lengths else 0.0
        
        # Ограничение амплитуды
        max_amp = total_len / (2 * zoom) if total_len > 0 else base_amp
        actual_amp = min(base_amp, max_amp)
        amplitude = actual_amp * (zoom / 5.0)
        
        freq = base_freq

        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        step = max(4, total_len / MAX_POINTS) if total_len > 0 else 4
        out = []
        t = 0.0
        prev_base = None
        arc_len = 0.0

        while t <= total_len + 1e-6:
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, t)
            if prev_base:
                arc_len += math.sqrt((x - prev_base[0]) ** 2 + (y - prev_base[1]) ** 2)
            norm_len = math.sqrt(dx * dx + dy * dy)
            nx, ny = (0.0, 0.0) if norm_len < 1e-9 else (-dy / norm_len, dx / norm_len)
            offset = amplitude * math.sin(arc_len * freq)
            out.extend([x + nx * offset, y + ny * offset])
            prev_base = (x, y)
            t += step
        return out

    def _generate_polyline_wave_coords_closed(self, coords, cum_lengths, wave_amplitude=None):
        """Стилизация замкнутого polyline волной.
        
        Корректно замыкает волну, подбирая частоту так, чтобы волна была непрерывной.
        
        Args:
            wave_amplitude: Амплитуда волны в единицах чертежа (из стиля).
        """
        if not coords:
            return []
        zoom = self.state.zoom
        
        # Амплитуда из параметра или по умолчанию
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        total_len = cum_lengths[-1] if cum_lengths else 0.0
        
        if total_len <= 0:
            return []
        
        # Ограничение амплитуды
        max_amp = total_len / (2 * zoom) if total_len > 0 else base_amp
        actual_amp = min(base_amp, max_amp)
        amplitude = actual_amp * (zoom / 5.0)
        
        # Подбираем частоту так, чтобы волна замкнулась (целое число периодов)
        base_freq = 0.2 / (zoom / 5.0)
        num_periods = max(1, round(total_len * base_freq / (2 * math.pi)))
        freq = num_periods * 2 * math.pi / total_len

        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        step = max(4, total_len / MAX_POINTS)
        out = []
        t = 0.0
        first_point = None

        while t < total_len - step * 0.5:
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, t)
            norm_len = math.sqrt(dx * dx + dy * dy)
            nx, ny = (0.0, 0.0) if norm_len < 1e-9 else (-dy / norm_len, dx / norm_len)
            offset = amplitude * math.sin(t * freq)
            px, py = x + nx * offset, y + ny * offset
            out.extend([px, py])
            
            if first_point is None:
                first_point = (px, py)
            
            t += step
        
        # Замыкаем - добавляем первую точку
        if first_point:
            out.extend([first_point[0], first_point[1]])
        
        return out

    def _generate_polyline_zigzag_coords(self, coords, cum_lengths, kinks_count=None):
        """Стилизация polyline зигзагом (для сплайнов, многоугольников и др.).
        
        Рисует базовую полилинию с заданным количеством изломов.
        Между изломами полилиния отрисовывается точками вдоль пути.
        
        Args:
            kinks_count: Количество изломов (из стиля).
                        Если больше, чем помещается - используется максимум.
        """
        if not coords:
            return []
        zoom = self.state.zoom
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        total_len = cum_lengths[-1] if cum_lengths else 0.0
        if total_len <= 0:
            return []

        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        path_step = max(4, total_len / MAX_POINTS)

        def normal_at(dist):
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, dist)
            norm_len = math.sqrt(dx * dx + dy * dy)
            nx, ny = (0.0, 0.0) if norm_len < 1e-9 else (-dy / norm_len, dx / norm_len)
            return x, y, nx, ny

        def add_path_points(out, start_s, end_s):
            """Добавляет промежуточные точки пути от start_s до end_s."""
            s = start_s + path_step
            while s < end_s - 1e-6:
                x, y, _, _ = normal_at(s)
                out.extend([x, y])
                s += path_step

        out = []
        x0, y0, _, _ = normal_at(0.0)
        out.extend([x0, y0])

        # Фиксированное число изломов, если задано
        if kinks_count is not None and kinks_count >= 1:
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((total_len - min_gap) / (kink_len + min_gap)))
            
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            if actual_kinks * kink_len < total_len:
                gap = (total_len - actual_kinks * kink_len) / (actual_kinks + 1)
                s = 0.0
                for _ in range(actual_kinks):
                    # Добавляем промежуточные точки до излома
                    kink_start = s + gap
                    add_path_points(out, s, kink_start)
                    
                    # Точка перед изломом
                    x_end, y_end, _, _ = normal_at(kink_start)
                    out.extend([x_end, y_end])

                    # Рисуем излом
                    d1 = kink_start + kink_len * 0.25
                    d2 = kink_start + kink_len * 0.75
                    d3 = kink_start + kink_len

                    x1, y1, nx1, ny1 = normal_at(d1)
                    x2, y2, nx2, ny2 = normal_at(d2)
                    x3, y3, _, _ = normal_at(d3)

                    out.extend([
                        x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                        x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                        x3, y3
                    ])
                    s = d3

                # Добавляем оставшуюся часть пути
                if s < total_len:
                    add_path_points(out, s, total_len)
                    x_end, y_end, _, _ = normal_at(total_len)
                    out.extend([x_end, y_end])
                return out

        # Автоматический режим
        s = 0.0
        while s < total_len - 1e-6:
            next_s = min(s + period, total_len)
            
            # Добавляем промежуточные точки
            add_path_points(out, s, next_s)
            
            x_end, y_end, _, _ = normal_at(next_s)
            out.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= total_len:
                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, nx1, ny1 = normal_at(d1)
                x2, y2, nx2, ny2 = normal_at(d2)
                x3, y3, _, _ = normal_at(d3)

                out.extend([
                    x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                    x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                    x3, y3
                ])
                s = d3
            else:
                break
        return out

    def _generate_polyline_zigzag_coords_closed(self, coords, cum_lengths, kinks_count=None):
        """Стилизация замкнутого polyline зигзагом.
        
        Для замкнутых контуров изломы распределяются равномерно по всему периметру.
        
        Args:
            kinks_count: Количество изломов (из стиля).
        """
        if not coords:
            return []
        zoom = self.state.zoom
        period = 40 * (zoom / 5.0)
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        total_len = cum_lengths[-1] if cum_lengths else 0.0
        if total_len <= 0:
            return []

        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        path_step = max(4, total_len / MAX_POINTS)

        def normal_at(dist):
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, dist)
            norm_len = math.sqrt(dx * dx + dy * dy)
            nx, ny = (0.0, 0.0) if norm_len < 1e-9 else (-dy / norm_len, dx / norm_len)
            return x, y, nx, ny

        def add_path_points(out, start_s, end_s):
            """Добавляет промежуточные точки пути от start_s до end_s."""
            s = start_s + path_step
            while s < end_s - 1e-6:
                x, y, _, _ = normal_at(s)
                out.extend([x, y])
                s += path_step

        out = []
        x0, y0, _, _ = normal_at(0.0)
        first_point = (x0, y0)
        out.extend([x0, y0])

        # Фиксированное число изломов для замкнутого контура
        if kinks_count is not None and kinks_count >= 1:
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((total_len - min_gap) / (kink_len + min_gap)))
            
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            total_kinks_len = actual_kinks * kink_len
            if total_kinks_len < total_len:
                # Для замкнутого контура: N изломов = N промежутков
                gap = (total_len - total_kinks_len) / actual_kinks
                
                s = 0.0
                for _ in range(actual_kinks):
                    # Добавляем промежуточные точки до излома
                    kink_start = s + gap
                    add_path_points(out, s, kink_start)
                    
                    # Точка перед изломом
                    x_end, y_end, _, _ = normal_at(kink_start)
                    out.extend([x_end, y_end])

                    # Рисуем излом
                    d1 = kink_start + kink_len * 0.25
                    d2 = kink_start + kink_len * 0.75
                    d3 = kink_start + kink_len

                    x1, y1, nx1, ny1 = normal_at(d1)
                    x2, y2, nx2, ny2 = normal_at(d2)
                    x3, y3, _, _ = normal_at(d3)

                    out.extend([
                        x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                        x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                        x3, y3
                    ])
                    s = d3

                # Добавляем оставшуюся часть пути до замыкания
                if s < total_len:
                    add_path_points(out, s, total_len)
                
                # Замыкаем контур
                out.extend([first_point[0], first_point[1]])
                return out

        # Автоматический режим для замкнутого контура
        s = 0.0
        while s < total_len - kink_len - 1e-6:
            next_s = min(s + period, total_len - kink_len)
            
            # Добавляем промежуточные точки
            add_path_points(out, s, next_s)
            
            x_end, y_end, _, _ = normal_at(next_s)
            out.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= total_len - period * 0.5:
                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, nx1, ny1 = normal_at(d1)
                x2, y2, nx2, ny2 = normal_at(d2)
                x3, y3, _, _ = normal_at(d3)

                out.extend([
                    x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                    x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                    x3, y3
                ])
                s = d3
            else:
                break
        
        # Добавляем оставшуюся часть и замыкаем
        if s < total_len:
            add_path_points(out, s, total_len)
        out.extend([first_point[0], first_point[1]])
        
        return out

    def _generate_ellipse_zigzag_coords(self, coords, cum_lengths, kinks_count=None):
        """Генерация координат эллипса с изломами.
        
        Рисует базовый эллипс с заданным количеством изломов.
        Между изломами эллипс отрисовывается точками вдоль контура.
        
        Args:
            kinks_count: Количество изломов из стиля.
        """
        zoom = self.state.zoom
        kink_len = 8 * (zoom / 5.0)
        amplitude = 5 * (zoom / 5.0)

        total_len = cum_lengths[-1] if cum_lengths else 0.0
        if total_len <= 0:
            return []

        # Адаптивный шаг: ограничиваем максимум ~1000 точек
        MAX_POINTS = 1000
        path_step = max(4, total_len / MAX_POINTS)

        def normal_at(dist):
            x, y, dx, dy = self._point_on_polyline(coords, cum_lengths, dist)
            norm_len = math.sqrt(dx * dx + dy * dy)
            nx, ny = (0.0, 0.0) if norm_len < 1e-9 else (-dy / norm_len, dx / norm_len)
            return x, y, nx, ny

        def add_path_points(out, start_s, end_s):
            """Добавляет промежуточные точки контура от start_s до end_s."""
            s = start_s + path_step
            while s < end_s - 1e-6:
                x, y, _, _ = normal_at(s)
                out.extend([x, y])
                s += path_step

        out = []
        x0, y0, _, _ = normal_at(0.0)
        first_point = (x0, y0)
        out.extend([x0, y0])
        
        # Режим с фиксированным количеством изломов
        if kinks_count is not None and kinks_count >= 1:
            min_gap = kink_len * 0.5
            max_kinks = max(1, int((total_len - min_gap) / (kink_len + min_gap)))
            actual_kinks = min(kinks_count, max_kinks)
            actual_kinks = max(1, actual_kinks)
            
            total_kinks_len = actual_kinks * kink_len
            if total_kinks_len < total_len:
                gap = (total_len - total_kinks_len) / actual_kinks
                
                s = 0.0
                for _ in range(actual_kinks):
                    # Добавляем промежуточные точки до излома
                    kink_start = s + gap
                    add_path_points(out, s, kink_start)
                    
                    # Точка перед изломом
                    x_end, y_end, _, _ = normal_at(kink_start)
                    out.extend([x_end, y_end])
                    
                    # Рисуем излом
                    d1 = kink_start + kink_len * 0.25
                    d2 = kink_start + kink_len * 0.75
                    d3 = kink_start + kink_len
                    
                    x1, y1, nx1, ny1 = normal_at(d1)
                    x2, y2, nx2, ny2 = normal_at(d2)
                    x3, y3, _, _ = normal_at(d3)
                    
                    out.extend([
                        x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                        x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                        x3, y3
                    ])
                    s = d3
                
                # Добавляем оставшуюся часть контура
                add_path_points(out, s, total_len)
                
                # Замыкаем эллипс
                out.extend([first_point[0], first_point[1]])
                return out

        # Автоматический режим
        period = 40 * (zoom / 5.0)
        s = 0.0
        
        while s < total_len - kink_len - 1e-6:
            next_s = min(s + period, total_len - kink_len)
            
            # Добавляем промежуточные точки
            add_path_points(out, s, next_s)
            
            x_end, y_end, _, _ = normal_at(next_s)
            out.extend([x_end, y_end])
            s = next_s

            if s + kink_len <= total_len - period * 0.5:
                d1 = s + kink_len * 0.25
                d2 = s + kink_len * 0.75
                d3 = s + kink_len

                x1, y1, nx1, ny1 = normal_at(d1)
                x2, y2, nx2, ny2 = normal_at(d2)
                x3, y3, _, _ = normal_at(d3)

                out.extend([
                    x1 - nx1 * amplitude, y1 - ny1 * amplitude,
                    x2 + nx2 * amplitude, y2 + ny2 * amplitude,
                    x3, y3
                ])
                s = d3
            else:
                break

        # Замыкаем эллипс
        out.extend([first_point[0], first_point[1]])
        return out

    def draw_ellipse(self, ellipse, override_color=None, override_width=None):
        draw_color = override_color if override_color else ellipse.color
        style = self.state.line_styles.get(ellipse.style_name)

        line_width = 1
        dash_pattern = None
        base_type = 'solid'

        if style:
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
            line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))
            base_type = getattr(style, 'base_type', 'solid')
            if style.dash_pattern:
                main_dash, main_gap = style.dash_pattern
                if base_type == 'dash_dot_dot':
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base_type == 'dash_dot':
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    dash_pattern = [main_dash, main_gap]

        if override_width:
            line_width = override_width
            dash_pattern = None
            base_type = 'solid'

        coords, cum_lengths = self._ellipse_polyline(ellipse)
        if not coords:
            return

        flat_coords = []
        for x, y in coords:
            flat_coords.extend([x, y])

        if dash_pattern:
            # Рисуем вручную штриховые сегменты как у других примитивов
            scaled = [float(v) * self.state.zoom for v in dash_pattern]
            if not scaled:
                scaled = [4.0 * self.state.zoom, 4.0 * self.state.zoom]
            self._draw_dashed_polyline(coords, scaled, draw_color, line_width)
        elif base_type in ['wave', 'zigzag']:
            if base_type == 'wave':
                wave_amp = getattr(style, 'wave_amplitude', None)
                styled = self._generate_ellipse_wave_coords(coords, cum_lengths, wave_amplitude=wave_amp)
                smooth_flag = True
            else:
                kinks = getattr(style, 'kinks_count', None)
                styled = self._generate_ellipse_zigzag_coords(coords, cum_lengths, kinks_count=kinks)
                smooth_flag = False
            if len(styled) >= 4:
                self.canvas.create_line(*styled, fill=draw_color, width=line_width, smooth=smooth_flag)
        else:
            # smooth=False для производительности - точки уже плавно расположены по кривой
            self.canvas.create_line(*flat_coords, fill=draw_color, width=line_width, smooth=False)

    def _draw_dashed_polyline(self, coords, pattern, color, width):
        """Рисуем штриховой контур polyline по аналогии с отрезками/окружностями."""
        if len(coords) < 2:
            return
        pat = pattern
        pat_len = len(pat)
        pat_idx = 0
        remain_in_dash = pat[0] if pat_len else 0
        draw_on = True  # стартуем с рисования, как в сегментах

        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            dx, dy = x2 - x1, y2 - y1
            seg_len = math.sqrt(dx * dx + dy * dy)
            if seg_len < 1e-9:
                continue

            ux, uy = dx / seg_len, dy / seg_len
            dist_done = 0.0
            cx, cy = x1, y1

            while dist_done < seg_len - 1e-9:
                if remain_in_dash <= 1e-9:
                    pat_idx = (pat_idx + 1) % pat_len
                    remain_in_dash = pat[pat_idx]
                    draw_on = not draw_on

                step = min(remain_in_dash, seg_len - dist_done)
                nx = cx + ux * step
                ny = cy + uy * step

                if draw_on:
                    self.canvas.create_line(cx, cy, nx, ny, fill=color, width=width, capstyle=tk.ROUND)

                cx, cy = nx, ny
                dist_done += step
                remain_in_dash -= step

    def draw_point(self, point, size=4, color='black'):
        x, y = self.converter.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

    def draw_spline(self, spline, override_color=None, override_width=None):
        """Отрисовка сплайна с учетом стиля."""
        draw_color = override_color if override_color else spline.color
        style = self.state.line_styles.get(spline.style_name)

        line_width = 1
        dash_pattern = None
        base_type = 'solid'

        if style:
            s_px = self.state.base_thickness_mm * self.state.mm_to_px_ratio
            line_width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))
            base_type = getattr(style, 'base_type', 'solid')
            if style.dash_pattern:
                main_dash, main_gap = style.dash_pattern
                if base_type == 'dash_dot_dot':
                    part = main_gap / 5.0
                    dash_pattern = [main_dash, part, part, part, part, part]
                elif base_type == 'dash_dot':
                    part = main_gap / 3.0
                    dash_pattern = [main_dash, part, part, part]
                else:
                    dash_pattern = [main_dash, main_gap]

        if override_width:
            line_width = override_width
            dash_pattern = None
            base_type = 'solid'

        coords, cum_lengths = self._spline_polyline(spline)
        if len(coords) < 2:
            return

        if dash_pattern:
            scaled = [float(v) * self.state.zoom for v in dash_pattern]
            self._draw_dashed_polyline(coords, scaled, draw_color, line_width)
        elif base_type in ['wave', 'zigzag']:
            if base_type == 'wave':
                # Используем амплитуду из стиля
                wave_amp = getattr(style, 'wave_amplitude', None)
                styled = self._generate_polyline_wave_coords(coords, cum_lengths, wave_amplitude=wave_amp)
                smooth_flag = True
            else:
                # Используем количество изломов из стиля
                kinks = getattr(style, 'kinks_count', None)
                styled = self._generate_polyline_zigzag_coords(coords, cum_lengths, kinks_count=kinks)
                smooth_flag = False
            if len(styled) >= 4:
                self.canvas.create_line(*styled, fill=draw_color, width=line_width, smooth=smooth_flag)
        else:
            # smooth=False для производительности - точки уже плотно расположены вдоль кривой
            flat_coords = []
            for x, y in coords:
                flat_coords.extend([x, y])
            self.canvas.create_line(*flat_coords, fill=draw_color, width=line_width, smooth=False)

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
        # 5.2 Рисуем выделенные эллипсы
        for ellipse in self.state.selected_ellipses:
            self.draw_ellipse(ellipse, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))
        # 5.3 Рисуем выделенные многоугольники
        for poly in self.state.selected_polygons:
            self.draw_polygon(poly, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))
        # 5.4 Рисуем выделенные сплайны
        for spline in self.state.selected_splines:
            self.draw_spline(spline, override_color='#00FFFF', override_width=max(4, self.state.base_thickness_mm + 6))

        # 5. Рисуем все остальные сегменты (кроме выделенных)
        selected_segments_set = set(id(s) for s in self.state.selected_segments)
        for segment in self.state.segments:
            if id(segment) not in selected_segments_set:
                self.draw_segment(segment)

        # 6. Рисуем все остальные окружности (кроме выделенных)
        selected_circles_set = set(id(c) for c in self.state.selected_circles)
        for circle in self.state.circles:
            if id(circle) not in selected_circles_set:
                self.draw_circle(circle)

        # 7. Рисуем все дуги (кроме выделенных)
        selected_arcs_set = set(id(a) for a in self.state.selected_arcs)
        for arc in self.state.arcs:
            if id(arc) not in selected_arcs_set:
                self.draw_arc(arc)

        # 7.1 Рисуем все прямоугольники (кроме выделенных)
        selected_rects_set = set(id(r) for r in self.state.selected_rectangles)
        for rect in self.state.rectangles:
            if id(rect) not in selected_rects_set:
                self.draw_rectangle(rect)

        # 7.2 Рисуем все эллипсы (кроме выделенных)
        selected_ellipses_set = set(id(e) for e in self.state.selected_ellipses)
        for ellipse in self.state.ellipses:
            if id(ellipse) not in selected_ellipses_set:
                self.draw_ellipse(ellipse)

        # 7.3 Рисуем все многоугольники (кроме выделенных)
        selected_polygons_set = set(id(p) for p in self.state.selected_polygons)
        for poly in self.state.polygons:
            if id(poly) not in selected_polygons_set:
                self.draw_polygon(poly)

        # 7.4 Рисуем все сплайны (кроме выделенных)
        selected_splines_set = set(id(s) for s in self.state.selected_splines)
        for spline in self.state.splines:
            if id(spline) not in selected_splines_set:
                self.draw_spline(spline)

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

        # 10.2 Рисуем превью эллипса
        if self.state.preview_ellipse:
            self.draw_ellipse(self.state.preview_ellipse, override_color='blue')
        # 10.3 Рисуем превью многоугольника
        if self.state.preview_polygon:
            self.draw_polygon(self.state.preview_polygon, override_color='blue')
        # 10.4 Рисуем превью сплайна
        if self.state.preview_spline:
            self.draw_spline(self.state.preview_spline, override_color='blue')

        # 11. Рисуем активные точки (начало и конец текущего отрезка/окружности)
        if self.state.active_p1:
            self.draw_point(self.state.active_p1)
        if self.state.active_p2:
            self.draw_point(self.state.active_p2)
        if self.state.active_p3:
            self.draw_point(self.state.active_p3)
        if self.state.active_p4:
            self.draw_point(self.state.active_p4)
        
        # 12. Рисуем индикатор привязки
        if self.state.current_snap_point:
            self.draw_snap_indicator(self.state.current_snap_point)
    
    def draw_snap_indicator(self, snap_point):
        """Отрисовывает визуальный индикатор точки привязки."""
        # Конвертируем координаты в экранные
        sx, sy = self.converter.world_to_screen(snap_point.x, snap_point.y)
        
        # Размер индикатора
        size = 8
        
        # Цвета для разных типов привязок
        snap_colors = {
            SnapType.ENDPOINT: '#FF6600',      # Оранжевый - конец
            SnapType.MIDPOINT: '#00CC00',      # Зелёный - середина
            SnapType.CENTER: '#0066FF',        # Синий - центр
            SnapType.INTERSECTION: '#FF0000',  # Красный - пересечение
            SnapType.PERPENDICULAR: '#9900CC', # Фиолетовый - перпендикуляр
            SnapType.TANGENT: '#CC6600',       # Коричневый - касательная
            SnapType.NEAREST: '#666666',       # Серый - ближайшая
            SnapType.GRID: '#999999',          # Светло-серый - сетка
        }
        
        color = snap_colors.get(snap_point.snap_type, '#FF6600')
        line_width = 2
        
        # Рисуем разные маркеры в зависимости от типа привязки
        if snap_point.snap_type == SnapType.ENDPOINT:
            # Квадрат для концевой точки
            self.canvas.create_rectangle(
                sx - size, sy - size, sx + size, sy + size,
                outline=color, width=line_width, fill=''
            )
        
        elif snap_point.snap_type == SnapType.MIDPOINT:
            # Треугольник для середины
            self.canvas.create_polygon(
                sx, sy - size,
                sx - size, sy + size,
                sx + size, sy + size,
                outline=color, width=line_width, fill=''
            )
        
        elif snap_point.snap_type == SnapType.CENTER:
            # Круг для центра
            self.canvas.create_oval(
                sx - size, sy - size, sx + size, sy + size,
                outline=color, width=line_width, fill=''
            )
        
        elif snap_point.snap_type == SnapType.INTERSECTION:
            # Крестик для пересечения
            self.canvas.create_line(
                sx - size, sy - size, sx + size, sy + size,
                fill=color, width=line_width
            )
            self.canvas.create_line(
                sx - size, sy + size, sx + size, sy - size,
                fill=color, width=line_width
            )
        
        elif snap_point.snap_type == SnapType.PERPENDICULAR:
            # Перпендикуляр (угол 90°)
            self.canvas.create_line(
                sx - size, sy, sx, sy, fill=color, width=line_width
            )
            self.canvas.create_line(
                sx, sy, sx, sy - size, fill=color, width=line_width
            )
            self.canvas.create_rectangle(
                sx - size, sy - size, sx + size, sy + size,
                outline=color, width=1, fill=''
            )
        
        elif snap_point.snap_type == SnapType.TANGENT:
            # Ромб для касательной
            self.canvas.create_polygon(
                sx, sy - size,
                sx + size, sy,
                sx, sy + size,
                sx - size, sy,
                outline=color, width=line_width, fill=''
            )
        
        elif snap_point.snap_type == SnapType.GRID:
            # Плюс для сетки
            self.canvas.create_line(
                sx - size, sy, sx + size, sy,
                fill=color, width=line_width
            )
            self.canvas.create_line(
                sx, sy - size, sx, sy + size,
                fill=color, width=line_width
            )
        
        else:
            # По умолчанию - квадрат
            self.canvas.create_rectangle(
                sx - size, sy - size, sx + size, sy + size,
                outline=color, width=line_width, fill=''
            )