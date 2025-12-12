# app/callbacks.py

'''
Этот файл решает, что делать, если пользователь нажал кнопку мыши, покрутил колесико или нажал "Enter". 
Он меняет данные в state и дает команду renderer перерисовать экран. 
Он связывает кнопки из main_window с действиями.
'''

import tkinter as tk
from tkinter import messagebox, colorchooser
import math
from logic.geometry import Point, Segment, Circle, Arc, Rectangle, Ellipse, RegularPolygon, Spline
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
        # Инициализируем метод создания дуги
        self.view.arc_method.set(self.state.arc_creation_method)
        self.view._update_arc_params_ui()
        # Инициализируем метод создания прямоугольника
        self.view.rect_method.set(self.state.rectangle_creation_method)
        self.view.rect_corner_type.set(self.state.rectangle_corner_type)
        self.view.rect_corner_value_entry.delete(0, tk.END)
        if self.state.rectangle_corner_value:
            self.view.rect_corner_value_entry.insert(0, f"{self.state.rectangle_corner_value:.2f}")
        self.view._update_rectangle_params_ui()
        # Инициализируем метод создания эллипса
        self.view.ellipse_method.set(self.state.ellipse_creation_method)
        # Инициализируем параметры многоугольника
        self.view.polygon_method.set(self.state.polygon_creation_method)
        self.view.polygon_variant.set(self.state.polygon_variant)
        self.view.polygon_sides_var.set(str(self.state.polygon_sides))

        self.set_app_state(self.state.app_mode)

    def set_app_state(self, mode):
        self.state.app_mode = mode
        is_creating_segment = (mode == 'CREATING_SEGMENT')
        is_creating_circle = mode.startswith('CREATING_CIRCLE')
        is_creating_arc = mode.startswith('CREATING_ARC')
        is_creating_rectangle = mode.startswith('CREATING_RECTANGLE')
        is_creating_ellipse = mode.startswith('CREATING_ELLIPSE')
        is_creating_polygon = mode.startswith('CREATING_POLYGON')
        is_creating_spline = mode.startswith('CREATING_SPLINE')
        is_creating = (
            is_creating_segment
            or is_creating_circle
            or is_creating_arc
            or is_creating_rectangle
            or is_creating_ellipse
            or is_creating_polygon
            or is_creating_spline
        )
        is_panning = (mode == 'PANNING')

        # Сброс превью других типов при смене режима
        if is_creating_segment:
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
        elif is_creating_circle:
            self.state.preview_segment = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
        elif is_creating_arc:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
        elif is_creating_rectangle:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
        elif is_creating_ellipse:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
        elif is_creating_polygon:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_spline = None
        elif is_creating_spline:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None

        entry_state = 'normal' if is_creating else 'disabled'
        entries = [self.view.p1_x_entry, self.view.p1_y_entry, self.view.p2_x_entry, self.view.p2_y_entry]

        # Поля окружностей
        circle_entries = [
            self.view.circle_center_x_entry, self.view.circle_center_y_entry,
            self.view.circle_param_entry, self.view.circle_p2_x_entry,
            self.view.circle_p2_y_entry, self.view.circle_p3_x_entry,
            self.view.circle_p3_y_entry
        ]

        # Поля дуг
        arc_entries = [
            self.view.arc_p1_x_entry, self.view.arc_p1_y_entry,
            self.view.arc_p2_x_entry, self.view.arc_p2_y_entry,
            self.view.arc_p3_x_entry, self.view.arc_p3_y_entry,
            self.view.arc_center_x_entry, self.view.arc_center_y_entry,
            self.view.arc_radius_entry, self.view.arc_start_angle_entry, self.view.arc_end_angle_entry
        ]

        # Поля прямоугольников
        rect_entries = [
            self.view.rect_p1_x_entry, self.view.rect_p1_y_entry,
            self.view.rect_p2_x_entry, self.view.rect_p2_y_entry,
            self.view.rect_corner_x_entry, self.view.rect_corner_y_entry,
            self.view.rect_width_entry, self.view.rect_height_entry,
            self.view.rect_center_x_entry, self.view.rect_center_y_entry,
            self.view.rect_center_w_entry, self.view.rect_center_h_entry,
            self.view.rect_corner_value_entry
        ]

        # Поля эллипсов
        ellipse_entries = [
            self.view.ellipse_center_x_entry, self.view.ellipse_center_y_entry,
            self.view.ellipse_a_x_entry, self.view.ellipse_a_y_entry,
            self.view.ellipse_b_x_entry, self.view.ellipse_b_y_entry
        ]
        # Поля многоугольников
        polygon_entries = [
            self.view.polygon_center_x_entry, self.view.polygon_center_y_entry,
            self.view.polygon_radius_entry, self.view.polygon_sides_spin
        ]
        # Поля сплайнов
        spline_entries = [
            self.view.spline_point_x_entry, self.view.spline_point_y_entry, self.view.spline_points_listbox
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
            # Блокируем поля дуг
            for entry in arc_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            # Блокируем поля прямоугольников
            for entry in rect_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            # Блокируем поля эллипсов
            for entry in ellipse_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            # Блокируем поля многоугольников
            for entry in polygon_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            # Блокируем поля сплайнов
            for entry in spline_entries:
                try:
                    entry.delete(0, tk.END)
                except Exception:
                    pass
                entry.config(state='disabled')
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None
            self.state.active_p1 = None
            self.state.active_p2 = None
            self.state.active_p3 = None
            self.state.active_p4 = None
            self.state.spline_control_points = []
            try:
                self._update_spline_points_listbox()
            except Exception:
                pass

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
        elif is_creating_arc:
            # Разблокируем поля
            for entry in entries: entry.config(state=entry_state)
            for entry in circle_entries: entry.config(state=entry_state)
            for entry in arc_entries: entry.config(state='normal')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_arc)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_arc)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_rectangle:
            for entry in entries: entry.config(state=entry_state)
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='normal')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_rectangle)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_rectangle)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_ellipse:
            for entry in entries: entry.config(state=entry_state)
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='disabled')
            for entry in ellipse_entries: entry.config(state='normal')
            for entry in polygon_entries: entry.config(state='disabled')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_ellipse)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_ellipse)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_polygon:
            for entry in entries: entry.config(state=entry_state)
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='disabled')
            for entry in ellipse_entries: entry.config(state='disabled')
            for entry in polygon_entries: entry.config(state='normal')
            for entry in spline_entries: entry.config(state='disabled')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_polygon)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_polygon)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_spline:
            for entry in entries: entry.config(state='disabled')
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='disabled')
            for entry in ellipse_entries: entry.config(state='disabled')
            for entry in polygon_entries: entry.config(state='disabled')
            for entry in spline_entries: entry.config(state='normal')
            self.state.points_clicked = 0
            self.state.spline_control_points = []
            self._update_spline_points_listbox()
            self.root.bind("<Return>", self.finalize_spline)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_spline)
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
        found_arc = None
        found_rectangle = None
        found_ellipse = None
        found_polygon = None
        found_spline = None

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

        # Ищем дуги
        if not found_segment and not found_circle:
            for arc in self.state.arcs:
                dist = arc.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_arc = arc
                    break

        # Ищем прямоугольники
        if not found_segment and not found_circle and not found_arc:
            for rect in self.state.rectangles:
                dist = rect.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_rectangle = rect
                    break

        # Ищем эллипсы
        if not found_segment and not found_circle and not found_arc and not found_rectangle:
            for ellipse in self.state.ellipses:
                dist = ellipse.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_ellipse = ellipse
                    break
        # Ищем многоугольники
        if not found_segment and not found_circle and not found_arc and not found_rectangle and not found_ellipse:
            for poly in self.state.polygons:
                dist = poly.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_polygon = poly
                    break
        # Ищем сплайны
        if not found_segment and not found_circle and not found_arc and not found_rectangle and not found_ellipse and not found_polygon:
            for spline in self.state.splines:
                dist = spline.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_spline = spline
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
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
            else:
                # Если Ctrl НЕ зажат - выбираем только этот (сброс остальных)
                self.state.selected_segments = [found_segment]
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
        elif found_circle:
            if ctrl_pressed:
                # Если Ctrl зажат - добавляем или убираем из списка
                if found_circle in self.state.selected_circles:
                    self.state.selected_circles.remove(found_circle)
                else:
                    self.state.selected_circles.append(found_circle)
                # Очищаем выделение сегментов при выборе окружности
                self.state.selected_segments = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
            else:
                # Если Ctrl НЕ зажат - выбираем только этот (сброс остальных)
                self.state.selected_segments = []
                self.state.selected_circles = [found_circle]
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
        elif found_arc:
            if ctrl_pressed:
                if found_arc in self.state.selected_arcs:
                    self.state.selected_arcs.remove(found_arc)
                else:
                    self.state.selected_arcs.append(found_arc)
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = [found_arc]
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
        elif found_ellipse:
            if ctrl_pressed:
                if found_ellipse in self.state.selected_ellipses:
                    self.state.selected_ellipses.remove(found_ellipse)
                else:
                    self.state.selected_ellipses.append(found_ellipse)
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = [found_ellipse]
                self.state.selected_polygons = []
                self.state.selected_splines = []
        elif found_rectangle:
            if ctrl_pressed:
                if found_rectangle in self.state.selected_rectangles:
                    self.state.selected_rectangles.remove(found_rectangle)
                else:
                    self.state.selected_rectangles.append(found_rectangle)
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = [found_rectangle]
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
        elif found_polygon:
            if ctrl_pressed:
                if found_polygon in self.state.selected_polygons:
                    self.state.selected_polygons.remove(found_polygon)
                else:
                    self.state.selected_polygons.append(found_polygon)
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_splines = []
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = [found_polygon]
                self.state.selected_splines = []
        elif found_spline:
            if ctrl_pressed:
                if found_spline in self.state.selected_splines:
                    self.state.selected_splines.remove(found_spline)
                else:
                    self.state.selected_splines.append(found_spline)
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = [found_spline]
        else:
            # Если клик в пустоту и Ctrl НЕ зажат - сбрасываем всё
            if not ctrl_pressed:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []

        # Синхронизируем UI (список стилей, превью) с тем, что мы выделили
        self._sync_ui_with_selection()
        self.redraw_all()

    def _sync_ui_with_selection(self):
        """Обновляет панель свойств в зависимости от выделения."""
        self.view.kinks_frame.pack_forget()

        sel_segments = self.state.selected_segments
        sel_circles = self.state.selected_circles
        sel_arcs = self.state.selected_arcs
        sel_rectangles = self.state.selected_rectangles
        sel_ellipses = self.state.selected_ellipses
        sel_polygons = self.state.selected_polygons
        sel_splines = self.state.selected_splines

        # Если ничего не выделено
        if not sel_segments and not sel_circles and not sel_arcs and not sel_rectangles and not sel_ellipses and not sel_polygons and not sel_splines:
            style_obj = GOST_STYLES.get(self.state.current_style_name)
            if style_obj:
                self.view.set_style_selection(style_obj.name)
                self.view.segment_swatch.config(bg=self.state.current_color)
            return

        # Определяем, что выделено
        if sel_segments and not sel_circles and not sel_arcs and not sel_rectangles and not sel_ellipses and not sel_polygons:
            # Выделены только сегменты
            self._sync_ui_with_segments(sel_segments)
        elif sel_circles and not sel_segments and not sel_arcs and not sel_rectangles and not sel_ellipses and not sel_polygons:
            # Выделены только окружности
            self._sync_ui_with_circles(sel_circles)
        elif sel_arcs and not sel_segments and not sel_circles and not sel_rectangles and not sel_ellipses and not sel_polygons:
            # Выделены только дуги
            self._sync_ui_with_arcs(sel_arcs)
        elif sel_rectangles and not sel_segments and not sel_circles and not sel_arcs and not sel_ellipses and not sel_polygons:
            self._sync_ui_with_rectangles(sel_rectangles)
        elif sel_ellipses and not sel_segments and not sel_circles and not sel_arcs and not sel_rectangles and not sel_polygons:
            self._sync_ui_with_ellipses(sel_ellipses)
        elif sel_polygons and not sel_segments and not sel_circles and not sel_arcs and not sel_rectangles and not sel_ellipses and not sel_splines:
            self._sync_ui_with_polygons(sel_polygons)
        elif sel_splines and not sel_segments and not sel_circles and not sel_arcs and not sel_rectangles and not sel_ellipses and not sel_polygons:
            self._sync_ui_with_splines(sel_splines)
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

    def _sync_ui_with_arcs(self, sel_arcs):
        """Синхронизация UI с выделенными дугами."""
        unique_styles = {arc.style_name for arc in sel_arcs}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_arcs[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_rectangles(self, sel_rectangles):
        """Синхронизация UI с выделенными прямоугольниками."""
        unique_styles = {rect.style_name for rect in sel_rectangles}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_rectangles[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_ellipses(self, sel_ellipses):
        """Синхронизация UI с выделенными эллипсами."""
        unique_styles = {ell.style_name for ell in sel_ellipses}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_ellipses[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_polygons(self, sel_polygons):
        """Синхронизация UI с выделенными многоугольниками."""
        unique_styles = {poly.style_name for poly in sel_polygons}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_polygons[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_splines(self, sel_splines):
        """Синхронизация UI с выделенными сплайнами."""
        unique_styles = {sp.style_name for sp in sel_splines}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_splines[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color

            style = self.state.line_styles.get(style_name)
            base_type = getattr(style, 'base_type', 'solid') if style else 'solid'

            if base_type in ['zigzag', 'wave'] and len(sel_splines) == 1:
                sp = sel_splines[0]
                self.view.kinks_frame.pack(fill=tk.X, padx=5, pady=5, after=self.view.style_combobox)
                if base_type == 'zigzag':
                    self.view.lbl_kinks.config(text="Кол-во изломов:")
                    current_val = getattr(sp, 'kinks_count', None)
                else:
                    self.view.lbl_kinks.config(text="Кол-во волн:")
                    current_val = getattr(sp, 'waves_count', None)
                if current_val:
                    self.view.kinks_var.set(str(current_val))
                else:
                    self.view.kinks_var.set('')
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    # Изменение количества изломов или волн
    def on_kinks_changed(self, event=None):
        target = None
        if self.state.selected_segments:
            target = self.state.selected_segments[0]
        elif self.state.selected_splines:
            target = self.state.selected_splines[0]
        else:
            return
        
        # Определяем тип текущей линии
        style = self.state.line_styles.get(target.style_name)
        base_type = getattr(style, 'base_type', 'solid')
        
        try:
            val_str = self.view.kinks_var.get()
            if not val_str: 
                if base_type == 'zigzag': target.kinks_count = None
                else: target.waves_count = None
                self.redraw_all()
                return
                
            val = int(val_str)
            zoom = self.state.zoom
            seg_len_px = (target.length if hasattr(target, 'length') else target.approximate_length()) * zoom
            
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
            if base_type == 'zigzag': target.kinks_count = val
            else: target.waves_count = val
            
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
        elif self.state.selected_arcs:
            for arc in self.state.selected_arcs:
                arc.style_name = new_style_name
        elif self.state.selected_rectangles:
            for rect in self.state.selected_rectangles:
                rect.style_name = new_style_name
        elif self.state.selected_ellipses:
            for ellipse in self.state.selected_ellipses:
                ellipse.style_name = new_style_name
        elif self.state.selected_polygons:
            for poly in self.state.selected_polygons:
                poly.style_name = new_style_name
        elif self.state.selected_splines:
            for spline in self.state.selected_splines:
                spline.style_name = new_style_name

        self._sync_ui_with_selection()

        self.update_preview_segment()
        self.update_preview_circle()
        self.update_preview_arc()
        self.update_preview_rectangle()
        self.update_preview_ellipse()
        self.update_preview_polygon()
        self.update_preview_spline()
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

    def on_new_arc_mode(self, event=None):
        self.set_app_state('CREATING_ARC')
        self.view.settings_notebook.select(3)  # Вкладка "Дуги"

        # Очищаем поля дуг
        for entry in [
            self.view.arc_p1_x_entry, self.view.arc_p1_y_entry,
            self.view.arc_p2_x_entry, self.view.arc_p2_y_entry,
            self.view.arc_p3_x_entry, self.view.arc_p3_y_entry,
            self.view.arc_center_x_entry, self.view.arc_center_y_entry,
            self.view.arc_radius_entry, self.view.arc_start_angle_entry, self.view.arc_end_angle_entry
        ]:
            entry.delete(0, tk.END)

        # Фокус на первую точку/центр
        method = self.state.arc_creation_method
        if method == 'three_points':
            self.view.arc_p1_x_entry.focus_set()
        else:
            self.view.arc_center_x_entry.focus_set()

    def on_new_rectangle_mode(self, event=None):
        self.set_app_state('CREATING_RECTANGLE')
        self.view.settings_notebook.select(4)  # Вкладка "Прямоугольники"

        for entry in [
            self.view.rect_p1_x_entry, self.view.rect_p1_y_entry,
            self.view.rect_p2_x_entry, self.view.rect_p2_y_entry,
            self.view.rect_corner_x_entry, self.view.rect_corner_y_entry,
            self.view.rect_width_entry, self.view.rect_height_entry,
            self.view.rect_center_x_entry, self.view.rect_center_y_entry,
            self.view.rect_center_w_entry, self.view.rect_center_h_entry,
            self.view.rect_corner_value_entry
        ]:
            entry.delete(0, tk.END)

        method = self.state.rectangle_creation_method
        if method == 'two_points':
            self.view.rect_p1_x_entry.focus_set()
        elif method == 'corner_size':
            self.view.rect_corner_x_entry.focus_set()
        else:
            self.view.rect_center_x_entry.focus_set()

    def on_new_ellipse_mode(self, event=None):
        self.set_app_state('CREATING_ELLIPSE')
        self.view.settings_notebook.select(5)  # Вкладка "Эллипсы"

        for entry in [
            self.view.ellipse_center_x_entry, self.view.ellipse_center_y_entry,
            self.view.ellipse_a_x_entry, self.view.ellipse_a_y_entry,
            self.view.ellipse_b_x_entry, self.view.ellipse_b_y_entry
        ]:
            entry.delete(0, tk.END)

        self.view.ellipse_center_x_entry.focus_set()

    def on_new_polygon_mode(self, event=None):
        self.set_app_state('CREATING_POLYGON')
        self.view.settings_notebook.select(6)  # Вкладка "Многоугольники"

        for entry in [
            self.view.polygon_center_x_entry, self.view.polygon_center_y_entry,
            self.view.polygon_radius_entry
        ]:
            entry.delete(0, tk.END)
        self.view.polygon_sides_var.set(str(self.state.polygon_sides))

    def on_new_spline_mode(self, event=None):
        self.set_app_state('CREATING_SPLINE')
        # Вкладка будет добавлена после многоугольников
        self.view.settings_notebook.select(7)
        self.state.spline_control_points = []
        self.state.preview_spline = None
        self.view.spline_point_x_entry.delete(0, tk.END)
        self.view.spline_point_y_entry.delete(0, tk.END)
        self._update_spline_points_listbox()
        self.view.spline_point_x_entry.focus_set()

        self.view.polygon_center_x_entry.focus_set()

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

    def update_preview_arc(self, event=None):
        try:
            method = self.state.arc_creation_method
            angle_unit = self.view.angle_units.get()

            def _to_rad(val):
                return math.radians(val) if angle_unit == 'degrees' else val

            if method == 'three_points':
                p1 = Point(float(self.view.arc_p1_x_entry.get()), float(self.view.arc_p1_y_entry.get()))
                p2 = Point(float(self.view.arc_p2_x_entry.get()), float(self.view.arc_p2_y_entry.get()))
                p3 = Point(float(self.view.arc_p3_x_entry.get()), float(self.view.arc_p3_y_entry.get()))
                self.state.preview_arc = Arc.from_three_points(
                    p1, p2, p3,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            else:
                center = Point(float(self.view.arc_center_x_entry.get()), float(self.view.arc_center_y_entry.get()))
                radius = float(self.view.arc_radius_entry.get())
                start_ang = _to_rad(float(self.view.arc_start_angle_entry.get()))
                end_ang = _to_rad(float(self.view.arc_end_angle_entry.get()))
                self.state.preview_arc = Arc.from_center_angles(
                    center, radius, start_ang, end_ang,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
        except (ValueError, tk.TclError):
            self.state.preview_arc = None
        self.redraw_all()

    def update_preview_rectangle(self, event=None):
        try:
            method = self.state.rectangle_creation_method
            corner_type = self.view.rect_corner_type.get()
            self.state.rectangle_corner_type = corner_type
            try:
                corner_val = float(self.view.rect_corner_value_entry.get())
            except (ValueError, tk.TclError):
                corner_val = 0.0
            self.state.rectangle_corner_value = corner_val

            common_kwargs = dict(
                style_name=self.state.current_style_name,
                color=self.state.current_color,
                corner_type=corner_type,
                corner_value=corner_val
            )

            if method == 'two_points':
                p1 = Point(float(self.view.rect_p1_x_entry.get()), float(self.view.rect_p1_y_entry.get()))
                p2 = Point(float(self.view.rect_p2_x_entry.get()), float(self.view.rect_p2_y_entry.get()))
                self.state.preview_rectangle = Rectangle.from_two_points(p1, p2, **common_kwargs)
            elif method == 'corner_size':
                corner = Point(float(self.view.rect_corner_x_entry.get()), float(self.view.rect_corner_y_entry.get()))
                width = float(self.view.rect_width_entry.get())
                height = float(self.view.rect_height_entry.get())
                self.state.preview_rectangle = Rectangle.from_corner_size(corner, width, height, **common_kwargs)
            elif method == 'center_size':
                center = Point(float(self.view.rect_center_x_entry.get()), float(self.view.rect_center_y_entry.get()))
                width = float(self.view.rect_center_w_entry.get())
                height = float(self.view.rect_center_h_entry.get())
                self.state.preview_rectangle = Rectangle.from_center_size(center, width, height, **common_kwargs)
        except (ValueError, tk.TclError):
            self.state.preview_rectangle = None
        self.redraw_all()

    def update_preview_ellipse(self, event=None):
        try:
            center = Point(float(self.view.ellipse_center_x_entry.get()), float(self.view.ellipse_center_y_entry.get()))
            axis_a = Point(float(self.view.ellipse_a_x_entry.get()), float(self.view.ellipse_a_y_entry.get()))
            axis_b = Point(float(self.view.ellipse_b_x_entry.get()), float(self.view.ellipse_b_y_entry.get()))
            self.state.preview_ellipse = Ellipse.from_center_axes(
                center, axis_a, axis_b,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
        except (ValueError, tk.TclError):
            self.state.preview_ellipse = None
        self.redraw_all()

    def update_preview_polygon(self, event=None):
        try:
            center = Point(float(self.view.polygon_center_x_entry.get()), float(self.view.polygon_center_y_entry.get()))
            radius = float(self.view.polygon_radius_entry.get())
            sides = int(self.view.polygon_sides_var.get())
            variant = self.view.polygon_variant.get()
            self.state.preview_polygon = RegularPolygon.from_center_radius(
                center, radius, sides,
                variant=variant,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            # Синхронизируем state с UI
            self.state.polygon_sides = max(3, sides)
            self.state.polygon_variant = variant
        except (ValueError, tk.TclError):
            self.state.preview_polygon = None
        self.redraw_all()

    def update_preview_spline(self, event=None):
        if len(self.state.spline_control_points) < 2:
            self.state.preview_spline = None
            self.redraw_all()
            return
        ctrl_copy = [Point(p.x, p.y) for p in self.state.spline_control_points]
        self.state.preview_spline = Spline(
            ctrl_copy,
            style_name=self.state.current_style_name,
            color=self.state.current_color
        )
        # Если выбрана волна/зигзаг и есть сохраненные параметры, переносим
        if self.state.selected_splines:
            src = self.state.selected_splines[0]
            self.state.preview_spline.kinks_count = getattr(src, 'kinks_count', None)
            self.state.preview_spline.waves_count = getattr(src, 'waves_count', None)
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

    def finalize_arc(self, event=None):
        if self.state.preview_arc:
            final_arc = Arc(
                self.state.preview_arc.center,
                self.state.preview_arc.radius,
                self.state.preview_arc.start_angle,
                self.state.preview_arc.end_angle,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.state.arcs.append(final_arc)
            self.set_app_state('IDLE')

    def finalize_rectangle(self, event=None):
        if self.state.preview_rectangle:
            rect = self.state.preview_rectangle
            final_rect = Rectangle(
                rect.min_x, rect.min_y, rect.max_x, rect.max_y,
                style_name=self.state.current_style_name,
                color=self.state.current_color,
                corner_type=rect.corner_type,
                corner_value=rect.corner_value
            )
            self.state.rectangles.append(final_rect)
            self.set_app_state('IDLE')

    def finalize_ellipse(self, event=None):
        if self.state.preview_ellipse:
            ell = self.state.preview_ellipse
            final_ellipse = Ellipse(
                ell.center,
                ell.axis_point_a,
                ell.axis_point_b,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.state.ellipses.append(final_ellipse)
            self.set_app_state('IDLE')

    def finalize_polygon(self, event=None):
        if self.state.preview_polygon:
            poly = self.state.preview_polygon
            final_poly = RegularPolygon(
                poly.center,
                poly.base_radius,
                poly.sides,
                variant=poly.variant,
                start_angle=poly.start_angle,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.state.polygons.append(final_poly)
            self.set_app_state('IDLE')

    def finalize_spline(self, event=None):
        if self.state.preview_spline:
            sp = self.state.preview_spline
            ctrl_copy = [Point(p.x, p.y) for p in sp.control_points]
            final_spline = Spline(
                ctrl_copy,
                style_name=self.state.current_style_name,
                color=self.state.current_color,
                kinks_count=getattr(sp, 'kinks_count', None),
                waves_count=getattr(sp, 'waves_count', None)
            )
            self.state.splines.append(final_spline)
            self.set_app_state('IDLE')

    def on_escape_key(self, event=None):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_CIRCLE', 'CREATING_ARC', 'CREATING_RECTANGLE', 'CREATING_ELLIPSE', 'CREATING_POLYGON', 'CREATING_SPLINE', 'PANNING']:
            self.set_app_state('IDLE')
        elif self.state.selected_segments or self.state.selected_circles or self.state.selected_arcs or self.state.selected_rectangles or self.state.selected_ellipses or self.state.selected_polygons or self.state.selected_splines:
            # Если есть выделение - снимаем его
            self.state.selected_segments = []
            self.state.selected_circles = []
            self.state.selected_arcs = []
            self.state.selected_rectangles = []
            self.state.selected_ellipses = []
            self.state.selected_polygons = []
            self.state.selected_splines = []
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
        elif self.state.selected_arcs:
            for arc in self.state.selected_arcs:
                if arc in self.state.arcs:
                    self.state.arcs.remove(arc)
            self.state.selected_arcs = []
        elif self.state.selected_rectangles:
            for rect in self.state.selected_rectangles:
                if rect in self.state.rectangles:
                    self.state.rectangles.remove(rect)
            self.state.selected_rectangles = []
        elif self.state.selected_ellipses:
            for ellipse in self.state.selected_ellipses:
                if ellipse in self.state.ellipses:
                    self.state.ellipses.remove(ellipse)
            self.state.selected_ellipses = []
        elif self.state.selected_polygons:
            for poly in self.state.selected_polygons:
                if poly in self.state.polygons:
                    self.state.polygons.remove(poly)
            self.state.selected_polygons = []
        elif self.state.selected_splines:
            for spline in self.state.selected_splines:
                if spline in self.state.splines:
                    self.state.splines.remove(spline)
            self.state.selected_splines = []
        elif self.state.segments:
            self.state.segments.pop()
        elif self.state.circles:
            self.state.circles.pop()
        elif self.state.arcs:
            self.state.arcs.pop()
        elif self.state.rectangles:
            self.state.rectangles.pop()
        elif self.state.ellipses:
            self.state.ellipses.pop()
        elif self.state.polygons:
            self.state.polygons.pop()
        elif self.state.splines:
            self.state.splines.pop()

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

    def on_polygon_variant_change(self):
        self.state.polygon_variant = self.view.polygon_variant.get()
        self.update_preview_polygon()

    def on_polygon_sides_change(self, event=None):
        try:
            sides = int(self.view.polygon_sides_var.get())
            if sides < 3:
                sides = 3
            self.state.polygon_sides = sides
            self.view.polygon_sides_var.set(str(sides))
        except ValueError:
            return
        self.update_preview_polygon()

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

    def on_lmb_click_arc(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        method = self.state.arc_creation_method
        angle_unit = self.view.angle_units.get()

        def _to_display_angle(rad_val):
            return math.degrees(rad_val) if angle_unit == 'degrees' else rad_val

        if method == 'three_points':
            if self.state.points_clicked == 0:
                self.view.arc_p1_x_entry.delete(0, tk.END); self.view.arc_p1_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_p1_y_entry.delete(0, tk.END); self.view.arc_p1_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                self.view.arc_p2_x_entry.delete(0, tk.END); self.view.arc_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_p2_y_entry.delete(0, tk.END); self.view.arc_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
            elif self.state.points_clicked == 2:
                self.view.arc_p3_x_entry.delete(0, tk.END); self.view.arc_p3_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_p3_y_entry.delete(0, tk.END); self.view.arc_p3_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 3
        else:
            if self.state.points_clicked == 0:
                # Центр
                self.view.arc_center_x_entry.delete(0, tk.END); self.view.arc_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_center_y_entry.delete(0, tk.END); self.view.arc_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                # Устанавливаем радиус и начальный угол
                cx = float(self.view.arc_center_x_entry.get())
                cy = float(self.view.arc_center_y_entry.get())
                radius = math.sqrt((wx - cx)**2 + (wy - cy)**2)
                ang = math.atan2(wy - cy, wx - cx)

                self.view.arc_radius_entry.delete(0, tk.END); self.view.arc_radius_entry.insert(0, f"{radius:.2f}")
                self.view.arc_start_angle_entry.delete(0, tk.END); self.view.arc_start_angle_entry.insert(0, f"{_to_display_angle(ang):.2f}")
                self.state.points_clicked = 2
            elif self.state.points_clicked == 2:
                cx = float(self.view.arc_center_x_entry.get())
                cy = float(self.view.arc_center_y_entry.get())
                ang = math.atan2(wy - cy, wx - cx)
                self.view.arc_end_angle_entry.delete(0, tk.END); self.view.arc_end_angle_entry.insert(0, f"{_to_display_angle(ang):.2f}")

                # Если радиус еще не задан, берем из текущей точки
                if not self.view.arc_radius_entry.get():
                    radius = math.sqrt((wx - cx)**2 + (wy - cy)**2)
                    self.view.arc_radius_entry.insert(0, f"{radius:.2f}")
                self.state.points_clicked = 3

        self.update_preview_arc()

    def on_lmb_click_rectangle(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        method = self.state.rectangle_creation_method

        if method == 'two_points':
            if self.state.points_clicked == 0:
                self.view.rect_p1_x_entry.delete(0, tk.END); self.view.rect_p1_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_p1_y_entry.delete(0, tk.END); self.view.rect_p1_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                self.view.rect_p2_x_entry.delete(0, tk.END); self.view.rect_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_p2_y_entry.delete(0, tk.END); self.view.rect_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
        elif method == 'corner_size':
            if self.state.points_clicked == 0:
                self.view.rect_corner_x_entry.delete(0, tk.END); self.view.rect_corner_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_corner_y_entry.delete(0, tk.END); self.view.rect_corner_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                try:
                    cx = float(self.view.rect_corner_x_entry.get())
                    cy = float(self.view.rect_corner_y_entry.get())
                except ValueError:
                    cx, cy = wx, wy
                self.view.rect_width_entry.delete(0, tk.END); self.view.rect_width_entry.insert(0, f"{wx - cx:.2f}")
                self.view.rect_height_entry.delete(0, tk.END); self.view.rect_height_entry.insert(0, f"{wy - cy:.2f}")
                self.state.points_clicked = 2
        elif method == 'center_size':
            if self.state.points_clicked == 0:
                self.view.rect_center_x_entry.delete(0, tk.END); self.view.rect_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_center_y_entry.delete(0, tk.END); self.view.rect_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                try:
                    cx = float(self.view.rect_center_x_entry.get())
                    cy = float(self.view.rect_center_y_entry.get())
                except ValueError:
                    cx, cy = wx, wy
                self.view.rect_center_w_entry.delete(0, tk.END); self.view.rect_center_w_entry.insert(0, f"{2*(wx - cx):.2f}")
                self.view.rect_center_h_entry.delete(0, tk.END); self.view.rect_center_h_entry.insert(0, f"{2*(wy - cy):.2f}")
                self.state.points_clicked = 2

        self.update_preview_rectangle()

    def on_lmb_click_ellipse(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self.view.ellipse_center_x_entry.delete(0, tk.END); self.view.ellipse_center_x_entry.insert(0, f"{wx:.2f}")
            self.view.ellipse_center_y_entry.delete(0, tk.END); self.view.ellipse_center_y_entry.insert(0, f"{wy:.2f}")
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            self.view.ellipse_a_x_entry.delete(0, tk.END); self.view.ellipse_a_x_entry.insert(0, f"{wx:.2f}")
            self.view.ellipse_a_y_entry.delete(0, tk.END); self.view.ellipse_a_y_entry.insert(0, f"{wy:.2f}")
            self.state.points_clicked = 2
        elif self.state.points_clicked == 2:
            self.view.ellipse_b_x_entry.delete(0, tk.END); self.view.ellipse_b_x_entry.insert(0, f"{wx:.2f}")
            self.view.ellipse_b_y_entry.delete(0, tk.END); self.view.ellipse_b_y_entry.insert(0, f"{wy:.2f}")
            self.state.points_clicked = 3

        self.update_preview_ellipse()

    def on_lmb_click_polygon(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self.view.polygon_center_x_entry.delete(0, tk.END); self.view.polygon_center_x_entry.insert(0, f"{wx:.2f}")
            self.view.polygon_center_y_entry.delete(0, tk.END); self.view.polygon_center_y_entry.insert(0, f"{wy:.2f}")
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            try:
                cx = float(self.view.polygon_center_x_entry.get())
                cy = float(self.view.polygon_center_y_entry.get())
            except ValueError:
                cx, cy = wx, wy
            radius = math.sqrt((wx - cx) ** 2 + (wy - cy) ** 2)
            self.view.polygon_radius_entry.delete(0, tk.END); self.view.polygon_radius_entry.insert(0, f"{radius:.2f}")
            self.state.points_clicked = 2
        self.update_preview_polygon()

    def _update_spline_points_listbox(self):
        lb = self.view.spline_points_listbox
        lb.delete(0, tk.END)
        for idx, p in enumerate(self.state.spline_control_points, start=1):
            lb.insert(tk.END, f"{idx}: ({p.x:.2f}, {p.y:.2f})")

    def on_add_spline_point_manual(self, event=None):
        try:
            x = float(self.view.spline_point_x_entry.get())
            y = float(self.view.spline_point_y_entry.get())
        except (ValueError, tk.TclError):
            return
        self.state.spline_control_points.append(Point(x, y))
        self._update_spline_points_listbox()
        self.update_preview_spline()

    def on_remove_last_spline_point(self, event=None):
        if self.state.spline_control_points:
            self.state.spline_control_points.pop()
            self._update_spline_points_listbox()
            self.update_preview_spline()

    def on_clear_spline_points(self, event=None):
        self.state.spline_control_points = []
        self._update_spline_points_listbox()
        self.view.spline_point_x_entry.delete(0, tk.END)
        self.view.spline_point_y_entry.delete(0, tk.END)
        self.update_preview_spline()

    def on_lmb_click_spline(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        self.state.spline_control_points.append(Point(wx, wy))
        self.view.spline_point_x_entry.delete(0, tk.END); self.view.spline_point_x_entry.insert(0, f"{wx:.2f}")
        self.view.spline_point_y_entry.delete(0, tk.END); self.view.spline_point_y_entry.insert(0, f"{wy:.2f}")
        self._update_spline_points_listbox()
        self.update_preview_spline()

    def on_rmb_click_rectangle(self, event):
        """ПКМ для удаления точек при создании прямоугольника."""
        method = self.state.rectangle_creation_method

        if method == 'two_points':
            if self.view.rect_p2_x_entry.get():
                self.view.rect_p2_x_entry.delete(0, tk.END); self.view.rect_p2_y_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.rect_p1_x_entry.get():
                self.view.rect_p1_x_entry.delete(0, tk.END); self.view.rect_p1_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'corner_size':
            if self.view.rect_width_entry.get() or self.view.rect_height_entry.get():
                self.view.rect_width_entry.delete(0, tk.END); self.view.rect_height_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.rect_corner_x_entry.get():
                self.view.rect_corner_x_entry.delete(0, tk.END); self.view.rect_corner_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'center_size':
            if self.view.rect_center_w_entry.get() or self.view.rect_center_h_entry.get():
                self.view.rect_center_w_entry.delete(0, tk.END); self.view.rect_center_h_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.rect_center_x_entry.get():
                self.view.rect_center_x_entry.delete(0, tk.END); self.view.rect_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0

        self.update_preview_rectangle()

    def on_rmb_click_ellipse(self, event):
        """ПКМ для удаления точек при создании эллипса."""
        if self.view.ellipse_b_x_entry.get():
            self.view.ellipse_b_x_entry.delete(0, tk.END); self.view.ellipse_b_y_entry.delete(0, tk.END)
            self.state.points_clicked = 2
        elif self.view.ellipse_a_x_entry.get():
            self.view.ellipse_a_x_entry.delete(0, tk.END); self.view.ellipse_a_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.ellipse_center_x_entry.get():
            self.view.ellipse_center_x_entry.delete(0, tk.END); self.view.ellipse_center_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_ellipse()

    def on_rmb_click_polygon(self, event):
        """ПКМ для отмены шагов при создании многоугольника."""
        if self.view.polygon_radius_entry.get():
            self.view.polygon_radius_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.polygon_center_x_entry.get():
            self.view.polygon_center_x_entry.delete(0, tk.END); self.view.polygon_center_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_polygon()

    def on_rmb_click_spline(self, event):
        """ПКМ удаляет последнюю контрольную точку сплайна."""
        self.on_remove_last_spline_point()

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

    def on_rmb_click_arc(self, event):
        """ПКМ для удаления точек при создании дуги"""
        method = self.state.arc_creation_method

        if method == 'three_points':
            if self.view.arc_p3_x_entry.get():
                self.view.arc_p3_x_entry.delete(0, tk.END); self.view.arc_p3_y_entry.delete(0, tk.END)
                self.state.points_clicked = 2
            elif self.view.arc_p2_x_entry.get():
                self.view.arc_p2_x_entry.delete(0, tk.END); self.view.arc_p2_y_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.arc_p1_x_entry.get():
                self.view.arc_p1_x_entry.delete(0, tk.END); self.view.arc_p1_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        else:
            if self.view.arc_end_angle_entry.get():
                self.view.arc_end_angle_entry.delete(0, tk.END)
                self.state.points_clicked = 2
            elif self.view.arc_start_angle_entry.get():
                self.view.arc_start_angle_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.arc_radius_entry.get():
                self.view.arc_radius_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.arc_center_x_entry.get():
                self.view.arc_center_x_entry.delete(0, tk.END)
                self.view.arc_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0

        self.update_preview_arc()

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
        all_objects = (
            self.state.segments
            + self.state.circles
            + self.state.arcs
            + self.state.rectangles
            + self.state.ellipses
            + self.state.polygons
            + self.state.splines
        )
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

        # Собираем координаты из дуг (учитываем критические углы)
        for arc in self.state.arcs:
            xs.append(arc.center.x); ys.append(arc.center.y)
            angles = [arc.start_angle, arc.end_angle]
            critical = [0, math.pi / 2, math.pi, 3 * math.pi / 2]
            for ang in critical:
                if Arc._is_angle_between_ccw(ang, arc.start_angle, arc.end_angle):
                    angles.append(ang)
            for ang in angles:
                xs.append(arc.center.x + arc.radius * math.cos(ang))
                ys.append(arc.center.y + arc.radius * math.sin(ang))

        # Координаты прямоугольников
        for rect in self.state.rectangles:
            xs.extend([rect.min_x, rect.max_x])
            ys.extend([rect.min_y, rect.max_y])

        # Эллипсы: используем их ограничивающие прямоугольники
        for ellipse in self.state.ellipses:
            min_x_e, max_x_e, min_y_e, max_y_e = ellipse.bounding_box()
            xs.extend([min_x_e, max_x_e])
            ys.extend([min_y_e, max_y_e])

        # Многоугольники
        for poly in self.state.polygons:
            verts = poly.vertices()
            for v in verts:
                xs.append(v.x); ys.append(v.y)

        # Сплайны (по дискретизации)
        for spline in self.state.splines:
            for p in spline.sample_points():
                xs.append(p.x); ys.append(p.y)

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
            for arc in self.state.selected_arcs:
                arc.color = c
            for rect in self.state.selected_rectangles:
                rect.color = c
            for ellipse in self.state.selected_ellipses:
                ellipse.color = c
            for poly in self.state.selected_polygons:
                poly.color = c
            for spline in self.state.selected_splines:
                spline.color = c
            if self.state.preview_spline:
                self.state.preview_spline.color = c
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
        self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = None, None, None, None

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

        # ПРИОРИТЕТ 1.7: РЕЖИМ СОЗДАНИЯ ДУГИ
        if self.state.app_mode == 'CREATING_ARC':
            method = self.state.arc_creation_method
            angle_unit = self.view.angle_units.get()
            sym = "°" if angle_unit == 'degrees' else " rad"

            if method == 'three_points':
                p1 = p2 = p3 = None
                try:
                    p1 = Point(float(self.view.arc_p1_x_entry.get()), float(self.view.arc_p1_y_entry.get()))
                    self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
                except (ValueError, tk.TclError):
                    self.view.p1_coord_var.set("P1: N/A")
                try:
                    p2 = Point(float(self.view.arc_p2_x_entry.get()), float(self.view.arc_p2_y_entry.get()))
                    self.view.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
                except (ValueError, tk.TclError):
                    self.view.p2_coord_var.set("P2: N/A")
                try:
                    p3 = Point(float(self.view.arc_p3_x_entry.get()), float(self.view.arc_p3_y_entry.get()))
                    self.view.p3_coord_var.set(f"P3({p3.x:.2f}, {p3.y:.2f})")
                except (ValueError, tk.TclError):
                    self.view.p3_coord_var.set("P3: N/A")

                self.state.active_p1 = p1
                self.state.active_p2 = p2
                self.state.active_p3 = p3
            else:
                center = None
                start_pt = None
                end_pt = None
                try:
                    center = Point(float(self.view.arc_center_x_entry.get()), float(self.view.arc_center_y_entry.get()))
                    self.view.p1_coord_var.set(f"Центр({center.x:.2f}, {center.y:.2f})")
                except (ValueError, tk.TclError):
                    self.view.p1_coord_var.set("Центр: N/A")
                try:
                    radius = float(self.view.arc_radius_entry.get())
                    self.view.p2_coord_var.set(f"Радиус: {radius:.2f}")
                except (ValueError, tk.TclError):
                    self.view.p2_coord_var.set("Радиус: N/A")
                try:
                    start_val = float(self.view.arc_start_angle_entry.get())
                    end_val = float(self.view.arc_end_angle_entry.get())
                    self.view.p3_coord_var.set(f"θ₁: {start_val:.2f}{sym} | θ₂: {end_val:.2f}{sym}")
                except (ValueError, tk.TclError):
                    self.view.p3_coord_var.set("Углы: N/A")

                # Если есть радиус и углы, вычисляем активные точки
                try:
                    if center is None:
                        center = Point(float(self.view.arc_center_x_entry.get()), float(self.view.arc_center_y_entry.get()))
                    r = float(self.view.arc_radius_entry.get())
                    start_ang = float(self.view.arc_start_angle_entry.get())
                    end_ang = float(self.view.arc_end_angle_entry.get())
                    if angle_unit == 'degrees':
                        start_ang = math.radians(start_ang)
                        end_ang = math.radians(end_ang)
                    start_pt = Point(center.x + r * math.cos(start_ang), center.y + r * math.sin(start_ang))
                    end_pt = Point(center.x + r * math.cos(end_ang), center.y + r * math.sin(end_ang))
                    self.state.active_p1 = center
                    self.state.active_p2 = start_pt
                    self.state.active_p3 = end_pt
                except (ValueError, tk.TclError):
                    self.state.active_p1 = center
                    self.state.active_p2 = start_pt
                    self.state.active_p3 = end_pt

            # Если есть превью, оно приоритетно для точек только для метода центр+углы
            arc_preview = self.state.preview_arc
            if arc_preview and method != 'three_points':
                center = arc_preview.center
                start_pt = Point(center.x + arc_preview.radius * math.cos(arc_preview.start_angle),
                                 center.y + arc_preview.radius * math.sin(arc_preview.start_angle))
                end_pt = Point(center.x + arc_preview.radius * math.cos(arc_preview.end_angle),
                               center.y + arc_preview.radius * math.sin(arc_preview.end_angle))
                self.state.active_p1 = center
                self.state.active_p2 = start_pt
                self.state.active_p3 = end_pt

            if arc_preview:
                sweep = arc_preview.sweep_angle
                sweep_disp = math.degrees(sweep) if angle_unit == 'degrees' else sweep
                self.view.length_var.set(f"Угол дуги: {sweep_disp:.2f}{sym}")
                self.view.angle_var.set("Дуга")
                self.view.p2_coord_var.set(f"Радиус: {arc_preview.radius:.2f}")
            else:
                self.view.length_var.set("Угол дуги: N/A")
                self.view.angle_var.set("Дуга")

            return

        # ПРИОРИТЕТ 1.8: РЕЖИМ СОЗДАНИЯ ПРЯМОУГОЛЬНИКА
        if self.state.app_mode == 'CREATING_RECTANGLE':
            rect_preview = self.state.preview_rectangle
            method = self.state.rectangle_creation_method

            if rect_preview:
                corners = rect_preview.corners()
                if len(corners) >= 4:
                    self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]

                self.view.length_var.set(f"W: {rect_preview.width:.2f} | H: {rect_preview.height:.2f}")
                self.view.angle_var.set("Прямоугольник")
                self.view.p1_coord_var.set(f"Мин({rect_preview.min_x:.2f}, {rect_preview.min_y:.2f})")
                self.view.p2_coord_var.set(f"Макс({rect_preview.max_x:.2f}, {rect_preview.max_y:.2f})")
                self.view.p3_coord_var.set(f"Углы: {rect_preview.corner_type} {rect_preview.corner_value:.2f}")
            else:
                # Без превью - заполняем по введенным значениям
                # Показываем/рисуем то, что уже есть в полях, даже если фигура еще не собрана
                if method == 'two_points':
                    p1 = p2 = None
                    try:
                        p1 = Point(float(self.view.rect_p1_x_entry.get()), float(self.view.rect_p1_y_entry.get()))
                        self.state.active_p1 = p1
                        self.view.p1_coord_var.set(f"P1({p1.x:.2f},{p1.y:.2f})")
                    except (ValueError, tk.TclError):
                        self.view.p1_coord_var.set("P1: N/A")
                    try:
                        p2 = Point(float(self.view.rect_p2_x_entry.get()), float(self.view.rect_p2_y_entry.get()))
                        self.state.active_p2 = p2
                        self.view.p2_coord_var.set(f"P2({p2.x:.2f},{p2.y:.2f})")
                    except (ValueError, tk.TclError):
                        if p1:
                            self.view.p2_coord_var.set("P2: ...")
                        else:
                            self.view.p2_coord_var.set("P2: N/A")
                    if p1 and p2:
                        rect_tmp = Rectangle.from_two_points(p1, p2, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect_tmp.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                elif method == 'corner_size':
                    corner_pt = None
                    w = h = None
                    try:
                        corner_pt = Point(float(self.view.rect_corner_x_entry.get()), float(self.view.rect_corner_y_entry.get()))
                        self.state.active_p1 = corner_pt
                        self.view.p1_coord_var.set(f"Угол({corner_pt.x:.2f},{corner_pt.y:.2f})")
                    except (ValueError, tk.TclError):
                        self.view.p1_coord_var.set("Угол: N/A")
                    try:
                        w = float(self.view.rect_width_entry.get())
                        h = float(self.view.rect_height_entry.get())
                        self.view.p2_coord_var.set(f"W:{w:.2f} H:{h:.2f}")
                    except (ValueError, tk.TclError):
                        if corner_pt:
                            self.view.p2_coord_var.set("Размеры: ...")
                        else:
                            self.view.p2_coord_var.set("Размеры: N/A")
                    if corner_pt is not None and w is not None and h is not None:
                        rect_tmp = Rectangle.from_corner_size(corner_pt, w, h, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect_tmp.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                elif method == 'center_size':
                    center_pt = None
                    w = h = None
                    try:
                        center_pt = Point(float(self.view.rect_center_x_entry.get()), float(self.view.rect_center_y_entry.get()))
                        self.state.active_p1 = center_pt
                        self.view.p1_coord_var.set(f"Центр({center_pt.x:.2f},{center_pt.y:.2f})")
                    except (ValueError, tk.TclError):
                        self.view.p1_coord_var.set("Центр: N/A")
                    try:
                        w = float(self.view.rect_center_w_entry.get())
                        h = float(self.view.rect_center_h_entry.get())
                        self.view.p2_coord_var.set(f"W:{w:.2f} H:{h:.2f}")
                    except (ValueError, tk.TclError):
                        if center_pt:
                            self.view.p2_coord_var.set("Размеры: ...")
                        else:
                            self.view.p2_coord_var.set("Размеры: N/A")
                    if center_pt is not None and w is not None and h is not None:
                        rect_tmp = Rectangle.from_center_size(center_pt, w, h, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect_tmp.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                else:
                    self.view.p1_coord_var.set("P1: N/A"); self.view.p2_coord_var.set("P2: N/A")
                self.view.length_var.set("W/H: N/A")
                self.view.angle_var.set("Прямоугольник")

            return

        # ПРИОРИТЕТ 1.9: РЕЖИМ СОЗДАНИЯ ЭЛЛИПСА
        if self.state.app_mode == 'CREATING_ELLIPSE':
            center = axis_a = axis_b = None
            try:
                center = Point(float(self.view.ellipse_center_x_entry.get()), float(self.view.ellipse_center_y_entry.get()))
                self.state.active_p1 = center
                self.view.p1_coord_var.set(f"Центр({center.x:.2f}, {center.y:.2f})")
            except (ValueError, tk.TclError):
                self.view.p1_coord_var.set("Центр: N/A")
            try:
                axis_a = Point(float(self.view.ellipse_a_x_entry.get()), float(self.view.ellipse_a_y_entry.get()))
                self.state.active_p2 = axis_a
                self.view.p2_coord_var.set(f"A({axis_a.x:.2f}, {axis_a.y:.2f})")
            except (ValueError, tk.TclError):
                if center:
                    self.view.p2_coord_var.set("A: ...")
                else:
                    self.view.p2_coord_var.set("A: N/A")
            try:
                axis_b = Point(float(self.view.ellipse_b_x_entry.get()), float(self.view.ellipse_b_y_entry.get()))
                self.state.active_p3 = axis_b
                self.view.p3_coord_var.set(f"B({axis_b.x:.2f}, {axis_b.y:.2f})")
            except (ValueError, tk.TclError):
                self.view.p3_coord_var.set("B: N/A")

            preview = self.state.preview_ellipse
            if preview:
                e1x, e1y, a, _, _, b = preview._basis()
                ang = math.atan2(e1y, e1x)
                if self.view.angle_units.get() == 'degrees':
                    ang_disp = math.degrees(ang)
                    sym = "°"
                else:
                    ang_disp = ang
                    sym = " rad"
                self.view.length_var.set(f"a: {a:.2f} | b: {b:.2f}")
                self.view.angle_var.set(f"Ось A: {ang_disp:.2f}{sym}")
            else:
                self.view.length_var.set("a/b: N/A")
                self.view.angle_var.set("Эллипс")

            return

        # ПРИОРИТЕТ 1.95: РЕЖИМ СОЗДАНИЯ МНОГОУГОЛЬНИКА
        if self.state.app_mode == 'CREATING_POLYGON':
            center = None
            try:
                center = Point(float(self.view.polygon_center_x_entry.get()), float(self.view.polygon_center_y_entry.get()))
                self.state.active_p1 = center
                self.view.p1_coord_var.set(f"Центр({center.x:.2f}, {center.y:.2f})")
            except (ValueError, tk.TclError):
                self.view.p1_coord_var.set("Центр: N/A")

            try:
                radius = float(self.view.polygon_radius_entry.get())
                self.view.p2_coord_var.set(f"R: {radius:.2f}")
            except (ValueError, tk.TclError):
                self.view.p2_coord_var.set("R: N/A")

            sides = self.state.polygon_sides
            variant = self.view.polygon_variant.get()
            self.view.p3_coord_var.set(f"N={sides} | {variant}")

            if self.state.preview_polygon:
                verts = self.state.preview_polygon.vertices()
                if verts:
                    self.state.active_p2 = verts[0]
                if len(verts) > 1:
                    self.state.active_p3 = verts[1]
                self.view.length_var.set(f"Сторон: {len(verts)}")
                self.view.angle_var.set("Многоугольник")
            else:
                self.view.length_var.set("Сторон: N/A")
                self.view.angle_var.set("Многоугольник")

            return

        # ПРИОРИТЕТ 1.97: РЕЖИМ СОЗДАНИЯ СПЛАЙНА
        if self.state.app_mode == 'CREATING_SPLINE':
            count = len(self.state.spline_control_points)
            self.view.p1_coord_var.set(f"Точек: {count}")
            if count:
                first = self.state.spline_control_points[0]
                last = self.state.spline_control_points[-1]
                self.view.p2_coord_var.set(f"Старт({first.x:.2f}, {first.y:.2f})")
                self.view.p3_coord_var.set(f"Финиш({last.x:.2f}, {last.y:.2f})")
                self.state.active_p1 = first
                self.state.active_p2 = last
            else:
                self.view.p2_coord_var.set("Старт: N/A")
                self.view.p3_coord_var.set("Финиш: N/A")

            if self.state.preview_spline:
                length = self.state.preview_spline.approximate_length()
                self.view.length_var.set(f"Длина≈ {length:.2f}")
            else:
                self.view.length_var.set("Длина: N/A")
            self.view.angle_var.set("Сплайн")
            return

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

        # ПРИОРИТЕТ 2.6: ВЫДЕЛЕНИЕ ДУГИ
        if self.state.selected_arcs:
            arc = self.state.selected_arcs[0]
            angle_unit = self.view.angle_units.get()
            sym = "°" if angle_unit == 'degrees' else " rad"
            sweep_disp = math.degrees(arc.sweep_angle) if angle_unit == 'degrees' else arc.sweep_angle

            center = arc.center
            start_pt = Point(center.x + arc.radius * math.cos(arc.start_angle),
                             center.y + arc.radius * math.sin(arc.start_angle))
            end_pt = Point(center.x + arc.radius * math.cos(arc.end_angle),
                           center.y + arc.radius * math.sin(arc.end_angle))

            self.view.p1_coord_var.set(f"Центр({center.x:.2f}, {center.y:.2f})")
            self.view.p2_coord_var.set(f"Радиус: {arc.radius:.2f}")
            self.view.p3_coord_var.set(f"Угол: {sweep_disp:.2f}{sym}")
            self.view.length_var.set(f"Угол дуги: {sweep_disp:.2f}{sym}")
            self.view.angle_var.set("Дуга")

            return

        # ПРИОРИТЕТ 2.7: ВЫДЕЛЕНИЕ ПРЯМОУГОЛЬНИКА
        if self.state.selected_rectangles:
            rect = self.state.selected_rectangles[0]
            self.view.p1_coord_var.set(f"Мин({rect.min_x:.2f}, {rect.min_y:.2f})")
            self.view.p2_coord_var.set(f"Макс({rect.max_x:.2f}, {rect.max_y:.2f})")
            self.view.p3_coord_var.set(f"Углы: {rect.corner_type} {rect.corner_value:.2f}")
            self.view.length_var.set(f"W: {rect.width:.2f} | H: {rect.height:.2f}")
            self.view.angle_var.set("Прямоугольник")
            return

        # ПРИОРИТЕТ 2.8: ВЫДЕЛЕНИЕ ЭЛЛИПСА
        if self.state.selected_ellipses:
            ell = self.state.selected_ellipses[0]
            self.view.p1_coord_var.set(f"Центр({ell.center.x:.2f}, {ell.center.y:.2f})")
            self.view.p2_coord_var.set(f"A({ell.axis_point_a.x:.2f}, {ell.axis_point_a.y:.2f})")
            self.view.p3_coord_var.set(f"B({ell.axis_point_b.x:.2f}, {ell.axis_point_b.y:.2f})")
            e1x, e1y, a, _, _, b = ell._basis()
            ang = math.atan2(e1y, e1x)
            if self.view.angle_units.get() == 'degrees':
                ang_disp = math.degrees(ang)
                sym = "°"
            else:
                ang_disp = ang
                sym = " rad"
            self.view.length_var.set(f"a: {a:.2f} | b: {b:.2f}")
            self.view.angle_var.set(f"Ось A: {ang_disp:.2f}{sym}")
            return

        # ПРИОРИТЕТ 2.9: ВЫДЕЛЕНИЕ МНОГОУГОЛЬНИКА
        if self.state.selected_polygons:
            poly = self.state.selected_polygons[0]
            self.view.p1_coord_var.set(f"Центр({poly.center.x:.2f}, {poly.center.y:.2f})")
            self.view.p2_coord_var.set(f"R: {poly.base_radius:.2f}")
            self.view.p3_coord_var.set(f"N={poly.sides} | {poly.variant}")
            self.view.length_var.set(f"Сторон: {poly.sides}")
            self.view.angle_var.set("Многоугольник")
            return

        if self.state.selected_splines:
            sp = self.state.selected_splines[0]
            pts = sp.control_points
            self.view.p1_coord_var.set(f"Точек: {len(pts)}")
            if pts:
                self.view.p2_coord_var.set(f"Старт({pts[0].x:.2f}, {pts[0].y:.2f})")
                self.view.p3_coord_var.set(f"Финиш({pts[-1].x:.2f}, {pts[-1].y:.2f})")
            else:
                self.view.p2_coord_var.set("Старт: N/A")
                self.view.p3_coord_var.set("Финиш: N/A")
            self.view.length_var.set(f"Длина≈ {sp.approximate_length():.2f}")
            self.view.angle_var.set("Сплайн")
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

        total_selected = (
            len(self.state.selected_segments)
            + len(self.state.selected_circles)
            + len(self.state.selected_arcs)
            + len(self.state.selected_rectangles)
            + len(self.state.selected_ellipses)
            + len(self.state.selected_polygons)
            + len(self.state.selected_splines)
        )
        if total_selected > 0:
             mode_text = f"Выбрано объектов: {total_selected}"
        else:
            modes = {
                'IDLE': "Ожидание",
                'CREATING_SEGMENT': "Создание отрезка",
                'CREATING_CIRCLE': "Создание окружности",
                'CREATING_ARC': "Создание дуги",
                'CREATING_RECTANGLE': "Создание прямоугольника",
                'CREATING_ELLIPSE': "Создание эллипса",
                'CREATING_POLYGON': "Создание многоугольника",
                'CREATING_SPLINE': "Создание сплайна",
                'PANNING': "Панорамирование"
            }
            mode_text = modes.get(self.state.app_mode, self.state.app_mode)

        self.view.status_mode.config(text=f"Режим: {mode_text}")

    def show_context_menu(self, event):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_CIRCLE', 'CREATING_ARC', 'CREATING_RECTANGLE', 'CREATING_ELLIPSE', 'CREATING_POLYGON', 'CREATING_SPLINE']:
            if self.state.app_mode == 'CREATING_SEGMENT':
                self.on_rmb_click(event)
            elif self.state.app_mode == 'CREATING_CIRCLE':
                self.on_rmb_click_circle(event)
            elif self.state.app_mode == 'CREATING_ARC':
                self.on_rmb_click_arc(event)
            elif self.state.app_mode == 'CREATING_RECTANGLE':
                self.on_rmb_click_rectangle(event)
            elif self.state.app_mode == 'CREATING_ELLIPSE':
                self.on_rmb_click_ellipse(event)
            elif self.state.app_mode == 'CREATING_POLYGON':
                self.on_rmb_click_polygon(event)
            else:
                self.on_rmb_click_spline(event)
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
        elif self.state.selected_circles:
            for circle in self.state.selected_circles:
                circle.style_name = style_key
            self._sync_ui_with_selection()
        elif self.state.selected_arcs:
            for arc in self.state.selected_arcs:
                arc.style_name = style_key
            self._sync_ui_with_selection()
        elif self.state.selected_rectangles:
            for rect in self.state.selected_rectangles:
                rect.style_name = style_key
            self._sync_ui_with_selection()
        elif self.state.selected_ellipses:
            for ellipse in self.state.selected_ellipses:
                ellipse.style_name = style_key
            self._sync_ui_with_selection()
        elif self.state.selected_polygons:
            for poly in self.state.selected_polygons:
                poly.style_name = style_key
            self._sync_ui_with_selection()
        elif self.state.selected_splines:
            for spline in self.state.selected_splines:
                spline.style_name = style_key
            self._sync_ui_with_selection()
        else:
            # Если нет выделения -> просто обновляем UI для будущего рисования
            self.view.set_style_selection(style_key)

        self.update_preview_segment()
        self.update_preview_circle()
        self.update_preview_arc()
        self.update_preview_rectangle()
        self.update_preview_ellipse()
        self.update_preview_polygon()
        self.update_preview_spline()
        self.redraw_all()