import tkinter as tk
from tkinter import messagebox, colorchooser, filedialog, simpledialog, ttk
import math
import os
from datetime import datetime
from logic.geometry import Point, Segment, Circle, Arc, Rectangle, Ellipse, RegularPolygon, Spline
from logic.dimensions import (
    AngularDimension,
    GeometryReference,
    LinearDimension,
    make_radial_dimension_from_object,
    make_reference_from_snap,
)
from logic.converter import CoordinateConverter
from logic.snap import SnapManager, SnapType
from ui.renderer import Renderer
from logic.styles import GOST_STYLES
from ui.style_manager import StyleManagerWindow
from logic.dxf_exporter import DxfExporter

class Callbacks:
    def __init__(self, root, state, view):
        self.root = root
        self.state = state
        self.view = view
        
        self.converter = None
        self.renderer = None
        self.snap_manager = None
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    def _is_dimension_mode(self, mode=None):
        mode = self.state.app_mode if mode is None else mode
        return str(mode).startswith("CREATING_DIMENSION_")

    def _get_dimension_mode_kind(self, mode=None):
        mode = self.state.app_mode if mode is None else mode
        return str(mode).replace("CREATING_DIMENSION_", "").lower()

    def _current_dimension_style(self):
        return self.state.dimension_styles.get(self.state.current_dimension_style_name)

    def _make_dimension_reference(self, x, y):
        snap_point = self.state.current_snap_point
        return make_reference_from_snap(snap_point, Point(x, y))

    def _selected_dimensions_count(self):
        return len(self.state.selected_dimensions)

    def _clear_dimension_creation_state(self):
        self.state.dimension_creation_refs = []
        self.state.dimension_creation_object = None
        self.state.preview_dimension = None
        self.state.dimension_grip_drag = None

    def _clear_tangent_creation_state(self):
        self.state.tangent_creation_circles = []
        self.state.preview_segment = None

    def _clear_all_selection(self):
        self.state.selected_segments = []
        self.state.selected_circles = []
        self.state.selected_arcs = []
        self.state.selected_rectangles = []
        self.state.selected_ellipses = []
        self.state.selected_polygons = []
        self.state.selected_splines = []
        self.state.selected_dimensions = []

    def _selected_non_dimension_objects(self):
        return (
            list(self.state.selected_segments)
            + list(self.state.selected_circles)
            + list(self.state.selected_arcs)
            + list(self.state.selected_rectangles)
            + list(self.state.selected_ellipses)
            + list(self.state.selected_polygons)
            + list(self.state.selected_splines)
        )

    def _clone_dimension_ref(self, ref):
        return GeometryReference(
            ref.kind,
            Point(ref.point.x, ref.point.y),
            source_object=ref.source_object,
            ref_kind=ref.ref_kind,
            ref_index=ref.ref_index,
        )

    def _selected_single_dimension(self):
        return self.state.selected_dimensions[0] if len(self.state.selected_dimensions) == 1 else None

    def _dimension_context_target(self):
        if self.state.editing_object is not None and self.state.editing_object_type == 'dimension':
            return self.state.editing_object
        return self._selected_single_dimension()

    def _sync_preview_dimension_from_editing_object(self):
        if (
            self.state.editing_object is not None
            and self.state.editing_object_type == 'dimension'
            and self.state.preview_dimension is not None
            and self.state.preview_dimension is not self.state.editing_object
        ):
            self.state.preview_dimension.copy_display_overrides_from(self.state.editing_object)

    def _set_dimension_swatch(self, swatch, color):
        swatch.config(bg=color or "#cccccc")

    def _set_dimension_entry_value(self, entry, value):
        prev_state = str(entry.cget("state"))
        if prev_state != "normal":
            entry.config(state="normal")
        entry.delete(0, tk.END)
        if value is not None:
            entry.insert(0, f"{float(value):.2f}")
        if prev_state != "normal":
            entry.config(state=prev_state)

    def _set_dimension_control_state(self, widget, enabled, readonly=False):
        try:
            widget.config(state="readonly" if enabled and readonly else ("normal" if enabled else "disabled"))
        except tk.TclError:
            widget.config(state=("normal" if enabled else "disabled"))

    def _selected_combobox_id(self, combobox, ids):
        idx = combobox.current()
        if 0 <= idx < len(ids):
            return ids[idx]
        return combobox.get().strip()

    def _selected_dimension_text_prefix(self):
        idx = self.view.dimension_text_prefix_combobox.current()
        if 0 <= idx < len(self.view.dimension_text_prefix_ids):
            return self.view.dimension_text_prefix_ids[idx]
        return None

    def _selected_dimension_text_suffix(self):
        idx = self.view.dimension_text_suffix_combobox.current()
        if 0 <= idx < len(self.view.dimension_text_suffix_ids):
            return self.view.dimension_text_suffix_ids[idx]
        return None

    def _sync_dimension_text_override_controls(self, dimension=None):
        self.view.dimension_text_override_entry.delete(0, tk.END)
        if dimension is not None and dimension.text_override:
            self.view.dimension_text_override_entry.insert(0, dimension.text_override)

        prefix = None if dimension is None else getattr(dimension, "text_prefix_override", None)
        suffix = None if dimension is None else getattr(dimension, "text_suffix_override", None)

        if prefix in self.view.dimension_text_prefix_ids:
            self.view.dimension_text_prefix_combobox.current(self.view.dimension_text_prefix_ids.index(prefix))
        else:
            self.view.dimension_text_prefix_combobox.current(0)

        if suffix in self.view.dimension_text_suffix_ids:
            self.view.dimension_text_suffix_combobox.current(self.view.dimension_text_suffix_ids.index(suffix))
        else:
            self.view.dimension_text_suffix_combobox.current(0)

    def _sync_dimension_appearance_controls(self, dimension=None):
        if dimension is None:
            self.view.dimension_extension_note_var.set("")
            self._set_dimension_swatch(self.view.dimension_ext_color_swatch, "#cccccc")
            self._set_dimension_swatch(self.view.dimension_dim_color_swatch, "#cccccc")
            self.view.dimension_ext_style_combobox.set("")
            self.view.dimension_dim_style_combobox.set("")
            self.view.dimension_arrow_type_combobox.set("")
            self.view.dimension_text_font_combobox.set("")
            self.view.dimension_text_position_combobox.set("")
            for entry in [
                self.view.dimension_ext_overrun_entry,
                self.view.dimension_dim_extension_entry,
                self.view.dimension_arrow_size_entry,
                self.view.dimension_text_gap_entry,
            ]:
                entry.delete(0, tk.END)
            self.view.dimension_text_height_combobox.set("")
            self.view.dimension_arrow_filled_var.set(True)
            controls = [
                (self.view.dimension_ext_style_combobox, True),
                (self.view.dimension_dim_style_combobox, True),
                (self.view.dimension_arrow_type_combobox, True),
                (self.view.dimension_text_font_combobox, True),
                (self.view.dimension_text_height_combobox, True),
                (self.view.dimension_text_position_combobox, True),
            ]
            for widget, readonly in controls:
                self._set_dimension_control_state(widget, False, readonly=readonly)
            for widget in [
                self.view.dimension_ext_overrun_entry,
                self.view.dimension_dim_extension_entry,
                self.view.dimension_arrow_size_entry,
                self.view.dimension_text_gap_entry,
                self.view.dimension_arrow_filled_check,
            ]:
                self._set_dimension_control_state(widget, False)
            return

        uses_extensions = dimension.dimension_type not in ("radius", "diameter")
        self.view.dimension_extension_note_var.set("" if uses_extensions else "Для радиуса и диаметра выносные линии не используются.")

        for widget, enabled, readonly in [
            (self.view.dimension_ext_style_combobox, uses_extensions, True),
            (self.view.dimension_dim_style_combobox, True, True),
            (self.view.dimension_arrow_type_combobox, True, True),
            (self.view.dimension_text_font_combobox, True, True),
            (self.view.dimension_text_height_combobox, True, True),
            (self.view.dimension_text_position_combobox, True, True),
        ]:
            self._set_dimension_control_state(widget, enabled, readonly=readonly)

        for widget, enabled in [
            (self.view.dimension_ext_overrun_entry, uses_extensions),
            (self.view.dimension_dim_extension_entry, True),
            (self.view.dimension_arrow_size_entry, True),
            (self.view.dimension_text_gap_entry, True),
            (self.view.dimension_arrow_filled_check, True),
        ]:
            self._set_dimension_control_state(widget, enabled)

        self._set_dimension_swatch(self.view.dimension_ext_color_swatch, dimension._effective_extension_line_color(self.state))
        self._set_dimension_swatch(self.view.dimension_dim_color_swatch, dimension._effective_dim_line_color(self.state))
        self.view.set_dimension_line_style_selection(self.view.dimension_ext_style_combobox, dimension._effective_extension_line_style_name(self.state))
        self.view.set_dimension_line_style_selection(self.view.dimension_dim_style_combobox, dimension._effective_dim_line_style_name(self.state))
        self._set_dimension_entry_value(self.view.dimension_ext_overrun_entry, dimension._effective_extension_overrun_mm(self.state))
        self._set_dimension_entry_value(self.view.dimension_dim_extension_entry, dimension._effective_dim_line_extension_mm(self.state))
        self._set_dimension_entry_value(self.view.dimension_arrow_size_entry, dimension._effective_arrow_size_mm(self.state))
        self._set_dimension_entry_value(self.view.dimension_text_gap_entry, dimension._effective_text_gap_mm(self.state))
        self.view.set_dimension_text_height_selection(dimension._effective_text_height_mm(self.state))
        self.view.set_dimension_option_selection(
            self.view.dimension_arrow_type_combobox,
            self.view.dimension_arrow_type_ids,
            self.view.dimension_arrow_type_names,
            dimension._effective_arrow_type(self.state),
        )
        self.view.dimension_arrow_filled_var.set(dimension._effective_arrow_filled(self.state))
        self.view.set_dimension_option_selection(
            self.view.dimension_text_position_combobox,
            self.view.dimension_text_position_ids,
            self.view.dimension_text_position_names,
            dimension._effective_text_position_mode(self.state),
        )
        font_name = dimension._effective_text_font_family(self.state)
        if font_name in self.view.dimension_font_names:
            self.view.dimension_text_font_combobox.current(self.view.dimension_font_names.index(font_name))
        else:
            self.view.dimension_text_font_combobox.set(font_name)

    def _update_document_path_display(self):
        if self.view and hasattr(self.view, "set_document_path"):
            self.view.set_document_path(self.state.current_dxf_path, self.state.current_dxf_saved_at)

    def _ask_dxf_save_path(self, title="Сохранить DXF"):
        current_path = self.state.current_dxf_path
        options = {
            "title": title,
            "defaultextension": ".dxf",
            "filetypes": [("DXF файлы", "*.dxf"), ("Все файлы", "*.*")],
        }
        if current_path:
            current_dir = os.path.dirname(current_path)
            if current_dir:
                options["initialdir"] = current_dir
            options["initialfile"] = os.path.basename(current_path)
        return filedialog.asksaveasfilename(**options)

    def _save_dxf(self, filepath):
        exporter = DxfExporter()
        exporter.export(self.state, filepath, self.view.root)
        self.state.current_dxf_path = filepath
        self.state.current_dxf_saved_at = datetime.now()
        self._update_document_path_display()

    def on_save_dxf(self, event=None):
        """Быстрое сохранение DXF: первый раз спрашивает имя, потом перезаписывает файл."""
        filepath = self.state.current_dxf_path
        if not filepath:
            filepath = self._ask_dxf_save_path()
        if not filepath:
            return "break"
        try:
            self._save_dxf(filepath)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить DXF:\n{e}")
        return "break"

    def on_export_dxf(self):
        """Экспорт чертежа в новый файл DXF."""
        filepath = self._ask_dxf_save_path("Экспорт в DXF как")
        if not filepath:
            return
        try:
            self._save_dxf(filepath)
            messagebox.showinfo("Экспорт DXF", f"Файл успешно сохранён:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", f"Не удалось сохранить DXF:\n{e}")

    def on_import_dxf(self):
        """Импорт чертежа из файла DXF."""
        from logic.dxf_importer import DxfImporter
        
        filepath = filedialog.askopenfilename(
            title="Импорт из DXF",
            filetypes=[("DXF файлы", "*.dxf"), ("Все файлы", "*.*")]
        )
        if not filepath:
            return
        try:
            importer = DxfImporter()
            importer.import_dxf(self.state, filepath, self.view.root)
            self.state.current_dxf_path = filepath
            self.state.current_dxf_saved_at = None
            self._update_document_path_display()
            
            # Обновляем UI после импорта
            self.view.refresh_layers_list(self.state)
            self._sync_ui_with_selection()
            self._refresh_settings_context_panel()
            
            # Зумируем камеру на импортированный чертеж (Phase 6)
            self.on_fit_to_view()
            
            messagebox.showinfo("Импорт DXF", "Файл успешно импортирован!")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", f"Не удалось прочитать DXF:\n{e}")

    def _refresh_settings_context_panel(self, *, auto_switch_tab=False):

        if not self.view:
            return

        def _select_tab(tab_widget):
            nb = getattr(self.view, "settings_notebook", None)
            if not nb or not tab_widget:
                return
            try:
                nb.select(tab_widget)
            except Exception:
                return

        is_editing = self.state.editing_object is not None
        
        if is_editing:
            edit_panels = {
                'segment': ("segment", "Редактирование: Отрезок"),
                'circle': ("circle", "Редактирование: Окружность"),
                'arc': ("arc", "Редактирование: Дуга"),
                'rectangle': ("rectangle", "Редактирование: Прямоугольник"),
                'ellipse': ("ellipse", "Редактирование: Эллипс"),
                'polygon': ("polygon", "Редактирование: Многоугольник"),
                'spline': ("spline", "Редактирование: Сплайн"),
                'dimension': ("dimension", "Редактирование: Размер"),
            }
            if self.state.editing_object_type in edit_panels:
                key, title = edit_panels[self.state.editing_object_type]
                self.view.set_context_panel(key, title)
                if auto_switch_tab:
                    _select_tab(getattr(self.view, "context_tab", None))
            else:
                self.view.set_context_panel(None, "—")
            return

        total_selected = (
            len(self.state.selected_segments)
            + len(self.state.selected_circles)
            + len(self.state.selected_arcs)
            + len(self.state.selected_rectangles)
            + len(self.state.selected_ellipses)
            + len(self.state.selected_polygons)
            + len(self.state.selected_splines)
            + len(self.state.selected_dimensions)
        )

        if total_selected == 1:
            if self.state.selected_segments:
                self.view.set_context_panel("segment", "Выбрано: Отрезок")
            elif self.state.selected_circles:
                self.view.set_context_panel("circle", "Выбрано: Окружность")
            elif self.state.selected_arcs:
                self.view.set_context_panel("arc", "Выбрано: Дуга")
            elif self.state.selected_rectangles:
                self.view.set_context_panel("rectangle", "Выбрано: Прямоугольник")
            elif self.state.selected_ellipses:
                self.view.set_context_panel("ellipse", "Выбрано: Эллипс")
            elif self.state.selected_polygons:
                self.view.set_context_panel("polygon", "Выбрано: Многоугольник")
            elif self.state.selected_splines:
                self.view.set_context_panel("spline", "Выбрано: Сплайн")
            elif self.state.selected_dimensions:
                self.view.set_context_panel("dimension", "Выбрано: Размер")
            else:
                self.view.set_context_panel(None, "—")
                return
            return

        if total_selected > 1:
            self.view.set_context_panel(None, "Выбрано: несколько объектов")
            return

        mode_to_panel = {
            "CREATING_SEGMENT": ("segment", "Создание: Отрезок"),
            "CREATING_TANGENT_SEGMENT": ("segment", "Создание: Касательная"),
            "CREATING_CIRCLE": ("circle", "Создание: Окружность"),
            "CREATING_ARC": ("arc", "Создание: Дуга"),
            "CREATING_RECTANGLE": ("rectangle", "Создание: Прямоугольник"),
            "CREATING_ELLIPSE": ("ellipse", "Создание: Эллипс"),
            "CREATING_POLYGON": ("polygon", "Создание: Многоугольник"),
            "CREATING_SPLINE": ("spline", "Создание: Сплайн"),
            "CREATING_DIMENSION_HORIZONTAL": ("dimension", "Создание: Линейный размер"),
            "CREATING_DIMENSION_VERTICAL": ("dimension", "Создание: Вертикальный размер"),
            "CREATING_DIMENSION_ALIGNED": ("dimension", "Создание: Выровненный размер"),
            "CREATING_DIMENSION_RADIUS": ("dimension", "Создание: Радиус"),
            "CREATING_DIMENSION_DIAMETER": ("dimension", "Создание: Диаметр"),
            "CREATING_DIMENSION_ANGULAR": ("dimension", "Создание: Угловой размер"),
        }
        if self.state.app_mode in mode_to_panel:
            key, title = mode_to_panel[self.state.app_mode]
            self.view.set_context_panel(key, title)
            if auto_switch_tab:
                _select_tab(getattr(self.view, "context_tab", None))
        else:
            self.view.set_context_panel(None, "—")

    def initialize_view(self):
        self.converter = CoordinateConverter(self.state, self.view.canvas)
        self.renderer = Renderer(self.view.canvas, self.state, self.converter)
        self.snap_manager = SnapManager(self.state)
        
        self.view.canvas.config(background=self.state.bg_color)
        self.view.bg_swatch.config(background=self.state.bg_color)
        self.view.grid_swatch.config(background=self.state.grid_color)
        self.view.segment_swatch.config(background=self.state.current_color)
        
        self.view.update_style_preview(self.state.current_style_name)
        self.view.refresh_dimension_style_combobox_values(self.state.dimension_styles)
        self.view.refresh_dimension_line_style_combobox_values(self.state.line_styles)
        self.view.set_dimension_style_selection(self.state.current_dimension_style_name)

        self.view.circle_method.set(self.state.circle_creation_method)
        self.view.arc_method.set(self.state.arc_creation_method)
        self.view._update_arc_params_ui()
        self.view.rect_method.set(self.state.rectangle_creation_method)
        self.view.rect_corner_type.set(self.state.rectangle_corner_type)
        self.view.rect_corner_value_entry.delete(0, tk.END)
        if self.state.rectangle_corner_value:
            self.view.rect_corner_value_entry.insert(0, f"{self.state.rectangle_corner_value:.2f}")
        self.view._update_rectangle_params_ui()
        self.view.ellipse_method.set(self.state.ellipse_creation_method)
        self.view.polygon_method.set(self.state.polygon_creation_method)
        self.view.polygon_variant.set(self.state.polygon_variant)
        self.view.polygon_sides_var.set(str(self.state.polygon_sides))

        self.view.refresh_layers_list(self.state)
        self._update_document_path_display()

        self.set_app_state(self.state.app_mode)

    def set_app_state(self, mode):
        prev_mode = self.state.app_mode
        self.state.app_mode = mode
        is_creating_segment = (mode == 'CREATING_SEGMENT')
        is_creating_tangent_segment = (mode == 'CREATING_TANGENT_SEGMENT')
        is_creating_circle = mode.startswith('CREATING_CIRCLE')
        is_creating_arc = mode.startswith('CREATING_ARC')
        is_creating_rectangle = mode.startswith('CREATING_RECTANGLE')
        is_creating_ellipse = mode.startswith('CREATING_ELLIPSE')
        is_creating_polygon = mode.startswith('CREATING_POLYGON')
        is_creating_spline = mode.startswith('CREATING_SPLINE')
        is_creating_dimension = mode.startswith('CREATING_DIMENSION')
        is_creating = (
            is_creating_segment
            or is_creating_tangent_segment
            or is_creating_circle
            or is_creating_arc
            or is_creating_rectangle
            or is_creating_ellipse
            or is_creating_polygon
            or is_creating_spline
            or is_creating_dimension
        )
        is_panning = (mode == 'PANNING')

        if is_creating_segment or is_creating_tangent_segment:
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
            self.state.preview_dimension = None
        elif is_creating_dimension:
            self.state.preview_segment = None
            self.state.preview_circle = None
            self.state.preview_arc = None
            self.state.preview_rectangle = None
            self.state.preview_ellipse = None
            self.state.preview_polygon = None
            self.state.preview_spline = None

        entered_creating = (not str(prev_mode).startswith("CREATING_")) and str(mode).startswith("CREATING_")
        is_editing = self.state.editing_object is not None
        self._refresh_settings_context_panel(auto_switch_tab=(entered_creating or is_editing))

        entry_state = 'normal' if is_creating else 'disabled'
        entries = [self.view.p1_x_entry, self.view.p1_y_entry, self.view.p2_x_entry, self.view.p2_y_entry]

        circle_entries = [
            self.view.circle_center_x_entry, self.view.circle_center_y_entry,
            self.view.circle_param_entry, self.view.circle_p2_x_entry,
            self.view.circle_p2_y_entry, self.view.circle_p3_x_entry,
            self.view.circle_p3_y_entry
        ]

        arc_entries = [
            self.view.arc_p1_x_entry, self.view.arc_p1_y_entry,
            self.view.arc_p2_x_entry, self.view.arc_p2_y_entry,
            self.view.arc_p3_x_entry, self.view.arc_p3_y_entry,
            self.view.arc_center_x_entry, self.view.arc_center_y_entry,
            self.view.arc_radius_entry, self.view.arc_start_angle_entry, self.view.arc_end_angle_entry
        ]

        rect_entries = [
            self.view.rect_p1_x_entry, self.view.rect_p1_y_entry,
            self.view.rect_p2_x_entry, self.view.rect_p2_y_entry,
            self.view.rect_corner_x_entry, self.view.rect_corner_y_entry,
            self.view.rect_width_entry, self.view.rect_height_entry,
            self.view.rect_center_x_entry, self.view.rect_center_y_entry,
            self.view.rect_center_w_entry, self.view.rect_center_h_entry,
            self.view.rect_corner_value_entry
        ]

        ellipse_entries = [
            self.view.ellipse_center_x_entry, self.view.ellipse_center_y_entry,
            self.view.ellipse_a_x_entry, self.view.ellipse_a_y_entry,
            self.view.ellipse_b_x_entry, self.view.ellipse_b_y_entry
        ]
        polygon_entries = [
            self.view.polygon_center_x_entry, self.view.polygon_center_y_entry,
            self.view.polygon_radius_entry, self.view.polygon_sides_spin
        ]
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
            for entry in circle_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            for entry in arc_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            for entry in rect_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            for entry in ellipse_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            for entry in polygon_entries:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
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
            self.state.preview_dimension = None
            self.state.active_p1 = None
            self.state.active_p2 = None
            self.state.active_p3 = None
            self.state.active_p4 = None
            self.state.spline_control_points = []
            self._clear_dimension_creation_state()
            self._clear_tangent_creation_state()
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
        elif is_creating_tangent_segment:
            for entry in entries: entry.config(state='disabled')
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='disabled')
            for entry in ellipse_entries: entry.config(state='disabled')
            for entry in polygon_entries: entry.config(state='disabled')
            for entry in spline_entries: entry.config(state='disabled')
            self.state.points_clicked = len(self.state.tangent_creation_circles)
            self.root.bind("<Return>", self.finalize_segment)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_tangent_segment)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_circle:
            for entry in entries: entry.config(state=entry_state)
            for entry in circle_entries: entry.config(state='normal')
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_circle)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_circle)
            self.view.canvas.config(cursor="crosshair") 
        elif is_creating_arc:
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
            self.view.canvas.bind("<Button-1>", self._on_spline_mouse_down)
            self.view.canvas.bind("<B1-Motion>", self._on_spline_mouse_drag)
            self.view.canvas.bind("<ButtonRelease-1>", self._on_spline_mouse_up)
            self.view.canvas.config(cursor="crosshair")
        elif is_creating_dimension:
            for entry in entries: entry.config(state='disabled')
            for entry in circle_entries: entry.config(state='disabled')
            for entry in arc_entries: entry.config(state='disabled')
            for entry in rect_entries: entry.config(state='disabled')
            for entry in ellipse_entries: entry.config(state='disabled')
            for entry in polygon_entries: entry.config(state='disabled')
            for entry in spline_entries: entry.config(state='disabled')
            self.state.points_clicked = len(self.state.dimension_creation_refs)
            self.root.bind("<Return>", self.finalize_dimension)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click_dimension)
            self.view.canvas.config(cursor="crosshair")
            
        elif is_panning:
            self.view.canvas.bind("<Button-1>", self.on_mouse_press)
            self.view.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.view.canvas.config(cursor="fleur")

        else:
            self.view.canvas.bind("<Button-1>", self.on_selection_click)
            self.view.canvas.bind("<B1-Motion>", self.on_idle_drag)
            self.view.canvas.bind("<ButtonRelease-1>", self.on_idle_release)
            self.view.canvas.config(cursor="arrow")
        
        self.redraw_all()

    def _find_dimension_grip_hit(self, event):
        if len(self.state.selected_dimensions) != 1:
            return None

        dimension = self.state.selected_dimensions[0]
        grips = dimension.grip_points(self.state)
        for grip_name, point in grips.items():
            sx, sy = self.converter.world_to_screen(point.x, point.y)
            if abs(event.x - sx) <= 10 and abs(event.y - sy) <= 10:
                return dimension, grip_name
        return None

    def on_selection_click(self, event):
        grip_hit = self._find_dimension_grip_hit(event)
        if grip_hit:
            dimension, grip_name = grip_hit
            self.state.dimension_grip_drag = {"dimension": dimension, "grip": grip_name}
            return

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
        found_dimension = None

        for segment in self.state.segments:
            if not self.state.is_layer_visible(segment.layer): continue
            dist = segment.distance_to_point(wx, wy)
            if dist < hit_threshold_world:
                found_segment = segment
                break

        if not found_segment:
            for circle in self.state.circles:
                if not self.state.is_layer_visible(circle.layer): continue
                dist = circle.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_circle = circle
                    break

        if not found_segment and not found_circle:
            for arc in self.state.arcs:
                if not self.state.is_layer_visible(arc.layer): continue
                dist = arc.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_arc = arc
                    break

        if not found_segment and not found_circle and not found_arc:
            for rect in self.state.rectangles:
                if not self.state.is_layer_visible(rect.layer): continue
                dist = rect.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_rectangle = rect
                    break

        if not found_segment and not found_circle and not found_arc and not found_rectangle:
            for ellipse in self.state.ellipses:
                if not self.state.is_layer_visible(ellipse.layer): continue
                dist = ellipse.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_ellipse = ellipse
                    break
        if not found_segment and not found_circle and not found_arc and not found_rectangle and not found_ellipse:
            for poly in self.state.polygons:
                if not self.state.is_layer_visible(poly.layer): continue
                dist = poly.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_polygon = poly
                    break
        if not found_segment and not found_circle and not found_arc and not found_rectangle and not found_ellipse and not found_polygon:
            for spline in self.state.splines:
                if not self.state.is_layer_visible(spline.layer): continue
                dist = spline.distance_to_point(wx, wy)
                if dist < hit_threshold_world:
                    found_spline = spline
                    break
        if not found_segment and not found_circle and not found_arc and not found_rectangle and not found_ellipse and not found_polygon and not found_spline:
            for dimension in self.state.dimensions:
                if not self.state.is_layer_visible(dimension.layer): continue
                dist = dimension.distance_to_point(wx, wy, self.state)
                if dist < hit_threshold_world * 1.5:
                    found_dimension = dimension
                    break

        ctrl_pressed = (event.state & 0x0004)

        if found_segment:
            if ctrl_pressed:
                if found_segment in self.state.selected_segments:
                    self.state.selected_segments.remove(found_segment)
                else:
                    self.state.selected_segments.append(found_segment)
            else:
                self.state.selected_segments = [found_segment]
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_circle:
            if ctrl_pressed:
                if found_circle in self.state.selected_circles:
                    self.state.selected_circles.remove(found_circle)
                else:
                    self.state.selected_circles.append(found_circle)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = [found_circle]
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_arc:
            if ctrl_pressed:
                if found_arc in self.state.selected_arcs:
                    self.state.selected_arcs.remove(found_arc)
                else:
                    self.state.selected_arcs.append(found_arc)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = [found_arc]
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_ellipse:
            if ctrl_pressed:
                if found_ellipse in self.state.selected_ellipses:
                    self.state.selected_ellipses.remove(found_ellipse)
                else:
                    self.state.selected_ellipses.append(found_ellipse)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = [found_ellipse]
                self.state.selected_polygons = []
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_rectangle:
            if ctrl_pressed:
                if found_rectangle in self.state.selected_rectangles:
                    self.state.selected_rectangles.remove(found_rectangle)
                else:
                    self.state.selected_rectangles.append(found_rectangle)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = [found_rectangle]
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_polygon:
            if ctrl_pressed:
                if found_polygon in self.state.selected_polygons:
                    self.state.selected_polygons.remove(found_polygon)
                else:
                    self.state.selected_polygons.append(found_polygon)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = [found_polygon]
                self.state.selected_splines = []
                self.state.selected_dimensions = []
        elif found_spline:
            if ctrl_pressed:
                if found_spline in self.state.selected_splines:
                    self.state.selected_splines.remove(found_spline)
                else:
                    self.state.selected_splines.append(found_spline)
            else:
                self.state.selected_segments = []
                self.state.selected_circles = []
                self.state.selected_arcs = []
                self.state.selected_rectangles = []
                self.state.selected_ellipses = []
                self.state.selected_polygons = []
                self.state.selected_splines = [found_spline]
                self.state.selected_dimensions = []
        elif found_dimension:
            if ctrl_pressed:
                if found_dimension in self.state.selected_dimensions:
                    self.state.selected_dimensions.remove(found_dimension)
                else:
                    self.state.selected_dimensions.append(found_dimension)
            else:
                self._clear_all_selection()
                self.state.selected_dimensions = [found_dimension]
        else:
            if not ctrl_pressed:
                self._clear_all_selection()

        self._sync_ui_with_selection()
        self._refresh_settings_context_panel()
        self.redraw_all()

    def _sync_ui_with_selection(self):
        editing_dimension = (
            self.state.editing_object
            if self.state.editing_object is not None and self.state.editing_object_type == 'dimension'
            else None
        )

        if editing_dimension is not None:
            geometry = editing_dimension.resolve_geometry(self.state)
            type_map = {
                "linear": "Линейный размер",
                "radius": "Радиальный размер",
                "diameter": "Диаметральный размер",
                "angular": "Угловой размер",
            }
            self.state.current_dimension_style_name = editing_dimension.dimension_style_name
            self.view.set_dimension_style_selection(editing_dimension.dimension_style_name)
            self.view.dimension_type_var.set(type_map.get(editing_dimension.dimension_type, "Размер"))
            self.view.dimension_value_var.set(
                f"Значение: {geometry.get('text', '—') if geometry else '—'}"
            )
            self.view.dimension_layer_var.set(f"Слой: {editing_dimension.layer}")
            self._sync_dimension_text_override_controls(editing_dimension)
            self._sync_dimension_appearance_controls(editing_dimension)
            self._refresh_settings_context_panel()
            return

        sel_segments = self.state.selected_segments
        sel_circles = self.state.selected_circles
        sel_arcs = self.state.selected_arcs
        sel_rectangles = self.state.selected_rectangles
        sel_ellipses = self.state.selected_ellipses
        sel_polygons = self.state.selected_polygons
        sel_splines = self.state.selected_splines
        sel_dimensions = self.state.selected_dimensions

        all_selected = (
            list(sel_segments) + list(sel_circles) + list(sel_arcs) +
            list(sel_rectangles) + list(sel_ellipses) + list(sel_polygons) + list(sel_splines) + list(sel_dimensions)
        )

        if not all_selected:
            style_obj = GOST_STYLES.get(self.state.current_style_name)
            if style_obj:
                self.view.set_style_selection(style_obj.name)
                self.view.segment_swatch.config(bg=self.state.current_color)
            self.view.set_dimension_style_selection(self.state.current_dimension_style_name)
            self.view.dimension_type_var.set("—")
            self.view.dimension_value_var.set("—")
            self.view.dimension_layer_var.set("Слой: —")
            self._sync_dimension_text_override_controls()
            self._sync_dimension_appearance_controls()
            self._refresh_settings_context_panel()
            return

        unique_styles = set()
        unique_colors = set()
        for obj in all_selected:
            if hasattr(obj, 'style_name'):
                unique_styles.add(obj.style_name)
            unique_colors.add(obj.color)

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            self.state.current_style_name = style_name
        elif not unique_styles:
            pass
        else:
            self.view.set_style_selection("Разные")

        if len(unique_colors) == 1:
            color = list(unique_colors)[0]
            self.view.segment_swatch.config(bg=color)
            self.state.current_color = color
        else:
            self.view.segment_swatch.config(bg="#cccccc")

        if sel_dimensions and len(all_selected) == len(sel_dimensions):
            unique_dim_styles = {dim.dimension_style_name for dim in sel_dimensions}
            if len(unique_dim_styles) == 1:
                dim_style_name = list(unique_dim_styles)[0]
                self.state.current_dimension_style_name = dim_style_name
                self.view.set_dimension_style_selection(dim_style_name)
            else:
                self.view.set_dimension_style_selection("Разные")

            if len(sel_dimensions) == 1:
                dimension = sel_dimensions[0]
                geometry = dimension.resolve_geometry(self.state)
                type_map = {
                    "linear": "Линейный размер",
                    "radius": "Радиальный размер",
                    "diameter": "Диаметральный размер",
                    "angular": "Угловой размер",
                }
                self.view.dimension_type_var.set(type_map.get(dimension.dimension_type, "Размер"))
                self.view.dimension_value_var.set(
                    f"Значение: {geometry.get('text', '—') if geometry else '—'}"
                )
                self.view.dimension_layer_var.set(f"Слой: {dimension.layer}")
                self._sync_dimension_text_override_controls(dimension)
                self._sync_dimension_appearance_controls(dimension)
            else:
                self.view.dimension_type_var.set("Несколько размеров")
                self.view.dimension_value_var.set("Значение: Разные")
                self.view.dimension_layer_var.set("Слой: Разные")
                self._sync_dimension_text_override_controls()
                self._sync_dimension_appearance_controls()
        else:
            self.view.dimension_type_var.set("—")
            self.view.dimension_value_var.set("—")
            self.view.dimension_layer_var.set("Слой: —")
            self._sync_dimension_text_override_controls()
            self._sync_dimension_appearance_controls()

        self._refresh_settings_context_panel()

    def _sync_ui_with_segments(self, sel_segments):

        unique_styles = {seg.style_name for seg in sel_segments}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_segments[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def _sync_ui_with_circles(self, sel_circles):

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

        unique_styles = {sp.style_name for sp in sel_splines}

        if len(unique_styles) == 1:
            style_name = list(unique_styles)[0]
            self.view.set_style_selection(style_name)
            first_color = sel_splines[0].color
            self.view.segment_swatch.config(bg=first_color)

            self.state.current_style_name = style_name
            self.state.current_color = first_color
        else:
            self.view.set_style_selection("Разные")
            self.view.segment_swatch.config(bg="#cccccc")

    def on_style_selected(self, event=None):
        idx = self.view.style_combobox.current()
        
        if idx == -1:
            return 

        try:
            new_style_name = self.view.style_ids[idx]
        except IndexError:
            return

        self.state.current_style_name = new_style_name

        for seg in self.state.selected_segments:
            seg.style_name = new_style_name
        for circle in self.state.selected_circles:
            circle.style_name = new_style_name
        for arc in self.state.selected_arcs:
            arc.style_name = new_style_name
        for rect in self.state.selected_rectangles:
            rect.style_name = new_style_name
        for ellipse in self.state.selected_ellipses:
            ellipse.style_name = new_style_name
        for poly in self.state.selected_polygons:
            poly.style_name = new_style_name
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

    def on_dimension_style_selected(self, event=None):
        if event is not None and event.widget is self.view.dimension_context_style_combobox:
            idx = self.view.dimension_context_style_combobox.current()
        elif event is not None and event.widget is self.view.dimension_style_combobox:
            idx = self.view.dimension_style_combobox.current()
        else:
            idx = self.view.dimension_style_combobox.current()
            if idx == -1:
                idx = self.view.dimension_context_style_combobox.current()
        if idx == -1:
            return

        try:
            new_style_name = self.view.dimension_style_ids[idx]
        except IndexError:
            return

        self.state.current_dimension_style_name = new_style_name
        for dimension in self.state.selected_dimensions:
            dimension.activate_dimension_style(new_style_name)

        if self.state.preview_dimension:
            self.state.preview_dimension.activate_dimension_style(new_style_name)

        if self.state.editing_object is not None and self.state.editing_object_type == 'dimension':
            self.state.editing_object.activate_dimension_style(new_style_name)
            self._sync_preview_dimension_from_editing_object()

        self._sync_ui_with_selection()
        self.redraw_all()

    def on_new_segment_mode(self, event=None):
        self._clear_tangent_creation_state()
        self.set_app_state('CREATING_SEGMENT')

        self.view.p1_x_entry.delete(0, tk.END)
        self.view.p1_y_entry.delete(0, tk.END)
        self.view.p2_x_entry.delete(0, tk.END)
        self.view.p2_y_entry.delete(0, tk.END)

        self.view.p1_x_entry.focus_set()

    def on_new_tangent_segment_mode(self, event=None):
        self._clear_tangent_creation_state()
        self.set_app_state('CREATING_TANGENT_SEGMENT')
        self.view.canvas.focus_set()

    def on_new_circle_mode(self, event=None):
        self.set_app_state('CREATING_CIRCLE')

        self.view.circle_center_x_entry.delete(0, tk.END)
        self.view.circle_center_y_entry.delete(0, tk.END)
        self.view.circle_param_entry.delete(0, tk.END)
        self.view.circle_p2_x_entry.delete(0, tk.END)
        self.view.circle_p2_y_entry.delete(0, tk.END)
        self.view.circle_p3_x_entry.delete(0, tk.END)
        self.view.circle_p3_y_entry.delete(0, tk.END)

        method = self.state.circle_creation_method
        if method in ['center_radius', 'center_diameter']:
            self.view.circle_center_x_entry.focus_set()
        else:
            self.view.circle_center_x_entry.focus_set()

    def on_new_arc_mode(self, event=None):
        self.set_app_state('CREATING_ARC')

        for entry in [
            self.view.arc_p1_x_entry, self.view.arc_p1_y_entry,
            self.view.arc_p2_x_entry, self.view.arc_p2_y_entry,
            self.view.arc_p3_x_entry, self.view.arc_p3_y_entry,
            self.view.arc_center_x_entry, self.view.arc_center_y_entry,
            self.view.arc_radius_entry, self.view.arc_start_angle_entry, self.view.arc_end_angle_entry
        ]:
            entry.delete(0, tk.END)

        method = self.state.arc_creation_method
        if method == 'three_points':
            self.view.arc_p1_x_entry.focus_set()
        else:
            self.view.arc_center_x_entry.focus_set()

    def on_new_rectangle_mode(self, event=None):
        self.set_app_state('CREATING_RECTANGLE')

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

        for entry in [
            self.view.ellipse_center_x_entry, self.view.ellipse_center_y_entry,
            self.view.ellipse_a_x_entry, self.view.ellipse_a_y_entry,
            self.view.ellipse_b_x_entry, self.view.ellipse_b_y_entry
        ]:
            entry.delete(0, tk.END)

        self.view.ellipse_center_x_entry.focus_set()

    def on_new_polygon_mode(self, event=None):
        self.set_app_state('CREATING_POLYGON')

        self.state.polygon_start_angle = 0.0
        for entry in [
            self.view.polygon_center_x_entry, self.view.polygon_center_y_entry,
            self.view.polygon_radius_entry
        ]:
            entry.delete(0, tk.END)
        self.view.polygon_sides_var.set(str(self.state.polygon_sides))

    def on_new_spline_mode(self, event=None):
        self.set_app_state('CREATING_SPLINE')
        self.state.spline_control_points = []
        self.state.preview_spline = None
        self.state.selected_spline_point_index = None
        self.state.dragging_spline_point_index = None
        self.view.spline_point_x_entry.delete(0, tk.END)
        self.view.spline_point_y_entry.delete(0, tk.END)
        self._update_spline_points_listbox()
        self.view.spline_point_x_entry.focus_set()

        self.view.polygon_center_x_entry.focus_set()

    def on_new_linear_dimension_mode(self, mode="aligned", event=None):
        mode_map = {
            "horizontal": "CREATING_DIMENSION_HORIZONTAL",
            "vertical": "CREATING_DIMENSION_VERTICAL",
            "aligned": "CREATING_DIMENSION_ALIGNED",
        }
        self._clear_dimension_creation_state()
        self.set_app_state(mode_map.get(mode, "CREATING_DIMENSION_ALIGNED"))
        self.view.canvas.focus_set()

    def on_new_radius_dimension_mode(self, event=None):
        self._clear_dimension_creation_state()
        self.set_app_state("CREATING_DIMENSION_RADIUS")
        self.view.canvas.focus_set()

    def on_new_diameter_dimension_mode(self, event=None):
        self._clear_dimension_creation_state()
        self.set_app_state("CREATING_DIMENSION_DIAMETER")
        self.view.canvas.focus_set()

    def on_new_angular_dimension_mode(self, event=None):
        self._clear_dimension_creation_state()
        self.set_app_state("CREATING_DIMENSION_ANGULAR")
        self.view.canvas.focus_set()

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
            start_angle = getattr(self.state, 'polygon_start_angle', 0.0) or 0.0
            self.state.preview_polygon = RegularPolygon.from_center_radius(
                center, radius, sides,
                variant=variant,
                start_angle=start_angle,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
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
        self.redraw_all()

    def update_preview_dimension(self, event=None):
        refs = self.state.dimension_creation_refs
        kind = self._get_dimension_mode_kind()
        self.state.preview_dimension = None
        target_layer = (
            self.state.editing_object.layer
            if self.state.editing_object is not None and self.state.editing_object_type == 'dimension'
            else self.state.active_layer
        )

        try:
            if kind in ("horizontal", "vertical", "aligned") and len(refs) >= 3:
                self.state.preview_dimension = LinearDimension(
                    refs[0],
                    refs[1],
                    refs[2],
                    mode=kind,
                    color=self.state.current_color,
                    layer=target_layer,
                    dimension_style_name=self.state.current_dimension_style_name,
                )
            elif kind in ("radius", "diameter") and self.state.dimension_creation_object is not None and len(refs) >= 1:
                prefix = "R" if kind == "radius" else "⌀"
                self.state.preview_dimension = make_radial_dimension_from_object(
                    self.state.dimension_creation_object,
                    refs[0].resolve(),
                    prefix=prefix,
                    color=self.state.current_color,
                    layer=target_layer,
                    dimension_style_name=self.state.current_dimension_style_name,
                )
            elif kind == "angular" and len(refs) >= 4:
                self.state.preview_dimension = AngularDimension(
                    refs[0],
                    refs[1],
                    refs[2],
                    refs[3],
                    color=self.state.current_color,
                    layer=target_layer,
                    dimension_style_name=self.state.current_dimension_style_name,
                )
        except Exception:
            self.state.preview_dimension = None

        if self.state.preview_dimension and self.state.editing_object is not None and self.state.editing_object_type == 'dimension':
            self.state.preview_dimension.copy_display_overrides_from(self.state.editing_object)

        self.redraw_all()

    def finalize_dimension(self, event=None):
        if not self.state.preview_dimension:
            return

        if self.state.editing_object and self.state.editing_object_type == 'dimension':
            idx = self.state.dimensions.index(self.state.editing_object)
            self.state.dimensions[idx] = self.state.preview_dimension
            self.state.selected_dimensions = [self.state.preview_dimension]
            self.state.editing_object = None
            self.state.editing_object_type = None
        else:
            self.state.dimensions.append(self.state.preview_dimension)
            self.state.selected_dimensions = [self.state.preview_dimension]

        self._clear_dimension_creation_state()
        self.set_app_state('IDLE')

    def finalize_segment(self, event=None):
        if self.state.preview_segment:
            if self.state.editing_object and self.state.editing_object_type == 'segment':
                segment = self.state.editing_object
                segment.p1 = Point(self.state.preview_segment.p1.x, self.state.preview_segment.p1.y)
                segment.p2 = Point(self.state.preview_segment.p2.x, self.state.preview_segment.p2.y)
                segment.style_name = self.state.current_style_name
                segment.color = self.state.current_color
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_segment = Segment(
                    self.state.preview_segment.p1,
                    self.state.preview_segment.p2,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_segment.layer = self.state.active_layer
                self.state.segments.append(final_segment)
            self._clear_tangent_creation_state()
            self.set_app_state('IDLE')

    def finalize_circle(self, event=None):
        if self.state.preview_circle:
            preview = self.state.preview_circle
            if self.state.editing_object and self.state.editing_object_type == 'circle':
                circle = self.state.editing_object
                circle.center = Point(preview.center.x, preview.center.y)
                circle.radius = preview.radius
                circle.style_name = self.state.current_style_name
                circle.color = self.state.current_color
                circle.creation_method = getattr(preview, 'creation_method', 'center_radius')
                circle.creation_data = getattr(preview, 'creation_data', {'center': Point(preview.center.x, preview.center.y), 'radius': preview.radius})
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_circle = Circle(
                    preview.center,
                    preview.radius,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_circle.creation_method = getattr(preview, 'creation_method', 'center_radius')
                final_circle.creation_data = getattr(preview, 'creation_data', {'center': Point(preview.center.x, preview.center.y), 'radius': preview.radius})
                final_circle.layer = self.state.active_layer
                self.state.circles.append(final_circle)
            self.set_app_state('IDLE')

    def finalize_arc(self, event=None):
        if self.state.preview_arc:
            preview = self.state.preview_arc
            if self.state.editing_object and self.state.editing_object_type == 'arc':
                arc = self.state.editing_object
                arc.center = Point(preview.center.x, preview.center.y)
                arc.radius = preview.radius
                arc.start_angle = preview.start_angle
                arc.end_angle = preview.end_angle
                arc.style_name = self.state.current_style_name
                arc.color = self.state.current_color
                arc.creation_method = getattr(preview, 'creation_method', 'center_angles')
                arc.creation_data = getattr(preview, 'creation_data', {
                    'center': Point(preview.center.x, preview.center.y),
                    'radius': preview.radius,
                    'start_angle': preview.start_angle,
                    'end_angle': preview.end_angle
                })
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_arc = Arc(
                    preview.center,
                    preview.radius,
                    preview.start_angle,
                    preview.end_angle,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_arc.creation_method = getattr(preview, 'creation_method', 'center_angles')
                final_arc.creation_data = getattr(preview, 'creation_data', {
                    'center': Point(preview.center.x, preview.center.y),
                    'radius': preview.radius,
                    'start_angle': preview.start_angle,
                    'end_angle': preview.end_angle
                })
                final_arc.layer = self.state.active_layer
                self.state.arcs.append(final_arc)
            self.set_app_state('IDLE')

    def finalize_rectangle(self, event=None):
        if self.state.preview_rectangle:
            preview = self.state.preview_rectangle
            if self.state.editing_object and self.state.editing_object_type == 'rectangle':
                edit_rect = self.state.editing_object
                edit_rect.min_x = preview.min_x
                edit_rect.min_y = preview.min_y
                edit_rect.max_x = preview.max_x
                edit_rect.max_y = preview.max_y
                edit_rect.style_name = self.state.current_style_name
                edit_rect.color = self.state.current_color
                edit_rect.corner_type = preview.corner_type
                edit_rect.corner_value = preview.corner_value
                edit_rect.creation_method = getattr(preview, 'creation_method', 'two_points')
                edit_rect.creation_data = getattr(preview, 'creation_data', {
                    'p1': Point(preview.min_x, preview.min_y),
                    'p2': Point(preview.max_x, preview.max_y)
                })
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_rect = Rectangle(
                    preview.min_x, preview.min_y, preview.max_x, preview.max_y,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color,
                    corner_type=preview.corner_type,
                    corner_value=preview.corner_value
                )
                final_rect.creation_method = getattr(preview, 'creation_method', 'two_points')
                final_rect.creation_data = getattr(preview, 'creation_data', {
                    'p1': Point(preview.min_x, preview.min_y),
                    'p2': Point(preview.max_x, preview.max_y)
                })
                final_rect.layer = self.state.active_layer
                self.state.rectangles.append(final_rect)
            self.set_app_state('IDLE')

    def finalize_ellipse(self, event=None):
        if self.state.preview_ellipse:
            ell = self.state.preview_ellipse
            if self.state.editing_object and self.state.editing_object_type == 'ellipse':
                edit_ell = self.state.editing_object
                edit_ell.center = Point(ell.center.x, ell.center.y)
                edit_ell.axis_point_a = Point(ell.axis_point_a.x, ell.axis_point_a.y)
                edit_ell.axis_point_b = Point(ell.axis_point_b.x, ell.axis_point_b.y)
                edit_ell.style_name = self.state.current_style_name
                edit_ell.color = self.state.current_color
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_ellipse = Ellipse(
                    ell.center,
                    ell.axis_point_a,
                    ell.axis_point_b,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_ellipse.layer = self.state.active_layer
                self.state.ellipses.append(final_ellipse)
            self.set_app_state('IDLE')

    def finalize_polygon(self, event=None):
        if self.state.preview_polygon:
            poly = self.state.preview_polygon
            if self.state.editing_object and self.state.editing_object_type == 'polygon':
                edit_poly = self.state.editing_object
                edit_poly.center = Point(poly.center.x, poly.center.y)
                edit_poly.base_radius = poly.base_radius
                edit_poly.sides = poly.sides
                edit_poly.variant = poly.variant
                edit_poly.start_angle = poly.start_angle
                edit_poly.style_name = self.state.current_style_name
                edit_poly.color = self.state.current_color
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_poly = RegularPolygon(
                    poly.center,
                    poly.base_radius,
                    poly.sides,
                    variant=poly.variant,
                    start_angle=poly.start_angle,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_poly.layer = self.state.active_layer
                self.state.polygons.append(final_poly)
            self.set_app_state('IDLE')

    def finalize_spline(self, event=None):
        if len(self.state.spline_control_points) >= 2:
            ctrl_copy = [Point(p.x, p.y) for p in self.state.spline_control_points]
            if self.state.editing_object and self.state.editing_object_type == 'spline':
                edit_spline = self.state.editing_object
                edit_spline.control_points = ctrl_copy
                edit_spline.style_name = self.state.current_style_name
                edit_spline.color = self.state.current_color
                self.state.editing_object = None
                self.state.editing_object_type = None
            else:
                final_spline = Spline(
                    ctrl_copy,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
                final_spline.layer = self.state.active_layer
                self.state.splines.append(final_spline)
            self.set_app_state('IDLE')

    def on_escape_key(self, event=None):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_TANGENT_SEGMENT', 'CREATING_CIRCLE', 'CREATING_ARC', 'CREATING_RECTANGLE', 'CREATING_ELLIPSE', 'CREATING_POLYGON', 'CREATING_SPLINE', 'PANNING'] or self._is_dimension_mode():
            self.state.editing_object = None
            self.state.editing_object_type = None
            self._clear_dimension_creation_state()
            self._clear_tangent_creation_state()
            self.set_app_state('IDLE')
        elif self.state.selected_segments or self.state.selected_circles or self.state.selected_arcs or self.state.selected_rectangles or self.state.selected_ellipses or self.state.selected_polygons or self.state.selected_splines or self.state.selected_dimensions:
            self._clear_all_selection()
            self._sync_ui_with_selection()
            self.redraw_all()
        elif self.state.app_mode == 'IDLE' and messagebox.askyesno("Выход", "Выйти из программы?"):
            self.root.destroy()

    def on_double_click(self, event):

        wx, wy = self.converter.screen_to_world(event.x, event.y)
        hit_threshold_pixels = 8
        hit_threshold_world = hit_threshold_pixels / self.state.zoom

        for segment in self.state.segments:
            if not self.state.is_layer_visible(segment.layer): continue
            if segment.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_segment(segment)
                return
        for circle in self.state.circles:
            if not self.state.is_layer_visible(circle.layer): continue
            if circle.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_circle(circle)
                return
        for arc in self.state.arcs:
            if not self.state.is_layer_visible(arc.layer): continue
            if arc.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_arc(arc)
                return
        for rect in self.state.rectangles:
            if not self.state.is_layer_visible(rect.layer): continue
            if rect.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_rectangle(rect)
                return
        for ellipse in self.state.ellipses:
            if not self.state.is_layer_visible(ellipse.layer): continue
            if ellipse.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_ellipse(ellipse)
                return
        for poly in self.state.polygons:
            if not self.state.is_layer_visible(poly.layer): continue
            if poly.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_polygon(poly)
                return
        for spline in self.state.splines:
            if not self.state.is_layer_visible(spline.layer): continue
            if spline.distance_to_point(wx, wy) < hit_threshold_world:
                self.start_edit_spline(spline)
                return
        for dimension in self.state.dimensions:
            if not self.state.is_layer_visible(dimension.layer): continue
            if dimension.distance_to_point(wx, wy, self.state) < hit_threshold_world * 1.5:
                self.start_edit_dimension(dimension)
                return

    def on_edit_selected(self, event=None):

        if len(self.state.selected_segments) == 1:
            self.start_edit_segment(self.state.selected_segments[0])
        elif len(self.state.selected_circles) == 1:
            self.start_edit_circle(self.state.selected_circles[0])
        elif len(self.state.selected_arcs) == 1:
            self.start_edit_arc(self.state.selected_arcs[0])
        elif len(self.state.selected_rectangles) == 1:
            self.start_edit_rectangle(self.state.selected_rectangles[0])
        elif len(self.state.selected_ellipses) == 1:
            self.start_edit_ellipse(self.state.selected_ellipses[0])
        elif len(self.state.selected_polygons) == 1:
            self.start_edit_polygon(self.state.selected_polygons[0])
        elif len(self.state.selected_splines) == 1:
            self.start_edit_spline(self.state.selected_splines[0])
        elif len(self.state.selected_dimensions) == 1:
            self.start_edit_dimension(self.state.selected_dimensions[0])

    def start_edit_segment(self, segment):

        self.state.editing_object = segment
        self.state.editing_object_type = 'segment'
        
        self.state.current_style_name = segment.style_name
        self.state.current_color = segment.color

        self.set_app_state('CREATING_SEGMENT')
        
        self.view.p1_x_entry.delete(0, tk.END)
        self.view.p1_x_entry.insert(0, f"{segment.p1.x:.2f}")
        self.view.p1_y_entry.delete(0, tk.END)
        self.view.p1_y_entry.insert(0, f"{segment.p1.y:.2f}")
        self.view.p2_x_entry.delete(0, tk.END)
        self.view.p2_x_entry.insert(0, f"{segment.p2.x:.2f}")
        self.view.p2_y_entry.delete(0, tk.END)
        self.view.p2_y_entry.insert(0, f"{segment.p2.y:.2f}")
        
        self.state.points_clicked = 2
        self.update_preview_segment()

    def start_edit_circle(self, circle):

        self.state.editing_object = circle
        self.state.editing_object_type = 'circle'
        
        self.state.current_style_name = circle.style_name
        self.state.current_color = circle.color
        
        method = getattr(circle, 'creation_method', 'center_radius')
        data = getattr(circle, 'creation_data', None)
        
        self.state.circle_creation_method = method
        self.view.circle_method.set(method)
        self.view._update_circle_params_ui()

        self.set_app_state('CREATING_CIRCLE')
        
        if method == 'center_radius' and data:
            self.view.circle_center_x_entry.delete(0, tk.END)
            self.view.circle_center_x_entry.insert(0, f"{data['center'].x:.2f}")
            self.view.circle_center_y_entry.delete(0, tk.END)
            self.view.circle_center_y_entry.insert(0, f"{data['center'].y:.2f}")
            self.view.circle_param_entry.delete(0, tk.END)
            self.view.circle_param_entry.insert(0, f"{data['radius']:.2f}")
            self.state.points_clicked = 2
        elif method == 'center_diameter' and data:
            self.view.circle_center_x_entry.delete(0, tk.END)
            self.view.circle_center_x_entry.insert(0, f"{data['center'].x:.2f}")
            self.view.circle_center_y_entry.delete(0, tk.END)
            self.view.circle_center_y_entry.insert(0, f"{data['center'].y:.2f}")
            self.view.circle_param_entry.delete(0, tk.END)
            self.view.circle_param_entry.insert(0, f"{data['diameter']:.2f}")
            self.state.points_clicked = 2
        elif method == 'two_points' and data:
            self.view.circle_center_x_entry.delete(0, tk.END)
            self.view.circle_center_x_entry.insert(0, f"{data['p1'].x:.2f}")
            self.view.circle_center_y_entry.delete(0, tk.END)
            self.view.circle_center_y_entry.insert(0, f"{data['p1'].y:.2f}")
            self.view.circle_p2_x_entry.delete(0, tk.END)
            self.view.circle_p2_x_entry.insert(0, f"{data['p2'].x:.2f}")
            self.view.circle_p2_y_entry.delete(0, tk.END)
            self.view.circle_p2_y_entry.insert(0, f"{data['p2'].y:.2f}")
            self.state.points_clicked = 2
        elif method == 'three_points' and data:
            self.view.circle_center_x_entry.delete(0, tk.END)
            self.view.circle_center_x_entry.insert(0, f"{data['p1'].x:.2f}")
            self.view.circle_center_y_entry.delete(0, tk.END)
            self.view.circle_center_y_entry.insert(0, f"{data['p1'].y:.2f}")
            self.view.circle_p2_x_entry.delete(0, tk.END)
            self.view.circle_p2_x_entry.insert(0, f"{data['p2'].x:.2f}")
            self.view.circle_p2_y_entry.delete(0, tk.END)
            self.view.circle_p2_y_entry.insert(0, f"{data['p2'].y:.2f}")
            self.view.circle_p3_x_entry.delete(0, tk.END)
            self.view.circle_p3_x_entry.insert(0, f"{data['p3'].x:.2f}")
            self.view.circle_p3_y_entry.delete(0, tk.END)
            self.view.circle_p3_y_entry.insert(0, f"{data['p3'].y:.2f}")
            self.state.points_clicked = 3
        else:
            self.view.circle_center_x_entry.delete(0, tk.END)
            self.view.circle_center_x_entry.insert(0, f"{circle.center.x:.2f}")
            self.view.circle_center_y_entry.delete(0, tk.END)
            self.view.circle_center_y_entry.insert(0, f"{circle.center.y:.2f}")
            self.view.circle_param_entry.delete(0, tk.END)
            self.view.circle_param_entry.insert(0, f"{circle.radius:.2f}")
            self.state.points_clicked = 2
        
        self.update_preview_circle()

    def start_edit_arc(self, arc):

        self.state.editing_object = arc
        self.state.editing_object_type = 'arc'
        
        self.state.current_style_name = arc.style_name
        self.state.current_color = arc.color
        
        method = getattr(arc, 'creation_method', 'center_angles')
        data = getattr(arc, 'creation_data', None)
        
        self.state.arc_creation_method = method
        self.view.arc_method.set(method)
        self.view._update_arc_params_ui()

        self.set_app_state('CREATING_ARC')
        
        angle_unit = self.view.angle_units.get()
        
        if method == 'three_points' and data:
            self.view.arc_p1_x_entry.delete(0, tk.END)
            self.view.arc_p1_x_entry.insert(0, f"{data['p1'].x:.2f}")
            self.view.arc_p1_y_entry.delete(0, tk.END)
            self.view.arc_p1_y_entry.insert(0, f"{data['p1'].y:.2f}")
            self.view.arc_p2_x_entry.delete(0, tk.END)
            self.view.arc_p2_x_entry.insert(0, f"{data['p2'].x:.2f}")
            self.view.arc_p2_y_entry.delete(0, tk.END)
            self.view.arc_p2_y_entry.insert(0, f"{data['p2'].y:.2f}")
            self.view.arc_p3_x_entry.delete(0, tk.END)
            self.view.arc_p3_x_entry.insert(0, f"{data['p3'].x:.2f}")
            self.view.arc_p3_y_entry.delete(0, tk.END)
            self.view.arc_p3_y_entry.insert(0, f"{data['p3'].y:.2f}")
            self.state.points_clicked = 3
        elif method == 'center_angles' and data:
            start_angle = data['start_angle']
            end_angle = data['end_angle']
            if angle_unit == 'degrees':
                start_angle = math.degrees(start_angle)
                end_angle = math.degrees(end_angle)
            
            self.view.arc_center_x_entry.delete(0, tk.END)
            self.view.arc_center_x_entry.insert(0, f"{data['center'].x:.2f}")
            self.view.arc_center_y_entry.delete(0, tk.END)
            self.view.arc_center_y_entry.insert(0, f"{data['center'].y:.2f}")
            self.view.arc_radius_entry.delete(0, tk.END)
            self.view.arc_radius_entry.insert(0, f"{data['radius']:.2f}")
            self.view.arc_start_angle_entry.delete(0, tk.END)
            self.view.arc_start_angle_entry.insert(0, f"{start_angle:.2f}")
            self.view.arc_end_angle_entry.delete(0, tk.END)
            self.view.arc_end_angle_entry.insert(0, f"{end_angle:.2f}")
            self.state.points_clicked = 3
        else:
            start_angle = arc.start_angle
            end_angle = arc.end_angle
            if angle_unit == 'degrees':
                start_angle = math.degrees(start_angle)
                end_angle = math.degrees(end_angle)
            
            self.view.arc_center_x_entry.delete(0, tk.END)
            self.view.arc_center_x_entry.insert(0, f"{arc.center.x:.2f}")
            self.view.arc_center_y_entry.delete(0, tk.END)
            self.view.arc_center_y_entry.insert(0, f"{arc.center.y:.2f}")
            self.view.arc_radius_entry.delete(0, tk.END)
            self.view.arc_radius_entry.insert(0, f"{arc.radius:.2f}")
            self.view.arc_start_angle_entry.delete(0, tk.END)
            self.view.arc_start_angle_entry.insert(0, f"{start_angle:.2f}")
            self.view.arc_end_angle_entry.delete(0, tk.END)
            self.view.arc_end_angle_entry.insert(0, f"{end_angle:.2f}")
            self.state.points_clicked = 3
        
        self.update_preview_arc()

    def start_edit_rectangle(self, rect):

        self.state.editing_object = rect
        self.state.editing_object_type = 'rectangle'
        
        self.state.current_style_name = rect.style_name
        self.state.current_color = rect.color
        
        method = getattr(rect, 'creation_method', 'two_points')
        data = getattr(rect, 'creation_data', None)
        
        self.state.rectangle_creation_method = method
        self.view.rect_method.set(method)
        self.view._update_rectangle_params_ui()

        self.set_app_state('CREATING_RECTANGLE')
        
        if method == 'two_points' and data:
            self.view.rect_p1_x_entry.delete(0, tk.END)
            self.view.rect_p1_x_entry.insert(0, f"{data['p1'].x:.2f}")
            self.view.rect_p1_y_entry.delete(0, tk.END)
            self.view.rect_p1_y_entry.insert(0, f"{data['p1'].y:.2f}")
            self.view.rect_p2_x_entry.delete(0, tk.END)
            self.view.rect_p2_x_entry.insert(0, f"{data['p2'].x:.2f}")
            self.view.rect_p2_y_entry.delete(0, tk.END)
            self.view.rect_p2_y_entry.insert(0, f"{data['p2'].y:.2f}")
            self.state.points_clicked = 2
        elif method == 'corner_size' and data:
            self.view.rect_corner_x_entry.delete(0, tk.END)
            self.view.rect_corner_x_entry.insert(0, f"{data['corner'].x:.2f}")
            self.view.rect_corner_y_entry.delete(0, tk.END)
            self.view.rect_corner_y_entry.insert(0, f"{data['corner'].y:.2f}")
            self.view.rect_width_entry.delete(0, tk.END)
            self.view.rect_width_entry.insert(0, f"{data['width']:.2f}")
            self.view.rect_height_entry.delete(0, tk.END)
            self.view.rect_height_entry.insert(0, f"{data['height']:.2f}")
            self.state.points_clicked = 2
        elif method == 'center_size' and data:
            self.view.rect_center_x_entry.delete(0, tk.END)
            self.view.rect_center_x_entry.insert(0, f"{data['center'].x:.2f}")
            self.view.rect_center_y_entry.delete(0, tk.END)
            self.view.rect_center_y_entry.insert(0, f"{data['center'].y:.2f}")
            self.view.rect_center_w_entry.delete(0, tk.END)
            self.view.rect_center_w_entry.insert(0, f"{data['width']:.2f}")
            self.view.rect_center_h_entry.delete(0, tk.END)
            self.view.rect_center_h_entry.insert(0, f"{data['height']:.2f}")
            self.state.points_clicked = 2
        else:
            self.view.rect_p1_x_entry.delete(0, tk.END)
            self.view.rect_p1_x_entry.insert(0, f"{rect.min_x:.2f}")
            self.view.rect_p1_y_entry.delete(0, tk.END)
            self.view.rect_p1_y_entry.insert(0, f"{rect.min_y:.2f}")
            self.view.rect_p2_x_entry.delete(0, tk.END)
            self.view.rect_p2_x_entry.insert(0, f"{rect.max_x:.2f}")
            self.view.rect_p2_y_entry.delete(0, tk.END)
            self.view.rect_p2_y_entry.insert(0, f"{rect.max_y:.2f}")
            self.state.points_clicked = 2
        
        self.view.rect_corner_type.set(rect.corner_type)
        self.view.rect_corner_value_entry.delete(0, tk.END)
        if rect.corner_value > 0:
            self.view.rect_corner_value_entry.insert(0, f"{rect.corner_value:.2f}")
        
        self.update_preview_rectangle()

    def start_edit_ellipse(self, ellipse):

        self.state.editing_object = ellipse
        self.state.editing_object_type = 'ellipse'
        
        self.state.current_style_name = ellipse.style_name
        self.state.current_color = ellipse.color

        self.set_app_state('CREATING_ELLIPSE')
        
        self.view.ellipse_center_x_entry.delete(0, tk.END)
        self.view.ellipse_center_x_entry.insert(0, f"{ellipse.center.x:.2f}")
        self.view.ellipse_center_y_entry.delete(0, tk.END)
        self.view.ellipse_center_y_entry.insert(0, f"{ellipse.center.y:.2f}")
        self.view.ellipse_a_x_entry.delete(0, tk.END)
        self.view.ellipse_a_x_entry.insert(0, f"{ellipse.axis_point_a.x:.2f}")
        self.view.ellipse_a_y_entry.delete(0, tk.END)
        self.view.ellipse_a_y_entry.insert(0, f"{ellipse.axis_point_a.y:.2f}")
        self.view.ellipse_b_x_entry.delete(0, tk.END)
        self.view.ellipse_b_x_entry.insert(0, f"{ellipse.axis_point_b.x:.2f}")
        self.view.ellipse_b_y_entry.delete(0, tk.END)
        self.view.ellipse_b_y_entry.insert(0, f"{ellipse.axis_point_b.y:.2f}")
        
        self.state.points_clicked = 3
        self.update_preview_ellipse()

    def start_edit_polygon(self, poly):

        self.state.editing_object = poly
        self.state.editing_object_type = 'polygon'
        
        self.state.current_style_name = poly.style_name
        self.state.current_color = poly.color

        self.set_app_state('CREATING_POLYGON')
        
        self.view.polygon_center_x_entry.delete(0, tk.END)
        self.view.polygon_center_x_entry.insert(0, f"{poly.center.x:.2f}")
        self.view.polygon_center_y_entry.delete(0, tk.END)
        self.view.polygon_center_y_entry.insert(0, f"{poly.center.y:.2f}")
        self.view.polygon_radius_entry.delete(0, tk.END)
        self.view.polygon_radius_entry.insert(0, f"{poly.base_radius:.2f}")
        self.view.polygon_sides_var.set(str(poly.sides))
        self.view.polygon_variant.set(poly.variant)
        
        self.state.polygon_sides = poly.sides
        self.state.polygon_variant = poly.variant
        self.state.polygon_start_angle = getattr(poly, 'start_angle', 0.0)
        
        self.state.points_clicked = 2
        self.update_preview_polygon()

    def start_edit_spline(self, spline):

        self.state.editing_object = spline
        self.state.editing_object_type = 'spline'
        
        self.state.current_style_name = spline.style_name
        self.state.current_color = spline.color

        self.set_app_state('CREATING_SPLINE')
        
        self.state.spline_control_points = [Point(p.x, p.y) for p in spline.control_points]
        self._update_spline_points_listbox()
        
        self.update_preview_spline()

    def start_edit_dimension(self, dimension):
        self.state.editing_object = dimension
        self.state.editing_object_type = 'dimension'
        self.state.current_color = dimension.color
        self.state.current_dimension_style_name = dimension.dimension_style_name
        self.view.set_dimension_style_selection(dimension.dimension_style_name)
        self._sync_dimension_text_override_controls(dimension)

        if isinstance(dimension, LinearDimension):
            self.state.dimension_creation_refs = [
                self._clone_dimension_ref(dimension.p1_ref),
                self._clone_dimension_ref(dimension.p2_ref),
                self._clone_dimension_ref(dimension.line_ref),
            ]
            self.set_app_state(f"CREATING_DIMENSION_{dimension.mode.upper()}")
        elif isinstance(dimension, AngularDimension):
            self.state.dimension_creation_refs = [
                self._clone_dimension_ref(dimension.p1_ref),
                self._clone_dimension_ref(dimension.vertex_ref),
                self._clone_dimension_ref(dimension.p2_ref),
                self._clone_dimension_ref(dimension.arc_ref),
            ]
            self.set_app_state("CREATING_DIMENSION_ANGULAR")
        else:
            prefix = getattr(dimension, 'prefix', 'R')
            self.state.dimension_creation_object = None
            if dimension.center_ref.source_object is not None:
                self.state.dimension_creation_object = dimension.center_ref.source_object
            self.state.dimension_creation_refs = [self._clone_dimension_ref(dimension.leader_ref)]
            self.set_app_state("CREATING_DIMENSION_RADIUS" if prefix == "R" else "CREATING_DIMENSION_DIAMETER")
        self.state.preview_dimension = dimension
        self.update_preview_dimension()
        self._sync_ui_with_selection()

    def on_delete_segment(self, event=None):

        has_selection = (
            self.state.selected_segments or
            self.state.selected_circles or
            self.state.selected_arcs or
            self.state.selected_rectangles or
            self.state.selected_ellipses or
            self.state.selected_polygons or
            self.state.selected_splines or
            self.state.selected_dimensions
        )
        
        if has_selection:
            removed_objects = []
            for seg in self.state.selected_segments:
                if seg in self.state.segments:
                    self.state.segments.remove(seg)
                    removed_objects.append(seg)
            self.state.selected_segments = []
            
            for circle in self.state.selected_circles:
                if circle in self.state.circles:
                    self.state.circles.remove(circle)
                    removed_objects.append(circle)
            self.state.selected_circles = []
            
            for arc in self.state.selected_arcs:
                if arc in self.state.arcs:
                    self.state.arcs.remove(arc)
                    removed_objects.append(arc)
            self.state.selected_arcs = []
            
            for rect in self.state.selected_rectangles:
                if rect in self.state.rectangles:
                    self.state.rectangles.remove(rect)
                    removed_objects.append(rect)
            self.state.selected_rectangles = []
            
            for ellipse in self.state.selected_ellipses:
                if ellipse in self.state.ellipses:
                    self.state.ellipses.remove(ellipse)
                    removed_objects.append(ellipse)
            self.state.selected_ellipses = []
            
            for poly in self.state.selected_polygons:
                if poly in self.state.polygons:
                    self.state.polygons.remove(poly)
                    removed_objects.append(poly)
            self.state.selected_polygons = []
            
            for spline in self.state.selected_splines:
                if spline in self.state.splines:
                    self.state.splines.remove(spline)
                    removed_objects.append(spline)
            self.state.selected_splines = []

            for dimension in self.state.selected_dimensions:
                if dimension in self.state.dimensions:
                    self.state.dimensions.remove(dimension)
            self.state.selected_dimensions = []

            if removed_objects:
                self.state.dimensions = [
                    dim for dim in self.state.dimensions
                    if not any(dim.depends_on(obj) for obj in removed_objects)
                ]
        else:
            removed_object = None
            if self.state.segments:
                removed_object = self.state.segments.pop()
            elif self.state.circles:
                removed_object = self.state.circles.pop()
            elif self.state.arcs:
                removed_object = self.state.arcs.pop()
            elif self.state.rectangles:
                removed_object = self.state.rectangles.pop()
            elif self.state.ellipses:
                removed_object = self.state.ellipses.pop()
            elif self.state.polygons:
                removed_object = self.state.polygons.pop()
            elif self.state.splines:
                removed_object = self.state.splines.pop()
            elif self.state.dimensions:
                self.state.dimensions.pop()

            if removed_object is not None:
                self.state.dimensions = [
                    dim for dim in self.state.dimensions
                    if not dim.depends_on(removed_object)
                ]

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

    def on_apply_dimension_text_override(self, event=None):
        dimension = self._dimension_context_target()
        if dimension is None:
            return
        dimension.text_override = self.view.dimension_text_override_entry.get().strip()
        dimension.text_prefix_override = self._selected_dimension_text_prefix()
        dimension.text_suffix_override = self._selected_dimension_text_suffix()
        self._sync_preview_dimension_from_editing_object()
        self._sync_ui_with_selection()
        self.redraw_all()

    def on_reset_dimension_text_override(self, event=None):
        dimension = self._dimension_context_target()
        if dimension is None:
            return
        dimension.text_override = ""
        dimension.text_prefix_override = None
        dimension.text_suffix_override = None
        self._sync_dimension_text_override_controls(dimension)
        self._sync_preview_dimension_from_editing_object()
        self._sync_ui_with_selection()
        self.redraw_all()

    def on_choose_dimension_extension_color(self):
        dimension = self._dimension_context_target()
        if dimension is None or dimension.dimension_type in ("radius", "diameter"):
            return
        _, c = colorchooser.askcolor(initialcolor=dimension._effective_extension_line_color(self.state))
        if c:
            dimension.extension_line_color = c
            self._sync_preview_dimension_from_editing_object()
            self._set_dimension_swatch(self.view.dimension_ext_color_swatch, c)
            self.redraw_all()

    def on_choose_dimension_dim_color(self):
        dimension = self._dimension_context_target()
        if dimension is None:
            return
        _, c = colorchooser.askcolor(initialcolor=dimension._effective_dim_line_color(self.state))
        if c:
            dimension.dim_line_color = c
            self._sync_preview_dimension_from_editing_object()
            self._set_dimension_swatch(self.view.dimension_dim_color_swatch, c)
            self.redraw_all()

    def on_apply_dimension_appearance(self):
        dimension = self._dimension_context_target()
        if dimension is None:
            return

        try:
            if dimension.dimension_type not in ("radius", "diameter"):
                dimension.extension_overrun_mm = float(self.view.dimension_ext_overrun_entry.get() or 0.0)
                dimension.extension_line_style_name = self._selected_combobox_id(
                    self.view.dimension_ext_style_combobox,
                    self.view.dimension_line_style_ids,
                )
            dimension.dim_line_extension_mm = float(self.view.dimension_dim_extension_entry.get() or 0.0)
            dimension.dim_line_style_name = self._selected_combobox_id(
                self.view.dimension_dim_style_combobox,
                self.view.dimension_line_style_ids,
            )
            dimension.arrow_type = self._selected_combobox_id(
                self.view.dimension_arrow_type_combobox,
                self.view.dimension_arrow_type_ids,
            )
            dimension.arrow_size_mm = float(self.view.dimension_arrow_size_entry.get() or 0.0)
            dimension.arrow_filled = bool(self.view.dimension_arrow_filled_var.get())
            dimension.text_font_family = self.view.dimension_text_font_combobox.get().strip() or "ГОСТ тип А наклонный"
            height_text = self._selected_combobox_id(
                self.view.dimension_text_height_combobox,
                self.view.dimension_text_height_ids,
            ).replace(",", ".")
            dimension.text_height_mm = float(height_text or 0.0)
            dimension.text_gap_mm = max(0.0, float((self.view.dimension_text_gap_entry.get() or "0").replace(",", ".")))
            dimension.text_position_mode = self._selected_combobox_id(
                self.view.dimension_text_position_combobox,
                self.view.dimension_text_position_ids,
            )
        except ValueError:
            messagebox.showerror("Параметры размера", "Числовые поля должны содержать корректные числа.")
            return

        dimension.custom_style_snapshot = dimension._capture_appearance_state()
        dimension.dimension_style_name = "user_custom"
        self.state.current_dimension_style_name = "user_custom"
        self._sync_preview_dimension_from_editing_object()
        self.redraw_all()
        self._sync_ui_with_selection()

    def on_reset_dimension_appearance(self):
        dimension = self._dimension_context_target()
        if dimension is None:
            return

        for attr in [
            "extension_line_color",
            "extension_line_style_name",
            "extension_overrun_mm",
            "dim_line_color",
            "dim_line_style_name",
            "dim_line_extension_mm",
            "arrow_type",
            "arrow_size_mm",
            "arrow_filled",
            "text_font_family",
            "text_height_mm",
            "text_gap_mm",
            "text_position_mode",
        ]:
            setattr(dimension, attr, None)

        dimension.custom_style_snapshot = {}
        dimension.dimension_style_name = "gost_default"
        self.state.current_dimension_style_name = "gost_default"
        self._sync_preview_dimension_from_editing_object()
        self.redraw_all()
        self._sync_ui_with_selection()

    def _find_radial_dimension_target_under_cursor(self, wx, wy):
        hit_threshold_world = 8 / self.state.zoom
        for circle in self.state.circles:
            if not self.state.is_layer_visible(circle.layer):
                continue
            if circle.distance_to_point(wx, wy) < hit_threshold_world * 1.5:
                return circle
        for arc in self.state.arcs:
            if not self.state.is_layer_visible(arc.layer):
                continue
            if arc.distance_to_point(wx, wy) < hit_threshold_world * 1.5:
                return arc
        for rect in self.state.rectangles:
            if not self.state.is_layer_visible(rect.layer):
                continue
            for fillet_arc in rect.fillet_arcs():
                if fillet_arc.distance_to_point(wx, wy) < hit_threshold_world * 1.5:
                    return rect
        return None

    def _find_circle_under_cursor(self, wx, wy):
        hit_threshold_world = 8 / self.state.zoom
        for circle in self.state.circles:
            if not self.state.is_layer_visible(circle.layer):
                continue
            if circle.distance_to_point(wx, wy) < hit_threshold_world * 1.5:
                return circle
        return None

    def _circle_tangent_segments(self, circle1, circle2):
        x1, y1 = circle1.center.x, circle1.center.y
        x2, y2 = circle2.center.x, circle2.center.y
        dx = x2 - x1
        dy = y2 - y1
        dist_sq = dx * dx + dy * dy
        if dist_sq < 1e-12:
            return []

        result = []
        for radius_sign in (1.0, -1.0):
            radius_delta = circle1.radius - radius_sign * circle2.radius
            h_sq = dist_sq - radius_delta * radius_delta
            if h_sq < -1e-9:
                continue
            h = math.sqrt(max(0.0, h_sq))
            for side in (1.0, -1.0):
                vx = (dx * radius_delta - dy * h * side) / dist_sq
                vy = (dy * radius_delta + dx * h * side) / dist_sq
                p1 = Point(x1 + vx * circle1.radius, y1 + vy * circle1.radius)
                p2 = Point(x2 + vx * radius_sign * circle2.radius, y2 + vy * radius_sign * circle2.radius)
                candidate = Segment(
                    p1,
                    p2,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color,
                )
                is_duplicate = any(
                    candidate.p1.distance_to_point(seg.p1.x, seg.p1.y) < 1e-7
                    and candidate.p2.distance_to_point(seg.p2.x, seg.p2.y) < 1e-7
                    for seg in result
                )
                if not is_duplicate:
                    result.append(candidate)
        return result

    def _update_tangent_segment_preview(self, wx, wy):
        circles = self.state.tangent_creation_circles
        if len(circles) < 2:
            self.state.preview_segment = None
            return
        candidates = self._circle_tangent_segments(circles[0], circles[1])
        if not candidates:
            self.state.preview_segment = None
            return
        self.state.preview_segment = min(candidates, key=lambda seg: seg.distance_to_point(wx, wy))

    def on_lmb_click(self, event):
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        if self.state.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.state.active_p1 = Point(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            self._update_p2_entries(Point(wx, wy))
            self.state.points_clicked = 2
        self.update_preview_segment()

    def on_lmb_click_tangent_segment(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        circles = self.state.tangent_creation_circles

        if len(circles) < 2:
            circle = self._find_circle_under_cursor(wx, wy)
            if circle is None:
                messagebox.showinfo("Касательная", "Кликни по окружности.")
                return
            if circles and circle is circles[0]:
                messagebox.showinfo("Касательная", "Выбери вторую окружность.")
                return
            circles.append(circle)
            self.state.points_clicked = len(circles)
            if len(circles) == 2:
                self._update_tangent_segment_preview(wx, wy)
                if self.state.preview_segment is None:
                    messagebox.showerror("Касательная", "Для этих окружностей общая касательная не найдена.")
                    self._clear_tangent_creation_state()
            self.redraw_all()
            return

        self._update_tangent_segment_preview(wx, wy)
        self.finalize_segment()

    def on_lmb_click_circle(self, event):
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        method = self.state.circle_creation_method

        if method in ['center_radius', 'center_diameter']:
            if self.state.points_clicked == 0:
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                distance = math.sqrt((wx - center_x)**2 + (wy - center_y)**2)
                if method == 'center_radius':
                    value = distance
                else:
                    value = distance * 2
                self.view.circle_param_entry.delete(0, tk.END)
                self.view.circle_param_entry.insert(0, f"{value:.2f}")
                self.state.points_clicked = 2
        elif method == 'two_points':
            if self.state.points_clicked == 0:
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
        elif method == 'three_points':
            if self.state.points_clicked == 0:
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
            elif self.state.points_clicked == 2:
                self.view.circle_p3_x_entry.delete(0, tk.END)
                self.view.circle_p3_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p3_y_entry.delete(0, tk.END)
                self.view.circle_p3_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 3

        self.update_preview_circle()

    def on_lmb_click_arc(self, event):
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        method = self.state.arc_creation_method
        angle_unit = self.view.angle_units.get()

        def _to_display_angle(rad_val):
            return math.degrees(rad_val) if angle_unit == 'degrees' else rad_val

        if method == 'three_points':
            if self.state.points_clicked == 0:
                self.view.arc_p1_x_entry.delete(0, tk.END); self.view.arc_p1_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_p1_y_entry.delete(0, tk.END); self.view.arc_p1_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
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
                self.view.arc_center_x_entry.delete(0, tk.END); self.view.arc_center_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_center_y_entry.delete(0, tk.END); self.view.arc_center_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                cx = float(self.view.arc_center_x_entry.get())
                cy = float(self.view.arc_center_y_entry.get())
                radius = math.sqrt((wx - cx)**2 + (wy - cy)**2)
                ang = math.atan2(wy - cy, wx - cx)

                self.view.arc_radius_entry.delete(0, tk.END); self.view.arc_radius_entry.insert(0, f"{radius:.2f}")
                self.view.arc_start_angle_entry.delete(0, tk.END); self.view.arc_start_angle_entry.insert(0, f"{_to_display_angle(ang):.2f}")
                self.state.active_p2 = Point(wx, wy)
                self.state.points_clicked = 2
            elif self.state.points_clicked == 2:
                cx = float(self.view.arc_center_x_entry.get())
                cy = float(self.view.arc_center_y_entry.get())
                ang = math.atan2(wy - cy, wx - cx)
                self.view.arc_end_angle_entry.delete(0, tk.END); self.view.arc_end_angle_entry.insert(0, f"{_to_display_angle(ang):.2f}")

                if not self.view.arc_radius_entry.get():
                    radius = math.sqrt((wx - cx)**2 + (wy - cy)**2)
                    self.view.arc_radius_entry.insert(0, f"{radius:.2f}")
                self.state.points_clicked = 3

        self.update_preview_arc()

    def on_lmb_click_rectangle(self, event):
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        method = self.state.rectangle_creation_method

        if method == 'two_points':
            if self.state.points_clicked == 0:
                self.view.rect_p1_x_entry.delete(0, tk.END); self.view.rect_p1_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_p1_y_entry.delete(0, tk.END); self.view.rect_p1_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
                self.state.points_clicked = 1
            elif self.state.points_clicked == 1:
                self.view.rect_p2_x_entry.delete(0, tk.END); self.view.rect_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_p2_y_entry.delete(0, tk.END); self.view.rect_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.points_clicked = 2
        elif method == 'corner_size':
            if self.state.points_clicked == 0:
                self.view.rect_corner_x_entry.delete(0, tk.END); self.view.rect_corner_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_corner_y_entry.delete(0, tk.END); self.view.rect_corner_y_entry.insert(0, f"{wy:.2f}")
                self.state.active_p1 = Point(wx, wy)
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
                self.state.active_p1 = Point(wx, wy)
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
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        if self.state.points_clicked == 0:
            self.view.ellipse_center_x_entry.delete(0, tk.END); self.view.ellipse_center_x_entry.insert(0, f"{wx:.2f}")
            self.view.ellipse_center_y_entry.delete(0, tk.END); self.view.ellipse_center_y_entry.insert(0, f"{wy:.2f}")
            self.state.active_p1 = Point(wx, wy)
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
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        if self.state.points_clicked == 0:
            self.view.polygon_center_x_entry.delete(0, tk.END); self.view.polygon_center_x_entry.insert(0, f"{wx:.2f}")
            self.view.polygon_center_y_entry.delete(0, tk.END); self.view.polygon_center_y_entry.insert(0, f"{wy:.2f}")
            self.state.active_p1 = Point(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            try:
                cx = float(self.view.polygon_center_x_entry.get())
                cy = float(self.view.polygon_center_y_entry.get())
            except ValueError:
                cx, cy = wx, wy
            radius = math.sqrt((wx - cx) ** 2 + (wy - cy) ** 2)
            self.view.polygon_radius_entry.delete(0, tk.END); self.view.polygon_radius_entry.insert(0, f"{radius:.2f}")
            self.state.polygon_start_angle = math.atan2(wy - cy, wx - cx)
            self.state.points_clicked = 2
        self.update_preview_polygon()

    def on_lmb_click_dimension(self, event):
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        kind = self._get_dimension_mode_kind()

        if kind in ("horizontal", "vertical", "aligned"):
            if len(self.state.dimension_creation_refs) < 2:
                ref = self._make_dimension_reference(wx, wy)
                self.state.dimension_creation_refs.append(ref)
                if len(self.state.dimension_creation_refs) == 1:
                    self.state.active_p1 = ref.resolve()
                elif len(self.state.dimension_creation_refs) == 2:
                    self.state.active_p2 = ref.resolve()
            else:
                ref = GeometryReference.static(Point(wx, wy))
                if len(self.state.dimension_creation_refs) == 2:
                    self.state.dimension_creation_refs.append(ref)
                else:
                    self.state.dimension_creation_refs[2] = ref
                self.state.active_p3 = ref.resolve()
                self.state.points_clicked = 3
                self.update_preview_dimension()
                self.finalize_dimension()
                return

        elif kind in ("radius", "diameter"):
            if self.state.dimension_creation_object is None:
                obj = self._find_radial_dimension_target_under_cursor(wx, wy)
                if obj is None:
                    return
                self.state.dimension_creation_object = obj
                self.state.active_p1 = Point(wx, wy)
            else:
                ref = GeometryReference.static(Point(wx, wy))
                if self.state.dimension_creation_refs:
                    self.state.dimension_creation_refs[0] = ref
                else:
                    self.state.dimension_creation_refs.append(ref)
                self.state.active_p2 = ref.resolve()
                self.state.points_clicked = 2
                self.update_preview_dimension()
                self.finalize_dimension()
                return

        elif kind == "angular":
            if len(self.state.dimension_creation_refs) < 3:
                ref = self._make_dimension_reference(wx, wy)
                self.state.dimension_creation_refs.append(ref)
                if len(self.state.dimension_creation_refs) == 1:
                    self.state.active_p1 = ref.resolve()
                elif len(self.state.dimension_creation_refs) == 2:
                    self.state.active_p2 = ref.resolve()
                elif len(self.state.dimension_creation_refs) == 3:
                    self.state.active_p3 = ref.resolve()
            else:
                ref = GeometryReference.static(Point(wx, wy))
                if len(self.state.dimension_creation_refs) == 3:
                    self.state.dimension_creation_refs.append(ref)
                else:
                    self.state.dimension_creation_refs[3] = ref
                self.state.active_p4 = ref.resolve()
                self.state.points_clicked = 4
                self.update_preview_dimension()
                self.finalize_dimension()
                return

        self.state.points_clicked = len(self.state.dimension_creation_refs)
        self.update_preview_dimension()

    def _update_spline_points_listbox(self):
        lb = self.view.spline_points_listbox
        current_selection = lb.curselection()
        lb.delete(0, tk.END)
        for idx, p in enumerate(self.state.spline_control_points, start=1):
            lb.insert(tk.END, f"{idx}: ({p.x:.2f}, {p.y:.2f})")
        if current_selection and current_selection[0] < len(self.state.spline_control_points):
            lb.selection_set(current_selection[0])

    def on_spline_point_selected(self, event=None):

        selection = self.view.spline_points_listbox.curselection()
        if selection and self.state.spline_control_points:
            idx = selection[0]
            if 0 <= idx < len(self.state.spline_control_points):
                pt = self.state.spline_control_points[idx]
                self.view.spline_point_x_entry.delete(0, tk.END)
                self.view.spline_point_x_entry.insert(0, f"{pt.x:.2f}")
                self.view.spline_point_y_entry.delete(0, tk.END)
                self.view.spline_point_y_entry.insert(0, f"{pt.y:.2f}")
                self.state.selected_spline_point_index = idx
                self.redraw_all()
                return
        self.state.selected_spline_point_index = None
        self.redraw_all()

    def on_update_selected_spline_point(self, event=None):

        selection = self.view.spline_points_listbox.curselection()
        if not selection or not self.state.spline_control_points:
            return
        
        idx = selection[0]
        if not (0 <= idx < len(self.state.spline_control_points)):
            return
        
        try:
            x = float(self.view.spline_point_x_entry.get())
            y = float(self.view.spline_point_y_entry.get())
        except (ValueError, tk.TclError):
            return
        
        self.state.spline_control_points[idx] = Point(x, y)
        self._update_spline_points_listbox()
        
        self.view.spline_points_listbox.selection_clear(0, tk.END)
        self.view.spline_points_listbox.selection_set(idx)
        self.view.spline_points_listbox.see(idx)
        
        self.update_preview_spline()

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
        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        self.state.spline_control_points.append(Point(wx, wy))
        self.view.spline_point_x_entry.delete(0, tk.END); self.view.spline_point_x_entry.insert(0, f"{wx:.2f}")
        self.view.spline_point_y_entry.delete(0, tk.END); self.view.spline_point_y_entry.insert(0, f"{wy:.2f}")
        self._update_spline_points_listbox()
        self.update_preview_spline()

    def _on_spline_mouse_down(self, event):
        """ЛКМ нажата: проверить попадание в существующую контрольную точку или добавить новую."""
        if not self.state.spline_control_points:
            self.on_lmb_click_spline(event)
            return

        hit_radius_px = 14
        for i, pt in enumerate(self.state.spline_control_points):
            sx, sy = self.converter.world_to_screen(pt.x, pt.y)
            if abs(event.x - sx) <= hit_radius_px and abs(event.y - sy) <= hit_radius_px:
                self.state.dragging_spline_point_index = i
                self.state.selected_spline_point_index = i
                # Синхронизация listbox и полей ввода
                self.view.spline_points_listbox.selection_clear(0, tk.END)
                self.view.spline_points_listbox.selection_set(i)
                self.view.spline_points_listbox.see(i)
                self.view.spline_point_x_entry.delete(0, tk.END)
                self.view.spline_point_x_entry.insert(0, f"{pt.x:.2f}")
                self.view.spline_point_y_entry.delete(0, tk.END)
                self.view.spline_point_y_entry.insert(0, f"{pt.y:.2f}")
                self.redraw_all()
                return

        # Не попали ни в одну точку — добавляем новую
        self.on_lmb_click_spline(event)

    def _on_spline_mouse_drag(self, event):
        """Перетаскивание контрольной точки сплайна."""
        idx = self.state.dragging_spline_point_index
        if idx is None or idx >= len(self.state.spline_control_points):
            return

        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        self.state.spline_control_points[idx] = Point(wx, wy)
        self.state.selected_spline_point_index = idx

        # Обновить поля ввода
        self.view.spline_point_x_entry.delete(0, tk.END)
        self.view.spline_point_x_entry.insert(0, f"{wx:.2f}")
        self.view.spline_point_y_entry.delete(0, tk.END)
        self.view.spline_point_y_entry.insert(0, f"{wy:.2f}")

        # Обновить listbox
        self._update_spline_points_listbox()
        self.view.spline_points_listbox.selection_clear(0, tk.END)
        self.view.spline_points_listbox.selection_set(idx)

        self.update_preview_spline()

    def _on_spline_mouse_up(self, event):
        """Отпускание ЛКМ — завершение перетаскивания."""
        self.state.dragging_spline_point_index = None

    def on_insert_spline_point_before(self, event=None):

        try:
            x = float(self.view.spline_point_x_entry.get())
            y = float(self.view.spline_point_y_entry.get())
        except (ValueError, tk.TclError):
            return
        
        selection = self.view.spline_points_listbox.curselection()
        if selection:
            insert_idx = selection[0]
        else:
            insert_idx = 0
        
        self.state.spline_control_points.insert(insert_idx, Point(x, y))
        self._update_spline_points_listbox()
        
        self.view.spline_points_listbox.selection_clear(0, tk.END)
        self.view.spline_points_listbox.selection_set(insert_idx)
        self.view.spline_points_listbox.see(insert_idx)
        
        self.update_preview_spline()

    def on_remove_selected_spline_point(self, event=None):

        if not self.state.spline_control_points:
            return
        
        selection = self.view.spline_points_listbox.curselection()
        if selection:
            remove_idx = selection[0]
        else:
            remove_idx = len(self.state.spline_control_points) - 1
        
        if 0 <= remove_idx < len(self.state.spline_control_points):
            self.state.spline_control_points.pop(remove_idx)
            self._update_spline_points_listbox()
            
            if self.state.spline_control_points:
                new_idx = min(remove_idx, len(self.state.spline_control_points) - 1)
                self.view.spline_points_listbox.selection_clear(0, tk.END)
                self.view.spline_points_listbox.selection_set(new_idx)
                self.view.spline_points_listbox.see(new_idx)
            
            self.update_preview_spline()

    def on_rmb_click_rectangle(self, event):

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

        if self.view.polygon_radius_entry.get():
            self.view.polygon_radius_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.polygon_center_x_entry.get():
            self.view.polygon_center_x_entry.delete(0, tk.END); self.view.polygon_center_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_polygon()

    def on_rmb_click_dimension(self, event=None):
        kind = self._get_dimension_mode_kind()
        if kind in ("horizontal", "vertical", "aligned", "angular"):
            if self.state.dimension_creation_refs:
                self.state.dimension_creation_refs.pop()
        elif kind in ("radius", "diameter"):
            if self.state.dimension_creation_refs:
                self.state.dimension_creation_refs = []
            else:
                self.state.dimension_creation_object = None
        self.state.points_clicked = len(self.state.dimension_creation_refs)
        self.update_preview_dimension()

    def on_rmb_click_spline(self, event):

        self.on_remove_last_spline_point()

    def on_rmb_click(self, event):
        if self.view.p2_x_entry.get():
            self.view.p2_x_entry.delete(0, tk.END); self.view.p2_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.p1_x_entry.get():
            self.view.p1_x_entry.delete(0, tk.END); self.view.p1_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_segment()

    def on_rmb_click_tangent_segment(self, event):
        if self.state.tangent_creation_circles:
            self.state.tangent_creation_circles.pop()
            self.state.points_clicked = len(self.state.tangent_creation_circles)
            self.state.preview_segment = None
            self.redraw_all()
        else:
            self.set_app_state('IDLE')

    def on_rmb_click_circle(self, event):

        method = self.state.circle_creation_method

        if method in ['center_radius', 'center_diameter']:
            if self.view.circle_param_entry.get():
                self.view.circle_param_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.circle_center_x_entry.get():
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'two_points':
            if self.view.circle_p2_x_entry.get():
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.state.points_clicked = 1
            elif self.view.circle_center_x_entry.get():
                self.view.circle_center_x_entry.delete(0, tk.END)
                self.view.circle_center_y_entry.delete(0, tk.END)
                self.state.points_clicked = 0
        elif method == 'three_points':
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
            + self.state.points
            + self.state.dimensions
        )
        if not all_objects:
            self.state.pan_x, self.state.pan_y = 0, 0
            self.state.zoom = 10.0
            self.redraw_all()
            self.view.canvas.focus_set()
            return

        xs, ys = [], []

        for p in self.state.points:
            xs.append(p.x); ys.append(p.y)

        for seg in self.state.segments:
            xs.extend([seg.p1.x, seg.p2.x])
            ys.extend([seg.p1.y, seg.p2.y])

        for circle in self.state.circles:
            xs.extend([circle.center.x - circle.radius, circle.center.x + circle.radius])
            ys.extend([circle.center.y - circle.radius, circle.center.y + circle.radius])

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

        for rect in self.state.rectangles:
            xs.extend([rect.min_x, rect.max_x])
            ys.extend([rect.min_y, rect.max_y])

        for ellipse in self.state.ellipses:
            min_x_e, max_x_e, min_y_e, max_y_e = ellipse.bounding_box()
            xs.extend([min_x_e, max_x_e])
            ys.extend([min_y_e, max_y_e])

        for poly in self.state.polygons:
            verts = poly.vertices()
            for v in verts:
                xs.append(v.x); ys.append(v.y)

        for spline in self.state.splines:
            for p in spline.sample_points():
                xs.append(p.x); ys.append(p.y)

        for dimension in self.state.dimensions:
            geometry = dimension.resolve_geometry(self.state)
            if not geometry:
                continue
            for seg in geometry.get("segments", []):
                xs.extend([seg.p1.x, seg.p2.x])
                ys.extend([seg.p1.y, seg.p2.y])
            for arc in geometry.get("arcs", []):
                xs.append(arc.center.x - arc.radius)
                xs.append(arc.center.x + arc.radius)
                ys.append(arc.center.y - arc.radius)
                ys.append(arc.center.y + arc.radius)
            tp = geometry.get("text_point")
            if tp:
                xs.append(tp.x)
                ys.append(tp.y)

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
            for dimension in self.state.selected_dimensions:
                dimension.color = c
            if self.state.preview_spline:
                self.state.preview_spline.color = c
            if self.state.preview_dimension:
                self.state.preview_dimension.color = c
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
    
    def _clear_info_panel(self):

        self.view.length_var.set("")
        self.view.angle_var.set("")
        self.view.p1_coord_var.set("")
        self.view.p2_coord_var.set("")
        self.view.p3_coord_var.set("")

    def update_info_panel(self):
        self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = None, None, None, None

        if self.state.app_mode == 'CREATING_SEGMENT':
            self._clear_info_panel()
            try: self.state.active_p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
            except (ValueError, tk.TclError): pass
            try:
                p1_for_p2, self.state.active_p2 = self._create_points_from_entries()
                if self.state.active_p1 is None: self.state.active_p1 = p1_for_p2
            except (ValueError, tk.TclError): pass
            
            p1, p2 = self.state.active_p1, self.state.active_p2
            if p1 and p2:
                seg = Segment(p1, p2)
                self.view.length_var.set(f"Длина: {seg.length:.2f}")
                angle = seg.angle
                val = math.degrees(angle) if self.view.angle_units.get() == 'degrees' else angle
                sym = "°" if self.view.angle_units.get() == 'degrees' else " рад"
                self.view.angle_var.set(f"Угол: {val:.2f}{sym}")
                self.view.p1_coord_var.set(f"P1: ({p1.x:.2f}; {p1.y:.2f})")
                self.view.p2_coord_var.set(f"P2: ({p2.x:.2f}; {p2.y:.2f})")
            return

        if self.state.app_mode == 'CREATING_CIRCLE':
            self._clear_info_panel()
            method = self.state.circle_creation_method
            center = None
            radius = None

            try:
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                center = Point(center_x, center_y)
                self.state.active_p1 = center
            except (ValueError, tk.TclError):
                pass

            if method == 'center_radius':
                try:
                    radius = float(self.view.circle_param_entry.get())
                except (ValueError, tk.TclError):
                    pass
            elif method == 'center_diameter':
                try:
                    diameter = float(self.view.circle_param_entry.get())
                    radius = diameter / 2.0
                except (ValueError, tk.TclError):
                    pass
            elif method in ['two_points', 'three_points']:
                try:
                    p2_x = float(self.view.circle_p2_x_entry.get())
                    p2_y = float(self.view.circle_p2_y_entry.get())
                    self.state.active_p2 = Point(p2_x, p2_y)
                    if center:
                        radius = math.sqrt((p2_x - center.x)**2 + (p2_y - center.y)**2) / 2.0
                        center = Point((center.x + p2_x) / 2, (center.y + p2_y) / 2)
                except (ValueError, tk.TclError):
                    pass
                if method == 'three_points':
                    try:
                        p3_x = float(self.view.circle_p3_x_entry.get())
                        p3_y = float(self.view.circle_p3_y_entry.get())
                        self.state.active_p3 = Point(p3_x, p3_y)
                    except (ValueError, tk.TclError):
                        pass

            if center and radius:
                self.view.length_var.set(f"Диаметр: {radius * 2:.2f}")
                self.view.angle_var.set(f"Радиус: {radius:.2f}")
                self.view.p1_coord_var.set(f"Центр: ({center.x:.2f}; {center.y:.2f})")
            return

        if self.state.app_mode == 'CREATING_ARC':
            self._clear_info_panel()
            method = self.state.arc_creation_method
            angle_unit = self.view.angle_units.get()
            sym = "°" if angle_unit == 'degrees' else " рад"
            arc_preview = self.state.preview_arc
            
            center = None
            radius = None
            sweep = None

            if method == 'three_points':
                p1 = p2 = p3 = None
                try:
                    p1 = Point(float(self.view.arc_p1_x_entry.get()), float(self.view.arc_p1_y_entry.get()))
                    self.state.active_p1 = p1
                except (ValueError, tk.TclError): pass
                try:
                    p2 = Point(float(self.view.arc_p2_x_entry.get()), float(self.view.arc_p2_y_entry.get()))
                    self.state.active_p2 = p2
                except (ValueError, tk.TclError): pass
                try:
                    p3 = Point(float(self.view.arc_p3_x_entry.get()), float(self.view.arc_p3_y_entry.get()))
                    self.state.active_p3 = p3
                except (ValueError, tk.TclError): pass
            else:
                try:
                    center = Point(float(self.view.arc_center_x_entry.get()), float(self.view.arc_center_y_entry.get()))
                    self.state.active_p1 = center
                except (ValueError, tk.TclError): pass
                try:
                    radius = float(self.view.arc_radius_entry.get())
                except (ValueError, tk.TclError): pass
                try:
                    start_val = float(self.view.arc_start_angle_entry.get())
                    start_ang = math.radians(start_val) if angle_unit == 'degrees' else start_val
                    if center and radius:
                        self.state.active_p2 = Point(center.x + radius * math.cos(start_ang), center.y + radius * math.sin(start_ang))
                except (ValueError, tk.TclError): pass
                try:
                    end_val = float(self.view.arc_end_angle_entry.get())
                    end_ang = math.radians(end_val) if angle_unit == 'degrees' else end_val
                    if center and radius:
                        self.state.active_p3 = Point(center.x + radius * math.cos(end_ang), center.y + radius * math.sin(end_ang))
                except (ValueError, tk.TclError): pass

            if arc_preview:
                center = arc_preview.center
                radius = arc_preview.radius
                sweep = arc_preview.sweep_angle
                if method != 'three_points':
                    self.state.active_p1 = center
                    self.state.active_p2 = Point(center.x + radius * math.cos(arc_preview.start_angle),
                                                 center.y + radius * math.sin(arc_preview.start_angle))
                    self.state.active_p3 = Point(center.x + radius * math.cos(arc_preview.end_angle),
                                                 center.y + radius * math.sin(arc_preview.end_angle))

            if center and radius:
                if sweep:
                    sweep_disp = math.degrees(sweep) if angle_unit == 'degrees' else sweep
                    self.view.length_var.set(f"Угол дуги: {sweep_disp:.2f}{sym}")
                self.view.angle_var.set(f"Радиус: {radius:.2f}")
                self.view.p1_coord_var.set(f"Центр: ({center.x:.2f}; {center.y:.2f})")
            return

        if self.state.app_mode == 'CREATING_RECTANGLE':
            self._clear_info_panel()
            rect_preview = self.state.preview_rectangle
            method = self.state.rectangle_creation_method

            rect = None
            if rect_preview:
                rect = rect_preview
                corners = rect_preview.corners()
                if len(corners) >= 4:
                    self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
            else:
                if method == 'two_points':
                    try:
                        p1 = Point(float(self.view.rect_p1_x_entry.get()), float(self.view.rect_p1_y_entry.get()))
                        p2 = Point(float(self.view.rect_p2_x_entry.get()), float(self.view.rect_p2_y_entry.get()))
                        self.state.active_p1 = p1
                        self.state.active_p2 = p2
                        rect = Rectangle.from_two_points(p1, p2, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                    except (ValueError, tk.TclError): pass
                elif method == 'corner_size':
                    try:
                        corner_pt = Point(float(self.view.rect_corner_x_entry.get()), float(self.view.rect_corner_y_entry.get()))
                        w = float(self.view.rect_width_entry.get())
                        h = float(self.view.rect_height_entry.get())
                        self.state.active_p1 = corner_pt
                        rect = Rectangle.from_corner_size(corner_pt, w, h, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                    except (ValueError, tk.TclError): pass
                elif method == 'center_size':
                    try:
                        center_pt = Point(float(self.view.rect_center_x_entry.get()), float(self.view.rect_center_y_entry.get()))
                        w = float(self.view.rect_center_w_entry.get())
                        h = float(self.view.rect_center_h_entry.get())
                        self.state.active_p1 = center_pt
                        rect = Rectangle.from_center_size(center_pt, w, h, style_name=self.state.current_style_name, color=self.state.current_color)
                        corners = rect.corners()
                        if len(corners) >= 4:
                            self.state.active_p1, self.state.active_p2, self.state.active_p3, self.state.active_p4 = corners[:4]
                    except (ValueError, tk.TclError): pass

            if rect:
                self.view.length_var.set(f"Длина: {rect.width:.2f}")
                self.view.angle_var.set(f"Ширина: {rect.height:.2f}")
                self.view.p1_coord_var.set(f"P1: ({rect.min_x:.2f}; {rect.min_y:.2f})")
                self.view.p2_coord_var.set(f"P2: ({rect.max_x:.2f}; {rect.max_y:.2f})")
                corner_type_ru = {'none': 'нет', 'chamfer': 'фаска', 'fillet': 'скругление'}.get(rect.corner_type, rect.corner_type)
                self.view.p3_coord_var.set(f"Углы: {corner_type_ru} {rect.corner_value:.2f}")
            return

        if self.state.app_mode == 'CREATING_ELLIPSE':
            self._clear_info_panel()
            center = axis_a = axis_b = None
            try:
                center = Point(float(self.view.ellipse_center_x_entry.get()), float(self.view.ellipse_center_y_entry.get()))
                self.state.active_p1 = center
            except (ValueError, tk.TclError): pass
            try:
                axis_a = Point(float(self.view.ellipse_a_x_entry.get()), float(self.view.ellipse_a_y_entry.get()))
                self.state.active_p2 = axis_a
            except (ValueError, tk.TclError): pass
            try:
                axis_b = Point(float(self.view.ellipse_b_x_entry.get()), float(self.view.ellipse_b_y_entry.get()))
                self.state.active_p3 = axis_b
            except (ValueError, tk.TclError): pass

            if center:
                self.view.length_var.set(f"Центр: ({center.x:.2f}; {center.y:.2f})")
            if axis_a:
                self.view.angle_var.set(f"Точка A: ({axis_a.x:.2f}; {axis_a.y:.2f})")
            if axis_b:
                self.view.p1_coord_var.set(f"Точка B: ({axis_b.x:.2f}; {axis_b.y:.2f})")
            return

        if self.state.app_mode == 'CREATING_POLYGON':
            self._clear_info_panel()
            center = None
            radius = None
            try:
                center = Point(float(self.view.polygon_center_x_entry.get()), float(self.view.polygon_center_y_entry.get()))
                self.state.active_p1 = center
            except (ValueError, tk.TclError): pass
            try:
                radius = float(self.view.polygon_radius_entry.get())
            except (ValueError, tk.TclError): pass

            sides = self.state.polygon_sides
            variant = self.view.polygon_variant.get()
            variant_ru = 'вписанный' if variant == 'inscribed' else 'описанный'

            if self.state.preview_polygon:
                verts = self.state.preview_polygon.vertices()
                if verts:
                    self.state.active_p2 = verts[0]
                if len(verts) > 1:
                    self.state.active_p3 = verts[1]

            if center:
                self.view.length_var.set(f"Центр: ({center.x:.2f}; {center.y:.2f})")
            self.view.angle_var.set(f"Количество углов: {sides}")
            self.view.p1_coord_var.set(f"Тип: {variant_ru}")
            if radius:
                self.view.p2_coord_var.set(f"Радиус: {radius:.2f}")
            return

        if self.state.app_mode == 'CREATING_SPLINE':
            self._clear_info_panel()
            count = len(self.state.spline_control_points)
            length = 0.0
            first = last = None

            if count:
                first = self.state.spline_control_points[0]
                last = self.state.spline_control_points[-1]
                self.state.active_p1 = first
                self.state.active_p2 = last

            if self.state.preview_spline:
                length = self.state.preview_spline.approximate_length()

            if length > 0:
                self.view.length_var.set(f"Длина: {length:.2f}")
            self.view.angle_var.set(f"Количество точек: {count}")
            if first:
                self.view.p1_coord_var.set(f"Точка старта: ({first.x:.2f}; {first.y:.2f})")
            if last:
                self.view.p2_coord_var.set(f"Точка финиша: ({last.x:.2f}; {last.y:.2f})")
            return

        if self._is_dimension_mode():
            self._clear_info_panel()
            preview = self.state.preview_dimension
            kind = self._get_dimension_mode_kind()
            names = {
                "horizontal": "Линейный размер",
                "vertical": "Вертикальный размер",
                "aligned": "Выровненный размер",
                "radius": "Радиус",
                "diameter": "Диаметр",
                "angular": "Угол",
            }
            self.view.length_var.set(f"Тип: {names.get(kind, 'Размер')}")
            if preview:
                self.view.angle_var.set(f"Значение: {preview.display_text(self.state)}")
                grips = preview.grip_points(self.state)
                if "p1" in grips:
                    self.view.p1_coord_var.set(f"P1: ({grips['p1'].x:.2f}; {grips['p1'].y:.2f})")
                if "p2" in grips:
                    self.view.p2_coord_var.set(f"P2: ({grips['p2'].x:.2f}; {grips['p2'].y:.2f})")
            return

        if self.state.selected_segments:
            self._clear_info_panel()
            seg = self.state.selected_segments[0]
            angle = seg.angle
            val = math.degrees(angle) if self.view.angle_units.get() == 'degrees' else angle
            sym = "°" if self.view.angle_units.get() == 'degrees' else " рад"
            self.view.length_var.set(f"Длина: {seg.length:.2f}")
            self.view.angle_var.set(f"Угол: {val:.2f}{sym}")
            self.view.p1_coord_var.set(f"P1: ({seg.p1.x:.2f}; {seg.p1.y:.2f})")
            self.view.p2_coord_var.set(f"P2: ({seg.p2.x:.2f}; {seg.p2.y:.2f})")
            return

        if self.state.selected_circles:
            self._clear_info_panel()
            circle = self.state.selected_circles[0]
            self.view.length_var.set(f"Диаметр: {circle.diameter:.2f}")
            self.view.angle_var.set(f"Радиус: {circle.radius:.2f}")
            self.view.p1_coord_var.set(f"Центр: ({circle.center.x:.2f}; {circle.center.y:.2f})")
            return

        if self.state.selected_arcs:
            self._clear_info_panel()
            arc = self.state.selected_arcs[0]
            angle_unit = self.view.angle_units.get()
            sym = "°" if angle_unit == 'degrees' else " рад"
            sweep_disp = math.degrees(arc.sweep_angle) if angle_unit == 'degrees' else arc.sweep_angle
            self.view.length_var.set(f"Угол дуги: {sweep_disp:.2f}{sym}")
            self.view.angle_var.set(f"Радиус: {arc.radius:.2f}")
            self.view.p1_coord_var.set(f"Центр: ({arc.center.x:.2f}; {arc.center.y:.2f})")
            return

        if self.state.selected_rectangles:
            self._clear_info_panel()
            rect = self.state.selected_rectangles[0]
            corner_type_ru = {'none': 'нет', 'chamfer': 'фаска', 'fillet': 'скругление'}.get(rect.corner_type, rect.corner_type)
            self.view.length_var.set(f"Длина: {rect.width:.2f}")
            self.view.angle_var.set(f"Ширина: {rect.height:.2f}")
            self.view.p1_coord_var.set(f"P1: ({rect.min_x:.2f}; {rect.min_y:.2f})")
            self.view.p2_coord_var.set(f"P2: ({rect.max_x:.2f}; {rect.max_y:.2f})")
            self.view.p3_coord_var.set(f"Углы: {corner_type_ru} {rect.corner_value:.2f}")
            return

        if self.state.selected_ellipses:
            self._clear_info_panel()
            ell = self.state.selected_ellipses[0]
            self.view.length_var.set(f"Центр: ({ell.center.x:.2f}; {ell.center.y:.2f})")
            self.view.angle_var.set(f"Точка A: ({ell.axis_point_a.x:.2f}; {ell.axis_point_a.y:.2f})")
            self.view.p1_coord_var.set(f"Точка B: ({ell.axis_point_b.x:.2f}; {ell.axis_point_b.y:.2f})")
            return

        if self.state.selected_polygons:
            self._clear_info_panel()
            poly = self.state.selected_polygons[0]
            variant_ru = 'вписанный' if poly.variant == 'inscribed' else 'описанный'
            self.view.length_var.set(f"Центр: ({poly.center.x:.2f}; {poly.center.y:.2f})")
            self.view.angle_var.set(f"Количество углов: {poly.sides}")
            self.view.p1_coord_var.set(f"Тип: {variant_ru}")
            self.view.p2_coord_var.set(f"Радиус: {poly.base_radius:.2f}")
            return

        if self.state.selected_splines:
            self._clear_info_panel()
            sp = self.state.selected_splines[0]
            pts = sp.control_points
            self.view.length_var.set(f"Длина: {sp.approximate_length():.2f}")
            self.view.angle_var.set(f"Количество точек: {len(pts)}")
            if pts:
                self.view.p1_coord_var.set(f"Точка старта: ({pts[0].x:.2f}; {pts[0].y:.2f})")
                self.view.p2_coord_var.set(f"Точка финиша: ({pts[-1].x:.2f}; {pts[-1].y:.2f})")
            return

        if self.state.selected_dimensions:
            self._clear_info_panel()
            dim = self.state.selected_dimensions[0]
            self.view.length_var.set(f"Размер: {dim.display_text(self.state)}")
            self.view.angle_var.set(f"Стиль: {dim.dimension_style_name}")
            self.view.p1_coord_var.set(f"Слой: {dim.layer}")
            return

        self._clear_info_panel()

    def on_reset_view(self, event=None):
        self.state.pan_x = 0
        self.state.pan_y = 0
        self.state.zoom = 10.0 
        self.state.rotation = 0.0
        self.redraw_all()
        self.view.canvas.focus_set()

    def on_mouse_move_stats(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        
        snap_point = None
        if self.snap_manager and self.state.snap_enabled:
            from_point = None
            if self.state.points_clicked >= 1 and self.state.active_p1:
                from_point = self.state.active_p1
            
            snap_radius_world = self.state.snap_radius_px / self.state.zoom
            
            snap_point = self.snap_manager.find_snap_point(
                wx, wy, snap_radius_world, from_point
            )
        
        self.state.current_snap_point = snap_point
        
        display_x, display_y = wx, wy
        if snap_point:
            display_x, display_y = snap_point.x, snap_point.y
        
        snap_indicator = ""
        if snap_point:
            from logic.snap import SNAP_NAMES
            snap_indicator = f" [{SNAP_NAMES.get(snap_point.snap_type, '')}]"
        self.view.status_coords.config(text=f"X: {display_x:.2f}  Y: {display_y:.2f}{snap_indicator}")
        
        self._update_preview_on_mouse_move(display_x, display_y)
        
        if self.state.app_mode.startswith('CREATING_'):
            self.redraw_all()
        elif snap_point is not None:
            self.redraw_all()
        elif hasattr(self, '_last_snap_point') and self._last_snap_point is not None:
            self.redraw_all()
        
        self._last_snap_point = snap_point
    
    def _update_preview_on_mouse_move(self, wx, wy):

        mode = self.state.app_mode
        
        if mode == 'CREATING_SEGMENT':
            self._update_segment_preview_mouse(wx, wy)
        elif mode == 'CREATING_TANGENT_SEGMENT':
            self._update_tangent_segment_preview(wx, wy)
        elif mode == 'CREATING_CIRCLE':
            self._update_circle_preview_mouse(wx, wy)
        elif mode == 'CREATING_ARC':
            self._update_arc_preview_mouse(wx, wy)
        elif mode == 'CREATING_RECTANGLE':
            self._update_rectangle_preview_mouse(wx, wy)
        elif mode == 'CREATING_ELLIPSE':
            self._update_ellipse_preview_mouse(wx, wy)
        elif mode == 'CREATING_POLYGON':
            self._update_polygon_preview_mouse(wx, wy)
        elif mode == 'CREATING_SPLINE':
            self._update_spline_preview_mouse(wx, wy)
        elif self._is_dimension_mode(mode):
            self._update_dimension_preview_mouse(wx, wy)
    
    def _update_segment_preview_mouse(self, wx, wy):

        if self.state.points_clicked == 1 and self.state.active_p1:
            p1 = self.state.active_p1
            p2 = Point(wx, wy)
            self.state.preview_segment = Segment(
                p1, p2,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
            self.view.p2_x_entry.delete(0, tk.END)
            self.view.p2_x_entry.insert(0, f"{wx:.2f}")
            self.view.p2_y_entry.delete(0, tk.END)
            self.view.p2_y_entry.insert(0, f"{wy:.2f}")
    
    def _update_circle_preview_mouse(self, wx, wy):

        method = self.state.circle_creation_method
        
        if method in ['center_radius', 'center_diameter'] and self.state.points_clicked == 1:
            try:
                center_x = float(self.view.circle_center_x_entry.get())
                center_y = float(self.view.circle_center_y_entry.get())
                distance = math.sqrt((wx - center_x)**2 + (wy - center_y)**2)
                
                if method == 'center_radius':
                    value = distance
                    self.view.circle_param_entry.delete(0, tk.END)
                    self.view.circle_param_entry.insert(0, f"{value:.2f}")
                    self.state.preview_circle = Circle.from_center_radius(
                        Point(center_x, center_y), value,
                        style_name=self.state.current_style_name,
                        color=self.state.current_color
                    )
                else:
                    value = distance * 2
                    self.view.circle_param_entry.delete(0, tk.END)
                    self.view.circle_param_entry.insert(0, f"{value:.2f}")
                    self.state.preview_circle = Circle.from_center_diameter(
                        Point(center_x, center_y), value,
                        style_name=self.state.current_style_name,
                        color=self.state.current_color
                    )
            except (ValueError, tk.TclError):
                pass
        
        elif method == 'two_points' and self.state.points_clicked == 1:
            try:
                p1_x = float(self.view.circle_center_x_entry.get())
                p1_y = float(self.view.circle_center_y_entry.get())
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
                self.state.preview_circle = Circle.from_two_points(
                    Point(p1_x, p1_y), Point(wx, wy),
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            except (ValueError, tk.TclError):
                pass
        
        elif method == 'three_points':
            if self.state.points_clicked == 1:
                self.view.circle_p2_x_entry.delete(0, tk.END)
                self.view.circle_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.circle_p2_y_entry.delete(0, tk.END)
                self.view.circle_p2_y_entry.insert(0, f"{wy:.2f}")
            elif self.state.points_clicked == 2:
                try:
                    p1_x = float(self.view.circle_center_x_entry.get())
                    p1_y = float(self.view.circle_center_y_entry.get())
                    p2_x = float(self.view.circle_p2_x_entry.get())
                    p2_y = float(self.view.circle_p2_y_entry.get())
                    self.view.circle_p3_x_entry.delete(0, tk.END)
                    self.view.circle_p3_x_entry.insert(0, f"{wx:.2f}")
                    self.view.circle_p3_y_entry.delete(0, tk.END)
                    self.view.circle_p3_y_entry.insert(0, f"{wy:.2f}")
                    self.state.preview_circle = Circle.from_three_points(
                        Point(p1_x, p1_y), Point(p2_x, p2_y), Point(wx, wy),
                        style_name=self.state.current_style_name,
                        color=self.state.current_color
                    )
                except (ValueError, tk.TclError):
                    pass
    
    def _update_arc_preview_mouse(self, wx, wy):

        method = self.state.arc_creation_method
        
        if method == 'three_points':
            if self.state.points_clicked == 1:
                self.view.arc_p2_x_entry.delete(0, tk.END)
                self.view.arc_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.arc_p2_y_entry.delete(0, tk.END)
                self.view.arc_p2_y_entry.insert(0, f"{wy:.2f}")
            elif self.state.points_clicked == 2:
                try:
                    p1 = Point(float(self.view.arc_p1_x_entry.get()), float(self.view.arc_p1_y_entry.get()))
                    p2 = Point(float(self.view.arc_p2_x_entry.get()), float(self.view.arc_p2_y_entry.get()))
                    p3 = Point(wx, wy)
                    self.view.arc_p3_x_entry.delete(0, tk.END)
                    self.view.arc_p3_x_entry.insert(0, f"{wx:.2f}")
                    self.view.arc_p3_y_entry.delete(0, tk.END)
                    self.view.arc_p3_y_entry.insert(0, f"{wy:.2f}")
                    self.state.preview_arc = Arc.from_three_points(
                        p1, p2, p3,
                        style_name=self.state.current_style_name,
                        color=self.state.current_color
                    )
                except (ValueError, tk.TclError):
                    pass
    
    def _update_rectangle_preview_mouse(self, wx, wy):

        method = self.state.rectangle_creation_method
        
        if method == 'two_points' and self.state.points_clicked == 1:
            try:
                p1_x = float(self.view.rect_p1_x_entry.get())
                p1_y = float(self.view.rect_p1_y_entry.get())
                self.view.rect_p2_x_entry.delete(0, tk.END)
                self.view.rect_p2_x_entry.insert(0, f"{wx:.2f}")
                self.view.rect_p2_y_entry.delete(0, tk.END)
                self.view.rect_p2_y_entry.insert(0, f"{wy:.2f}")
                
                corner_type = self.view.rect_corner_type.get()
                try:
                    corner_val = float(self.view.rect_corner_value_entry.get())
                except (ValueError, tk.TclError):
                    corner_val = 0.0
                
                self.state.preview_rectangle = Rectangle.from_two_points(
                    Point(p1_x, p1_y), Point(wx, wy),
                    style_name=self.state.current_style_name,
                    color=self.state.current_color,
                    corner_type=corner_type,
                    corner_value=corner_val
                )
            except (ValueError, tk.TclError):
                pass
    
    def _update_ellipse_preview_mouse(self, wx, wy):

        if self.state.points_clicked == 1:
            try:
                center_x = float(self.view.ellipse_center_x_entry.get())
                center_y = float(self.view.ellipse_center_y_entry.get())
                self.view.ellipse_a_x_entry.delete(0, tk.END)
                self.view.ellipse_a_x_entry.insert(0, f"{wx:.2f}")
                self.view.ellipse_a_y_entry.delete(0, tk.END)
                self.view.ellipse_a_y_entry.insert(0, f"{wy:.2f}")
            except (ValueError, tk.TclError):
                pass
        elif self.state.points_clicked == 2:
            try:
                center_x = float(self.view.ellipse_center_x_entry.get())
                center_y = float(self.view.ellipse_center_y_entry.get())
                axis_a_x = float(self.view.ellipse_a_x_entry.get())
                axis_a_y = float(self.view.ellipse_a_y_entry.get())
                self.view.ellipse_b_x_entry.delete(0, tk.END)
                self.view.ellipse_b_x_entry.insert(0, f"{wx:.2f}")
                self.view.ellipse_b_y_entry.delete(0, tk.END)
                self.view.ellipse_b_y_entry.insert(0, f"{wy:.2f}")
                self.state.preview_ellipse = Ellipse.from_center_axes(
                    Point(center_x, center_y),
                    Point(axis_a_x, axis_a_y),
                    Point(wx, wy),
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            except (ValueError, tk.TclError):
                pass
    
    def _update_polygon_preview_mouse(self, wx, wy):

        if self.state.points_clicked == 1:
            try:
                center_x = float(self.view.polygon_center_x_entry.get())
                center_y = float(self.view.polygon_center_y_entry.get())
                radius = math.sqrt((wx - center_x)**2 + (wy - center_y)**2)
                self.view.polygon_radius_entry.delete(0, tk.END)
                self.view.polygon_radius_entry.insert(0, f"{radius:.2f}")
                
                sides = int(self.view.polygon_sides_var.get())
                variant = self.view.polygon_variant.get()
                
                start_angle = math.atan2(wy - center_y, wx - center_x)
                self.state.polygon_start_angle = start_angle
                
                self.state.preview_polygon = RegularPolygon.from_center_radius(
                    Point(center_x, center_y), radius, sides,
                    variant=variant,
                    start_angle=start_angle,
                    style_name=self.state.current_style_name,
                    color=self.state.current_color
                )
            except (ValueError, tk.TclError):
                pass
    
    def _update_spline_preview_mouse(self, wx, wy):

        # При перетаскивании — не добавлять фантомную точку
        if self.state.dragging_spline_point_index is not None:
            return

        if len(self.state.spline_control_points) >= 1:
            ctrl_copy = [Point(p.x, p.y) for p in self.state.spline_control_points]
            ctrl_copy.append(Point(wx, wy))
            self.state.preview_spline = Spline(
                ctrl_copy,
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
        else:
            self.state.preview_spline = None

    def _update_dimension_preview_mouse(self, wx, wy):
        kind = self._get_dimension_mode_kind()

        if kind in ("horizontal", "vertical", "aligned"):
            if len(self.state.dimension_creation_refs) >= 2:
                line_ref = GeometryReference.static(Point(wx, wy))
                if len(self.state.dimension_creation_refs) == 2:
                    refs = self.state.dimension_creation_refs + [line_ref]
                else:
                    refs = self.state.dimension_creation_refs[:2] + [line_ref]
                self.state.dimension_creation_refs = refs
                self.update_preview_dimension()
        elif kind in ("radius", "diameter"):
            if self.state.dimension_creation_object is not None:
                ref = GeometryReference.static(Point(wx, wy))
                if self.state.dimension_creation_refs:
                    self.state.dimension_creation_refs[0] = ref
                else:
                    self.state.dimension_creation_refs = [ref]
                self.update_preview_dimension()
        elif kind == "angular":
            if len(self.state.dimension_creation_refs) >= 3:
                ref = GeometryReference.static(Point(wx, wy))
                if len(self.state.dimension_creation_refs) == 3:
                    self.state.dimension_creation_refs.append(ref)
                else:
                    self.state.dimension_creation_refs[3] = ref
                self.update_preview_dimension()

    def on_idle_drag(self, event):
        drag = self.state.dimension_grip_drag
        if not drag:
            return

        wx, wy = self._get_snapped_coordinates(event.x, event.y)
        new_point = Point(wx, wy)
        dimension = drag["dimension"]
        grip_name = drag["grip"]
        dimension.move_grip(grip_name, new_point, self.state)
        self._sync_ui_with_selection()
        self.redraw_all()

    def on_idle_release(self, event):
        self.state.dimension_grip_drag = None
    
    def _get_snapped_coordinates(self, event_x, event_y):

        wx, wy = self.converter.screen_to_world(event_x, event_y)
        
        if self.state.current_snap_point:
            return self.state.current_snap_point.x, self.state.current_snap_point.y
        
        return wx, wy

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
            + len(self.state.selected_dimensions)
        )
        
        is_editing = self.state.editing_object is not None
        
        if is_editing:
            edit_modes = {
                'segment': "Редактирование отрезка",
                'circle': "Редактирование окружности",
                'arc': "Редактирование дуги",
                'rectangle': "Редактирование прямоугольника",
                'ellipse': "Редактирование эллипса",
                'polygon': "Редактирование многоугольника",
                'spline': "Редактирование сплайна",
                'dimension': "Редактирование размера"
            }
            mode_text = edit_modes.get(self.state.editing_object_type, "Редактирование")
        elif total_selected > 0:
             mode_text = f"Выбрано объектов: {total_selected}"
        else:
            modes = {
                'IDLE': "Ожидание",
                'CREATING_SEGMENT': "Создание отрезка",
                'CREATING_TANGENT_SEGMENT': "Касательная к двум окружностям",
                'CREATING_CIRCLE': "Создание окружности",
                'CREATING_ARC': "Создание дуги",
                'CREATING_RECTANGLE': "Создание прямоугольника",
                'CREATING_ELLIPSE': "Создание эллипса",
                'CREATING_POLYGON': "Создание многоугольника",
                'CREATING_SPLINE': "Создание сплайна",
                'CREATING_DIMENSION_HORIZONTAL': "Создание линейного размера",
                'CREATING_DIMENSION_VERTICAL': "Создание вертикального размера",
                'CREATING_DIMENSION_ALIGNED': "Создание выровненного размера",
                'CREATING_DIMENSION_RADIUS': "Создание радиуса",
                'CREATING_DIMENSION_DIAMETER': "Создание диаметра",
                'CREATING_DIMENSION_ANGULAR': "Создание углового размера",
                'PANNING': "Панорамирование"
            }
            mode_text = modes.get(self.state.app_mode, self.state.app_mode)

        self.view.status_mode.config(text=f"Режим: {mode_text}")

        # Слой выделенных объектов
        all_selected = (
            list(self.state.selected_segments) +
            list(self.state.selected_circles) +
            list(self.state.selected_arcs) +
            list(self.state.selected_rectangles) +
            list(self.state.selected_ellipses) +
            list(self.state.selected_polygons) +
            list(self.state.selected_splines) +
            list(self.state.selected_dimensions)
        )
        if not all_selected:
            self.view.status_layer.config(text="")
        else:
            layers = set(getattr(obj, 'layer', '0') for obj in all_selected)
            if len(layers) == 1:
                self.view.status_layer.config(text=f"Слой: {layers.pop()}")
            else:
                self.view.status_layer.config(text="Разные слои")

    def show_context_menu(self, event):
        if self.state.app_mode in ['CREATING_SEGMENT', 'CREATING_TANGENT_SEGMENT', 'CREATING_CIRCLE', 'CREATING_ARC', 'CREATING_RECTANGLE', 'CREATING_ELLIPSE', 'CREATING_POLYGON', 'CREATING_SPLINE'] or self._is_dimension_mode():
            if self.state.app_mode == 'CREATING_SEGMENT':
                self.on_rmb_click(event)
            elif self.state.app_mode == 'CREATING_TANGENT_SEGMENT':
                self.on_rmb_click_tangent_segment(event)
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
            elif self._is_dimension_mode():
                self.on_rmb_click_dimension(event)
            else:
                self.on_rmb_click_spline(event)
        else:
            total_selected = (
                len(self.state.selected_segments)
                + len(self.state.selected_circles)
                + len(self.state.selected_arcs)
                + len(self.state.selected_rectangles)
                + len(self.state.selected_ellipses)
                + len(self.state.selected_polygons)
                + len(self.state.selected_splines)
                + len(self.state.selected_dimensions)
            )
            if total_selected == 1:
                self.view.context_menu.entryconfig(0, state='normal')
            else:
                self.view.context_menu.entryconfig(0, state='disabled')
            
            self.view.context_menu.post(event.x_root, event.y_root)

    def on_styles_updated(self):
        self.view.refresh_style_combobox_values(self.state.line_styles)
        self.view.refresh_dimension_line_style_combobox_values(self.state.line_styles)
        
        self.redraw_all()
        
        self._sync_ui_with_selection()

    def on_open_style_manager(self):
        StyleManagerWindow(self.root, self.state, self.on_styles_updated)

    def on_quick_style_set(self, style_key):
        if style_key not in self.state.line_styles:
            return

        self.state.current_style_name = style_key
        
        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                seg.style_name = style_key
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
            self.view.set_style_selection(style_key)

        self.update_preview_segment()
        self.update_preview_circle()
        self.update_preview_arc()
        self.update_preview_rectangle()
        self.update_preview_ellipse()
        self.update_preview_polygon()
        self.update_preview_spline()
        self.redraw_all()

    def on_snap_toggle(self):

        self.state.snap_enabled = self.view.snap_enabled_var.get()
        self.redraw_all()
    
    def on_snap_setting_changed(self):

        self.state.snap_endpoint = self.view.snap_endpoint_var.get()
        self.state.snap_midpoint = self.view.snap_midpoint_var.get()
        self.state.snap_center = self.view.snap_center_var.get()
        self.state.snap_intersection = self.view.snap_intersection_var.get()
        self.state.snap_perpendicular = self.view.snap_perpendicular_var.get()
        self.state.snap_tangent = self.view.snap_tangent_var.get()
        self.state.snap_grid = self.view.snap_grid_var.get()
        self.redraw_all()
    
    def on_open_snap_settings(self):

        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки привязок")
        dialog.geometry("320x380")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Настройки системы привязок", font=('Arial', 11, 'bold')).pack(pady=10)
        
        canvas_frame = ttk.Frame(dialog)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_frame = scrollable_frame
        
        ttk.Checkbutton(
            main_frame, text="Включить привязки (глобально)",
            variable=self.view.snap_enabled_var,
            command=self.on_snap_toggle
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Обязательные привязки:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        
        ttk.Checkbutton(main_frame, text="□ Конец - концы отрезков, вершины",
                       variable=self.view.snap_endpoint_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        ttk.Checkbutton(main_frame, text="△ Середина - середины отрезков",
                       variable=self.view.snap_midpoint_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        ttk.Checkbutton(main_frame, text="○ Центр - центры окружностей, дуг",
                       variable=self.view.snap_center_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Дополнительные привязки:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        
        ttk.Checkbutton(main_frame, text="× Пересечение",
                       variable=self.view.snap_intersection_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        ttk.Checkbutton(main_frame, text="⊥ Перпендикуляр*",
                       variable=self.view.snap_perpendicular_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        ttk.Checkbutton(main_frame, text="◇ Касательная*",
                       variable=self.view.snap_tangent_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        
        ttk.Label(main_frame, text="* Работают после первой точки", 
                 font=('Arial', 8)).pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Сетка:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        ttk.Checkbutton(main_frame, text="+ Привязка к сетке",
                       variable=self.view.snap_grid_var, command=self.on_snap_setting_changed).pack(anchor=tk.W)
        
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        ttk.Label(main_frame, text="Радиус привязки (пиксели):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        radius_frame = ttk.Frame(main_frame)
        radius_frame.pack(fill=tk.X, pady=5)
        
        self._snap_radius_var = tk.StringVar(value=str(self.state.snap_radius_px))
        snap_radius_entry = ttk.Entry(radius_frame, textvariable=self._snap_radius_var, width=8)
        snap_radius_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        def apply_radius():
            try:
                val = int(self._snap_radius_var.get())
                if val > 0:
                    self.state.snap_radius_px = val
            except ValueError:
                pass
        
        ttk.Button(radius_frame, text="Применить", command=apply_radius).pack(side=tk.LEFT)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        ttk.Button(btn_frame, text="Закрыть", command=lambda: (canvas.unbind_all("<MouseWheel>"), dialog.destroy())).pack()

    # ── Callbacks для слоёв ──

    def _get_selected_layer_name(self):
        """Получить имя слоя по выбранному индексу в Listbox."""
        sel = self.view.layers_listbox.curselection()
        if not sel:
            return None
        idx = sel[0]
        if 0 <= idx < len(self.state.layers):
            return self.state.layers[idx].name
        return None

    def on_layer_selected(self, event=None):
        pass  # Выбор отрабатывает в toggle/double_click

    def on_layer_double_click(self, event=None):
        """Двойной клик → сделать слой активным."""
        name = self._get_selected_layer_name()
        if name:
            self.state.active_layer = name
            self.view.active_layer_var.set(f"Активный слой: {name}")
            self.view.refresh_layers_list(self.state)

    def on_add_layer(self, event=None):
        """Добавить новый слой через диалог."""
        name = simpledialog.askstring("Новый слой", "Имя слоя:", parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        if not self.state.add_layer(name):
            messagebox.showwarning("Слой", f"Слой «{name}» уже существует.")
            return
        self.view.refresh_layers_list(self.state)

    def on_delete_layer(self, event=None):
        """Удалить выбранный слой."""
        name = self._get_selected_layer_name()
        if not name:
            messagebox.showinfo("Слой", "Выберите слой для удаления.")
            return
        if name == "0":
            messagebox.showwarning("Слой", "Слой «0» нельзя удалить.")
            return
        if not messagebox.askyesno("Удалить слой", f"Удалить слой «{name}»?\nОбъекты будут перенесены на слой «0»."):
            return
        self.state.delete_layer(name)
        self.view.active_layer_var.set(f"Активный слой: {self.state.active_layer}")
        self.view.refresh_layers_list(self.state)
        self.renderer.render_scene()

    def on_toggle_layer_visibility(self, event=None):
        """Переключить видимость выбранного слоя."""
        name = self._get_selected_layer_name()
        if not name:
            return
        layer = self.state.get_layer(name)
        if layer:
            layer.visible = not layer.visible
            self.view.refresh_layers_list(self.state)
            self.renderer.render_scene()

    def on_move_to_layer(self, event=None):
        """Переместить выделенные примитивы на выбранный слой."""
        name = self._get_selected_layer_name()
        if not name:
            messagebox.showinfo("Слой", "Выберите целевой слой в списке.")
            return

        all_selected = (
            self.state.selected_segments +
            self.state.selected_circles +
            self.state.selected_arcs +
            self.state.selected_rectangles +
            self.state.selected_ellipses +
            self.state.selected_polygons +
            self.state.selected_splines +
            self.state.selected_dimensions
        )
        if not all_selected:
            messagebox.showinfo("Слой", "Сначала выделите объекты для переноса.")
            return

        for obj in all_selected:
            obj.layer = name

        self.view.refresh_layers_list(self.state)
        self.renderer.render_scene()
