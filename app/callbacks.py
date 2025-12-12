# app/callbacks.py

'''
Этот файл решает, что делать, если пользователь нажал кнопку мыши, покрутил колесико или нажал "Enter". 
Он меняет данные в state и дает команду renderer перерисовать экран. 
Он связывает кнопки из main_window с действиями.
'''

import tkinter as tk
from tkinter import messagebox, colorchooser
import math
from logic.geometry import Point, Segment, Circle
from logic.converter import CoordinateConverter
from ui.renderer import Renderer
from logic.styles import GOST_STYLES
from ui.style_manager import StyleManagerWindow

class Callbacks:
    def __init__(self, root, state, view):
        self.root = root
        self.state = state
        self.view = view
        
        self.converter = None
        self.renderer = None
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    def initialize_view(self):
        self.converter = CoordinateConverter(self.state, self.view.canvas)
        self.renderer = Renderer(self.view.canvas, self.state, self.converter)
        
        self.view.canvas.config(background=self.state.bg_color)
        self.view.bg_swatch.config(background=self.state.bg_color)
        self.view.grid_swatch.config(background=self.state.grid_color)
        self.view.segment_swatch.config(background=self.state.current_color)
        
        # Инициализируем превью в панели свойств текущим стилем
        self.view.update_style_preview(self.state.current_style_name)

        # Инициализируем метод создания окружности
        self.view.circle_method.set(self.state.circle_creation_method)

        self.set_app_state(self.state.app_mode)

    def set_app_state(self, mode):
        self.state.app_mode = mode
        is_creating_segment = (mode == 'CREATING_SEGMENT')
        is_creating_circle = mode.startswith('CREATING_CIRCLE')
        is_creating = is_creating_segment or is_creating_circle
        is_panning = (mode == 'PANNING')

        entry_state = 'normal' if is_creating else 'disabled'
        entries = [self.view.p1_x_entry, self.view.p1_y_entry, self.view.p2_x_entry, self.view.p2_y_entry]

        # Поля окружностей
        circle_entries = [
            self.view.circle_center_x_entry, self.view.circle_center_y_entry,
            self.view.circle_param_entry, self.view.circle_p2_x_entry,
            self.view.circle_p2_y_entry, self.view.circle_p3_x_entry,
            self.view.circle_p3_y_entry
        ]

        self.view.canvas.unbind("<Button-1>")
        self.view.canvas.unbind("<B1-Motion>")
        self.view.canvas.unbind("<ButtonRelease-1>")
        self.view.canvas.config(cursor="")
        self.root.unbind("<Return>")

        if not is_creating:
            for entry in entries:
                entry.delete(0, tk.END)
                entry.config(state=entry_state)
            # Блокируем поля окружностей
            for entry in circle_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.active_p1 = None
            self.state.active_p2 = None
            self.state.active_p3 = None

        if is_creating or is_panning:
            self.view.hotkey_frame.pack(side=tk.RIGHT, padx=5)
            self.view.lbl_esc.pack(side=tk.LEFT, padx=5)
            if is_creating:
                self.view.lbl_enter.pack(side=tk.LEFT, padx=5)
            else:
                self.view.lbl_enter.pack_forget()
        else:
            self.view.hotkey_frame.pack_forget()

        if is_creating_segment:
            for entry in entries: entry.config(state=entry_state)
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_segment)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_circle:
            # Разблокируем поля отрезков (для совместимости)
            for entry in entries: entry.config(state=entry_state)
            # Разблокируем поля окружностей
            for entry in circle_entries: entry.config(state='normal')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_circle)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_circle)
            self.view.canvas.config(cursor="crosshair") 
            
        elif is_panning:
            self.view.canvas.bind("<Button-1>", self.on_mouse_press)
            self.view.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.view.canvas.config(cursor="fleur")

        else:
            # В режиме IDLE работает выделение
            self.view.canvas.bind("<Button-1>", self.on_selection_click)
            self.view.canvas.config(cursor="arrow")
        
        self.redraw_all()

    # --- ЛОГИКА ВЫДЕЛЕНИЯ ---

    def on_selection_click(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        hit_threshold_pixels = 8
        hit_threshold_world = hit_threshold_pixels / self.state.zoom

        found_segment = None
        found_circle = None

        # Ищем сегменты
        for segment in self.state.segments:
            dist = segment.distance_to_point(wx, wy)
            if dist < hit_threshold_world:
                found_segment = segment
                break

        # Ищем окружности
        if not found_segment:  # Приоритет сегментам
            for circle in self.state.circles:
                dist = circle.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_circle = circle
                    break

        # Проверка нажатия Ctrl (бит 0x0004)
        ctrl_pressed = (event.state & 0x0004)

        if found_segment:
            if ctrl_pressed:
                # Если Ctrl зажат - добавляем или убираем из списка
                if found_segment in self.state.selected_segments:
                    self.state.selected_segments.remove(found_segment)
                else:
                    self.state.selected_segments.append(found_segment)
                # Очищаем выделение окружностей при выборе сегмента
                self.state.selected_circles = []
            else:
                # Если Ctrl НЕ зажат - выбираем только этот (сброс остальных)
                self.state.selected_segments = [found_segment]
                self.state.selected_circles = []
        elif found_circle:
            if ctrl_pressed:
                # Если Ctrl зажат - добавляем или убираем из списка
                if found_circle in self.state.selected_circles:
                    self.state.selected_circles.remove(found_circle)
                else:
                    self.state.selected_circles.append(found_circle)
                # Очищаем выделение сегментов при выборе окружности
                self.state.selected_segments = []
            else:
                # Если Ctrl НЕ зажат - выбираем только этот (сброс остальных)
                self.state.selected_segments = []
                self.state.selected_circles = [found_circle]
        else:
            # Если клик в пустоту и Ctrl НЕ зажат - сбрасываем всё
            if not ctrl_pressed:
                self.state.selected_segments = []
                self.state.selected_circles = []

        # Синхронизируем UI (список стилей, превью) с тем, что мы выделили
        self._sync_ui_with_selection()
        self.redraw_all()

    def _sync_ui_with_selection(self):
        """Обновляет панель свойств в зависимости от выделения."""
        self.view.kinks_frame.pack_forget()

        sel_segments = self.state.selected_segments
        sel_circles = self.state.selected_circles

        # Если ничего не выделено
        if not sel_segments and not sel_circles:
            style_obj = GOST_STYLES.get(self.state.current_style_name)
            if style_obj:
                self.view.set_style_selection(style_obj.name)
                self.view.segment_swatch.config(bg=self.state.current_color)
            return

        # Определяем, что выделено
        if sel_segments and not sel_circles:
            # Выделены только сегменты
            self._sync_ui_with_segments(sel_segments)
        elif sel_circles and not sel_segments:
            # Выделены только окружности
            self._sync_ui_with_circles(sel_circles)
        else:
            # Смешанное выделение - показываем "Разные"
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_segments(self, sel_segments):
        """Синхронизация UI с выделенными сегментами."""
        unique_styles = {seg.style_name for seg in sel_segments}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_segments[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color

            # --- ЛОГИКА ОТОБРАЖЕНИЯ ПАНЕЛИ ИЗЛОМОВ/ВОЛН ---
            style = self.state.line_styles.get(style_name)
            base_type = getattr(style, 'base_type', 'solid')

            # Если это ЗИГЗАГ или ВОЛНА и выделен ОДИН объект
            if base_type in ['zigzag', 'wave'] and len(sel_segments) == 1:
                seg = sel_segments[0]
                self.view.kinks_frame.pack(fill=tk.X, padx=5, pady=5, after=self.view.style_combobox)

                # Меняем текст лейбла в зависимости от типа
                if base_type == 'zigzag':
                    self.view.lbl_kinks.config(text="Кол-во изломов:")
                    current_val = seg.kinks_count
                else:
                    self.view.lbl_kinks.config(text="Кол-во волн:")
                    current_val = seg.waves_count

                if current_val:
                    self.view.kinks_var.set(str(current_val))
                else:
                    # РАСЧЕТ ДЕФОЛТА
                    zoom = self.state.zoom
                    seg_len_px = seg.length * zoom

                    if base_type == 'zigzag':
                        # Period(40) + Kink(6) = 46 (при зуме 5.0)
                        # Реальная длина: (40 + 6) * (zoom / 5.0)
                        unit_len = 46 * (zoom / 5.0)
                    else: # wave
                        # Freq = 0.2 / (zoom/5.0). Period T = 2*pi / freq
                        # T = 2*pi / (0.2 / scale) = 10*pi * scale
                        # 10 * 3.14 = 31.4 * scale
                        unit_len = 31.4159 * (zoom / 5.0)

                    if unit_len > 0.1:
                        default_count = int(seg_len_px / unit_len)
                    else:
                        default_count = 1

                    self.view.kinks_var.set(str(default_count))
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_circles(self, sel_circles):
        """Синхронизация UI с выделенными окружностями."""
        unique_styles = {circle.style_name for circle in sel_circles}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_circles[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    # Изменение количества изломов или волн
    def on_kinks_changed(self, event=None):
        if not self.state.selected_segments: return
        seg = self.state.selected_segments[0]
        
        # Определяем тип текущей линии
        style = self.state.line_styles.get(seg.style_name)
        base_type = getattr(style, 'base_type', 'solid')
        
        try:
            val_str = self.view.kinks_var.get()
            if not val_str: 
                if base_type == 'zigzag': seg.kinks_count = None
                else: seg.waves_count = None
                self.redraw_all()
                return
                
            val = int(val_str)
            zoom = self.state.zoom
            seg_len_px = seg.length * zoom
            
            # Считаем минимально возможную длину элемента (чтобы не зависло)
            if base_type == 'zigzag':
                # Минимум - только сам излом (6) без пробелов
                min_unit = 8 * (zoom / 5.0)
            else:
                # Минимум - хотя бы 2 пикселя на волну
                min_unit = 2
            
            # Максимум сколько влезет
            max_n = int(seg_len_px / min_unit)
            if max_n < 1: max_n = 1
            
            # Ограничиваем
            if val < 1: val = 1
            if val > max_n: val = max_n
            
            # Сохраняем
            if base_type == 'zigzag': seg.kinks_count = val
            else: seg.waves_count = val
            
            if event and (event.keysym == 'Return' or event.type == 'VirtualEvent'): 
                 self.view.kinks_var.set(str(val))
            
            self.redraw_all()
            
        except ValueError:
            pass

    def on_style_selected(self, event=None):
        # Получаем индекс выбранного элемента
        idx = self.view.style_combobox.current()
        
        # Если индекс -1, значит ничего не выбрано или текст введен вручную (например "Разные")
        if idx == -1:
            return 

        # Берем ID стиля напрямую из списка ключей View
        try:
            new_style_name = self.view.style_ids[idx]
        except IndexError:
            return # На всякий случай

        self.state.current_style_name = new_style_name

        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                seg.style_name = new_style_name
        elif self.state.selected_circles:
            for circle in self.state.selected_circles:
                circle.style_name = new_style_name

        self._sync_ui_with_selection()

        self.update_preview_segment()
        self.update_preview_circle()
        self.redraw_all()

    # --- СТАНДАРТНЫЕ МЕТОДЫ ---

    def on_new_segment_mode(self, event=None):
        self.set_app_state('CREATING_SEGMENT')
        self.view.settings_notebook.select(1)  # Переключаемся на вкладку "Отрезки"

        # Очищаем поля отрезков
        self.view.p1_x_entry.delete(0, tk.END)
        self.view.p1_y_entry.delete(0, tk.END)
        self.view.p2_x_entry.delete(0, tk.END)
        self.view.p2_y_entry.delete(0, tk.END)

        self.view.p1_x_entry.focus_set()

    def on_new_circle_mode(self, event=None):
        self.set_app_state('CREATING_CIRCLE')
        self.view.settings_notebook.select(2)  # Переключаемся на вкладку "Окружности"

        # Очищаем поля окружностей
        self.view.circle_center_x_entry.delete(0, tk.END)
        self.view.circle_center_y_entry.delete(0, tk.END)
        self.view.circle_param_entry.delete(0, tk.END)
        self.view.circle_p2_x_entry.delete(0, tk.END)
        self.view.circle_p2_y_entry.delete(0, tk.END)
        self.view.circle_p3_x_entry.delete(0, tk.END)
        self.view.circle_p3_y_entry.delete(0, tk.END)

        # Для методов центр+радиус/диаметр фокус на центр
        method = self.state.circle_creation_method
        if method in ['center_radius', 'center_diameter']:
            self.view.circle_center_x_entry.focus_set()
        else:
            self.view.circle_center_x_entry.focus_set()

    def on_hand_mode(self, event=None):
        self.set_app_state('PANNING')
        self.view.canvas.focus_set()

    def update_preview_segment(self, event=None):
        try:
            p1, p2 = self._create_points_from_entries()
            self.state.preview_segment = Segment(
                p1, p2,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
        except (ValueError, tk.TclError):
            self.state.preview_segment = None
        self.redraw_all()

    def update_preview_circle(self, event=None):
        try:
            method = self.state.circle_creation_method
            if method == 'center_radius':
                # Центр и радиус
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                center = Point(center_x, center_y)
                radius = float(self.view.circle_param_entry.get())
                self.state.preview_circle = Circle.from_center_radius(
                    center, radius,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            elif method == 'center_diameter':
                # Центр и диаметр
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                center = Point(center_x, center_y)
                diameter = float(self.view.circle_param_entry.get())
                self.state.preview_circle = Circle.from_center_diameter(
                    center, diameter,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            elif method == 'two_points':
                # Две точки (диаметр)
                p1_x = float(self.view.circle_center_x_entry.get())
                p1_y = float(self.view.circle_center_y_entry.get())
                p1 = Point(p1_x, p1_y)
                p2_x = float(self.view.circle_p2_x_entry.get())
                p2_y = float(self.view.circle_p2_y_entry.get())
                p2 = Point(p2_x, p2_y)
                self.state.preview_circle = Circle.from_two_points(
                    p1, p2,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            elif method == 'three_points':
                # Три точки на окружности
                p1_x = float(self.view.circle_center_x_entry.get())
                p1_y = float(self.view.circle_center_y_entry.get())
                p1 = Point(p1_x, p1_y)
                p2_x = float(self.view.circle_p2_x_entry.get())
                p2_y = float(self.view.circle_p2_y_entry.get())
                p2 = Point(p2_x, p2_y)
                p3_x = float(self.view.circle_p3_x_entry.get())
                p3_y = float(self.view.circle_p3_y_entry.get())
                p3 = Point(p3_x, p3_y)
                self.state.preview_circle = Circle.from_three_points(
                    p1, p2, p3,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
        except (ValueError, tk.TclError):
            self.state.preview_circle = None
        self.redraw_all()

    def finalize_segment(self, event=None):
        if self.state.preview_segment:
            final_segment = Segment(
                self.state.preview_segment.p1,
                self.state.preview_segment.p2,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.state.segments.append(final_segment)
            self.set_app_state('IDLE')

    def finalize_circle(self, event=None):
        if self.state.preview_circle:
            final_circle = Circle(
                self.state.preview_circle.center,
                self.state.preview_circle.radius,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.state.circles.append(final_circle)
            self.set_app_state('IDLE')

    def on_escape_key(self, event=None):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_CIRCLE', 'PANNING']:
            self.set_app_state('IDLE')
        elif self.state.selected_segments or self.state.selected_circles:
            # Если есть выделение - снимаем его
            self.state.selected_segments = []
            self.state.selected_circles = []
            self._sync_ui_with_selection()
            self.redraw_all()
        elif self.state.app_mode == 'IDLE' and messagebox.askyesno("Выход", "Выйти из программы?"):
            self.root.destroy()

    def on_delete_segment(self, event=None):
        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                if seg in self.state.segments:
                    self.state.segments.remove(seg)
            self.state.selected_segments = []
        elif self.state.selected_circles:
            for circle in self.state.selected_circles:
                if circle in self.state.circles:
                    self.state.circles.remove(circle)
            self.state.selected_circles = []
        elif self.state.segments:
            self.state.segments.pop()
        elif self.state.circles:
            self.state.circles.pop()

        self._sync_ui_with_selection()
        self.redraw_all()

    def on_apply_settings(self):
        try:
            new_step = int(self.view.grid_step_var.get())
            if new_step <= 0: raise ValueError
            self.state.grid_step = new_step
            self.redraw_all()
        except ValueError: messagebox.showerror("Ошибка", "Шаг сетки должен быть > 0")

    def on_coord_system_change(self):
        new_system = self.view.coord_system.get()
        self.view.p2_label1.config(text="R₂:" if new_system == 'polar' else "X₂:")
        self.view.p2_label2.config(text="θ₂:" if new_system == 'polar' else "Y₂:")
        try:
            val1 = float(self.view.p2_x_entry.get())
            val2 = float(self.view.p2_y_entry.get())
            try: p1_x, p1_y = float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get())
            except ValueError: p1_x, p1_y = 0.0, 0.0
            p2 = Point()
            if new_system == 'cartesian':
                angle = math.radians(val2) if self.view.angle_units.get() == 'degrees' else val2
                p2.x = p1_x + val1 * math.cos(angle)
                p2.y = p1_y + val1 * math.sin(angle)
            else:
                p2 = Point(val1, val2)
        except (ValueError, tk.TclError): return
        self._update_p2_entries(p2)
        self.redraw_all()

    def on_lmb_click(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            self._update_p2_entries(Point(wx, wy))
            self.state.points_clicked = 2
        self.update_preview_segment()

    def on_lmb_click_circle(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        method = self.state.circle_creation_method

        if method in ['center_radius', 'center_diameter']:
            # Для методов центр+радиус/диаметр нужны 2 клика: центр и радиус/диаметр
            if self.state.points_clicked == 0:
                # Первый клик - центр
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                # Второй клик - определяем радиус/диаметр
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                distance = math.sqrt((wx - center_x)**2 + (wy - center_y)**2)
                if method == 'center_radius':
                    value = distance
                else:  # center_diameter
                    value = distance * 2
                self.view.circle_param_entry.delete(0, tk.END)
                self.view.circle_param_entry.insert(0, f"{value:.2f}")
                self.state.points_clicked = 2
        elif method == 'two_points':
            # Для метода две точки нужны 2 клика
            if self.state.points_clicked == 0:
                # Первый клик - первая точка (центр в терминах интерфейса)
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                # Второй клик - вторая точка
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
        elif method == 'three_points':
            # Для метода три точки нужны 3 клика
            if self.state.points_clicked == 0:
                # Первый клик - первая точка
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                # Второй клик - вторая точка
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
            elif self.state.points_clicked == 2:
                # Третий клик - третья точка
                self.view.circle_p3_x_entry.delete(0, tk.END)
                self.view.circle_p3_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p3_y_entry.delete(0, tk.END)
                self.view.circle_p3_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 3

        self.update_preview_circle()

    def on_rmb_click(self, event):
        if self.view.p2_x_entry.get():
            self.view.p2_x_entry.delete(0, tk.END); self.view.p2_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.p1_x_entry.get():
            self.view.p1_x_entry.delete(0, tk.END); self.view.p1_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_segment()

    def on_rmb_click_circle(self, event):
        """ПКМ для удаления точек при создании окружностей"""
        method = self.state.circle_creation_method

        if method in ['center_radius', 'center_diameter']:
            # Для центр+параметр: сначала очищаем параметр, потом центр
            if self.view.circle_param_entry.get():
                self.view.circle_param_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.circle_center_x_entry.get():
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'two_points':
            # Для двух точек: сначала P2, потом P1
            if self.view.circle_p2_x_entry.get():
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.circle_center_x_entry.get():
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'three_points':
            # Для трех точек: P3 -> P2 -> P1
            if self.view.circle_p3_x_entry.get():
                self.view.circle_p3_x_entry.delete(0, tk.END)
                self.view.circle_p3_y_entry.delete(0, tk.END)
                self.state.points_clicked = 2
            elif self.view.circle_p2_x_entry.get():
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.circle_center_x_entry.get():
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0

        self.update_preview_circle()

    def on_mouse_press(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y

    def on_mouse_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.state.pan_x += dx; self.state.pan_y += dy
        self._drag_start_x, self._drag_start_y = event.x, event.y
        self.redraw_all()

    def _perform_zoom(self, factor, center_screen_x, center_screen_y):
        wx, wy = self.converter.screen_to_world(center_screen_x, center_screen_y)
        self.state.zoom = max(0.1, min(self.state.zoom * factor, 1000.0))
        sx_new, sy_new = self.converter.world_to_screen(wx, wy)
        self.state.pan_x += center_screen_x - sx_new
        self.state.pan_y += center_screen_y - sy_new
        self.redraw_all()

    def on_mouse_wheel(self, event):
        factor = 1.2 if (hasattr(event, 'delta') and event.delta > 0) or event.num == 4 else 1/1.2
        self._perform_zoom(factor, event.x, event.y)

    def on_zoom_in(self, event=None):
        cx, cy = self.view.canvas.winfo_width() / 2, self.view.canvas.winfo_height() / 2
        self._perform_zoom(1.2, cx, cy)
        self.view.canvas.focus_set()

    def on_zoom_out(self, event=None):
        cx, cy = self.view.canvas.winfo_width() / 2, self.view.canvas.winfo_height() / 2
        self._perform_zoom(1/1.2, cx, cy)
        self.view.canvas.focus_set()

    def on_fit_to_view(self, event=None):
        all_objects = self.state.segments + self.state.circles
        if not all_objects:
            self.state.pan_x, self.state.pan_y = 0, 0
            self.state.zoom = 10.0
            self.redraw_all()
            self.view.canvas.focus_set()
            return

        xs, ys = [], []

        # Собираем координаты из сегментов
        for seg in self.state.segments:
            xs.extend([seg.p1.x, seg.p2.x])
            ys.extend([seg.p1.y, seg.p2.y])

        # Собираем координаты из окружностей (центр ± радиус)
        for circle in self.state.circles:
            xs.extend([circle.center.x - circle.radius, circle.center.x + circle.radius])
            ys.extend([circle.center.y - circle.radius, circle.center.y + circle.radius])

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        world_w = max_x - min_x
        world_h = max_y - min_y
        center_wx = (min_x + max_x) / 2
        center_wy = (min_y + max_y) / 2
        screen_w = self.view.canvas.winfo_width() * 0.9
        screen_h = self.view.canvas.winfo_height() * 0.9
        if world_w == 0: world_w = 1
        if world_h == 0: world_h = 1
        scale_x = screen_w / world_w
        scale_y = screen_h / world_h
        self.state.zoom = min(scale_x, scale_y)
        self.state.pan_x = -center_wx * self.state.zoom
        self.state.pan_y = center_wy * self.state.zoom
        self.redraw_all()
        self.view.canvas.focus_set()

    def rotate_view(self, angle_delta_deg, event=None):
        is_shift = False
        if event and (event.state & 0x0001): 
            is_shift = True
        if is_shift:
            current_deg = math.degrees(self.state.rotation)
            snapped_deg = round(current_deg / 90) * 90
            if abs(snapped_deg - current_deg) < 1.0:
                target_deg = snapped_deg + (90 if angle_delta_deg > 0 else -90)
            else:
                target_deg = snapped_deg
            self.state.rotation = math.radians(target_deg)
        else:
            self.state.rotation += math.radians(angle_delta_deg)
        self.redraw_all()
        self.view.canvas.focus_set()

    def on_rotate_left(self, event=None): self.rotate_view(1, event)
    def on_rotate_right(self, event=None): self.rotate_view(-1, event)
    def on_canvas_resize(self, event): self.redraw_all()
    
    def toggle_fullscreen(self, event=None):
        self.state.is_fullscreen = not self.state.is_fullscreen
        self.root.attributes("-fullscreen", self.state.is_fullscreen)

    def on_choose_bg_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.bg_color)
        if c: 
            self.state.bg_color = c
            self.view.canvas.config(bg=c); self.view.bg_swatch.config(bg=c)

    def on_choose_grid_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.grid_color)
        if c: self.state.grid_color = c; self.view.grid_swatch.config(bg=c); self.redraw_all()

    def on_choose_segment_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.current_color)
        if c:
            self.state.current_color = c
            self.view.segment_swatch.config(bg=c)
            for seg in self.state.selected_segments:
                seg.color = c
            for circle in self.state.selected_circles:
                circle.color = c
            self.redraw_all()

    def _create_points_from_entries(self):
        p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
        val1, val2 = float(self.view.p2_x_entry.get()), float(self.view.p2_y_entry.get())
        p2 = Point()
        if self.view.coord_system.get() == 'cartesian': p2 = Point(val1, val2)
        else:
            angle = math.radians(val2) if self.view.angle_units.get() == 'degrees' else val2
            p2.x = p1.x + val1 * math.cos(angle)
            p2.y = p1.y + val1 * math.sin(angle)
        return p1, p2

    def _update_p1_entries(self, x, y):
        self.view.p1_x_entry.delete(0, tk.END); self.view.p1_x_entry.insert(0, f"{x:.2f}")
        self.view.p1_y_entry.delete(0, tk.END); self.view.p1_y_entry.insert(0, f"{y:.2f}")

    def _update_p2_entries(self, p2):
        is_polar = (self.view.coord_system.get() == 'polar')
        if is_polar:
            try: p1_x, p1_y = float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get())
            except ValueError: p1_x, p1_y = 0.0, 0.0
            r = math.sqrt((p2.x - p1_x)**2 + (p2.y - p1_y)**2)
            theta = math.atan2(p2.y - p1_y, p2.x - p1_x)
            if self.view.angle_units.get() == 'degrees': theta = math.degrees(theta)
            vals = [r, theta]
        else: vals = [p2.x, p2.y]
        
        for entry, v in zip([self.view.p2_x_entry, self.view.p2_y_entry], vals):
            entry.config(state='normal'); entry.delete(0, tk.END); entry.insert(0, f"{v:.2f}")
            if self.state.app_mode == 'IDLE': entry.config(state='disabled')

    def redraw_all(self):
        self.update_info_panel()
        self.update_status_bar()
        if self.renderer:
            self.renderer.render_scene()
    
    def update_info_panel(self):
        # Сбрасываем активные точки (по умолчанию ничего не рисуем)
        self.state.active_p1, self.state.active_p2, self.state.active_p3 = None, None, None

        # ПРИОРИТЕТ 1: РЕЖИМ СОЗДАНИЯ
        # Если мы строим отрезок или окружность, нам важно видеть именно ЕГО точки и размеры
        if self.state.app_mode == 'CREATING_SEGMENT':
            try: self.state.active_p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
            except (ValueError, tk.TclError): pass
            try:
                p1_for_p2, self.state.active_p2 = self._create_points_from_entries()
                if self.state.active_p1 is None: self.state.active_p1 = p1_for_p2
            except (ValueError, tk.TclError): pass
            
            # Обновляем текст для создаваемого отрезка
            p1, p2 = self.state.active_p1, self.state.active_p2

            if p1: self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
            else: self.view.p1_coord_var.set("P1: N/A")

            if p2:
                if self.view.coord_system.get() == 'polar':
                    dx = p2.x - (p1.x if p1 else 0)
                    dy = p2.y - (p1.y if p1 else 0)
                    r = math.sqrt(dx**2 + dy**2)
                    theta = math.atan2(dy, dx)
                    unit = self.view.angle_units.get()
                    sym = "°" if unit == 'degrees' else " rad"
                    if unit == 'degrees': theta = math.degrees(theta)
                    self.view.p2_coord_var.set(f"P2(r={r:.2f}, θ={theta:.2f}{sym})")
                else: self.view.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
            else: self.view.p2_coord_var.set("P2: N/A")

            if p1 and p2:
                seg = Segment(p1, p2)
                self.view.length_var.set(f"Длина: {seg.length:.2f}")
                angle = seg.angle
                val = math.degrees(angle) if self.view.angle_units.get() == 'degrees' else angle
                sym = "°" if self.view.angle_units.get() == 'degrees' else " rad"
                self.view.angle_var.set(f"Угол: {val:.2f}{sym}")
            else:
                self.view.length_var.set("Длина: N/A"); self.view.angle_var.set("Угол: N/A")

            return # Выходим, чтобы не перетереть данные выделением

        # ПРИОРИТЕТ 1.5: РЕЖИМ СОЗДАНИЯ ОКРУЖНОСТИ
        if self.state.app_mode == 'CREATING_CIRCLE':
            method = self.state.circle_creation_method

            # Получаем точки из соответствующих полей в зависимости от метода
            try:
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                self.state.active_p1 = Point(center_x, center_y)
            except (ValueError, tk.TclError):
                self.state.active_p1 = None

            if method in ['two_points', 'three_points']:
                try:
                    p2_x = float(self.view.circle_p2_x_entry.get())
                    p2_y = float(self.view.circle_p2_y_entry.get())
                    self.state.active_p2 = Point(p2_x, p2_y)
                except (ValueError, tk.TclError):
                    self.state.active_p2 = None

            if method == 'three_points':
                try:
                    p3_x = float(self.view.circle_p3_x_entry.get())
                    p3_y = float(self.view.circle_p3_y_entry.get())
                    self.state.active_p3 = Point(p3_x, p3_y)
                except (ValueError, tk.TclError):
                    self.state.active_p3 = None
            else:
                self.state.active_p3 = None

            # Обновляем текст для создаваемой окружности
            p1, p2, p3 = self.state.active_p1, self.state.active_p2, self.state.active_p3

            if method == 'center_radius':
                if p1:
                    self.view.p1_coord_var.set(f"Центр({p1.x:.2f}, {p1.y:.2f})")
                    try:
                        radius = float(self.view.circle_param_entry.get())
                        self.view.p2_coord_var.set(f"Радиус: {radius:.2f}")
                        self.view.length_var.set(f"Диаметр: {radius*2:.2f}")
                    except (ValueError, tk.TclError):
                        self.view.p2_coord_var.set("Радиус: N/A")
                        self.view.length_var.set("Диаметр: N/A")
                else:
                    self.view.p1_coord_var.set("Центр: N/A")
                    self.view.p2_coord_var.set("Радиус: N/A")
                    self.view.length_var.set("Диаметр: N/A")
                self.view.angle_var.set("Окружность")
            elif method == 'center_diameter':
                if p1:
                    self.view.p1_coord_var.set(f"Центр({p1.x:.2f}, {p1.y:.2f})")
                    try:
                        diameter = float(self.view.circle_param_entry.get())
                        self.view.p2_coord_var.set(f"Диаметр: {diameter:.2f}")
                        self.view.length_var.set(f"Радиус: {diameter/2:.2f}")
                    except (ValueError, tk.TclError):
                        self.view.p2_coord_var.set("Диаметр: N/A")
                        self.view.length_var.set("Радиус: N/A")
                else:
                    self.view.p1_coord_var.set("Центр: N/A")
                    self.view.p2_coord_var.set("Диаметр: N/A")
                    self.view.length_var.set("Радиус: N/A")
                self.view.angle_var.set("Окружность")
            elif method == 'two_points':
                if p1: self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
                else: self.view.p1_coord_var.set("P1: N/A")

                if p2: self.view.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
                else: self.view.p2_coord_var.set("P2: N/A")

                self.view.length_var.set("Радиус: N/A")
                self.view.angle_var.set("Окружность")
            elif method == 'three_points':
                if p1: self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
                else: self.view.p1_coord_var.set("P1: N/A")

                if p2: self.view.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
                else: self.view.p2_coord_var.set("P2: N/A")

                if p3: self.view.p3_coord_var.set(f"P3({p3.x:.2f}, {p3.y:.2f})")
                else: self.view.p3_coord_var.set("P3: N/A")

                self.view.length_var.set("Радиус: N/A")
                self.view.angle_var.set("Окружность")

            return # Выходим, чтобы не перетереть данные выделением

        # ПРИОРИТЕТ 2: ВЫДЕЛЕНИЕ
        # Если мы НЕ строим, но что-то выделено
        if self.state.selected_segments:
            seg = self.state.selected_segments[0]

            # ОБНОВЛЕНИЕ ТЕКСТА
            self.view.p1_coord_var.set(f"P1({seg.p1.x:.2f}, {seg.p1.y:.2f})")
            self.view.p2_coord_var.set(f"P2({seg.p2.x:.2f}, {seg.p2.y:.2f})")
            self.view.length_var.set(f"Длина: {seg.length:.2f}")

            angle = seg.angle
            if self.view.angle_units.get() == 'degrees':
                val = math.degrees(angle)
                sym = "°"
            else:
                val = angle
                sym = " rad"
            self.view.angle_var.set(f"Угол: {val:.2f}{sym}")

            # ВАЖНО: Мы НЕ устанавливаем self.state.active_p1/p2
            # Поэтому точки на краях выделенного отрезка рисоваться НЕ БУДУТ.
            return

        # ПРИОРИТЕТ 2.5: ВЫДЕЛЕНИЕ ОКРУЖНОСТИ
        if self.state.selected_circles:
            circle = self.state.selected_circles[0]

            # ОБНОВЛЕНИЕ ТЕКСТА
            self.view.p1_coord_var.set(f"Центр({circle.center.x:.2f}, {circle.center.y:.2f})")
            self.view.p2_coord_var.set(f"Радиус: {circle.radius:.2f}")
            self.view.length_var.set(f"Диаметр: {circle.diameter:.2f}")
            self.view.angle_var.set("Окружность")

            return 

        # ПРИОРИТЕТ 3: ПУСТОТА
        self.view.length_var.set("Длина: N/A")
        self.view.angle_var.set("Угол: N/A")
        self.view.p1_coord_var.set("P1: N/A")
        self.view.p2_coord_var.set("P2: N/A")

    def on_reset_view(self, event=None):
        self.state.pan_x = 0
        self.state.pan_y = 0
        self.state.zoom = 10.0 
        self.state.rotation = 0.0
        self.redraw_all()
        self.view.canvas.focus_set()

    def on_mouse_move_stats(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        self.view.status_coords.config(text=f"X: {wx:.2f}  Y: {wy:.2f}")

    def update_status_bar(self):
        zoom_pct = int((self.state.zoom / 10.0) * 100)
        self.view.status_zoom.config(text=f"Zoom: {zoom_pct}%")
        deg = math.degrees(self.state.rotation)
        self.view.status_angle.config(text=f"Angle: {deg:.1f}°")

        total_selected = len(self.state.selected_segments) + len(self.state.selected_circles)
        if total_selected > 0:
             mode_text = f"Выбрано объектов: {total_selected}"
        else:
            modes = {'IDLE': "Ожидание", 'CREATING_SEGMENT': "Создание отрезка", 'CREATING_CIRCLE': "Создание окружности", 'PANNING': "Панорамирование"}
            mode_text = modes.get(self.state.app_mode, self.state.app_mode)

        self.view.status_mode.config(text=f"Режим: {mode_text}")

    def show_context_menu(self, event):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_CIRCLE']:
            self.on_rmb_click_circle(event)
        else:
            self.view.context_menu.post(event.x_root, event.y_root)

    # Вызывается, когда в Менеджере нажали "Применить"
    def on_styles_updated(self):
        # 1. Обновляем список в главном окне (чтобы появился новый стиль)
        self.view.refresh_style_combobox_values(self.state.line_styles)
        
        # 2. Перерисовываем холст
        self.redraw_all()
        
        # 3. Синхронизируем панель свойств (если вдруг удалили текущий стиль)
        self._sync_ui_with_selection()

    # Метод открытия окна
    def on_open_style_manager(self):
        # Передаем НЕ redraw_all, а наш новый метод
        StyleManagerWindow(self.root, self.state, self.on_styles_updated)

    # Обработка кнопок быстрого доступа
    def on_quick_style_set(self, style_key):
        # Проверяем, есть ли такой стиль вообще (вдруг удалили)
        if style_key not in self.state.line_styles:
            return

        self.state.current_style_name = style_key
        
        # Если есть выделенные объекты -> меняем стиль им всем
        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                seg.style_name = style_key
            # Синхронизируем UI (Combobox и превью обновятся сами)
            self._sync_ui_with_selection()
        else:
            # Если нет выделения -> просто обновляем UI для будущего рисования
            self.view.set_style_selection(style_key)

        self.update_preview_segment()
        self.redraw_all()