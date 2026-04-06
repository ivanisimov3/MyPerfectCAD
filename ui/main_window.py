import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser 
import math
from logic.styles import GOST_STYLES

class MainWindow:
    def __init__(self, root, callbacks):
        self.root = root
        self.callbacks = callbacks 
        
        root.title("MyPerfectCAD")
        root.minsize(950, 600)
        
        root.columnconfigure(0, weight=1)
        self.sidebar_width = 360
        root.columnconfigure(1, weight=0, minsize=self.sidebar_width)
        root.rowconfigure(1, weight=1)

        self.setup_main_menu(root, callbacks)
        
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self._setup_toolbar_buttons(toolbar, callbacks)

        self.canvas = tk.Canvas(root, borderwidth=2, relief="sunken", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        self.sidebar_container = tk.Frame(root, width=self.sidebar_width)
        self.sidebar_container.grid(row=1, column=1, sticky=('N', 'S', 'E', 'W'), padx=5, pady=5)
        self.sidebar_container.pack_propagate(False)
        self.sidebar_container.grid_propagate(False)

        settings_panel = ttk.LabelFrame(self.sidebar_container, text="Настройки", padding="5")
        settings_panel.pack(fill=tk.BOTH, expand=True)
        self.setup_settings_panel(settings_panel, callbacks)
        
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.setup_info_panel(info_panel)
        
        status_bar = ttk.Frame(root, relief="sunken", padding="2")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.setup_status_bar(status_bar)

        self.create_context_menu(root, callbacks)
        
        self.canvas.bind("<Configure>", callbacks.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", callbacks.on_mouse_press)
        self.canvas.bind("<B2-Motion>", callbacks.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-4>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-5>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Motion>", callbacks.on_mouse_move_stats)
        self.canvas.bind("<Button-3>", callbacks.show_context_menu)
        self.canvas.bind("<Double-Button-1>", callbacks.on_double_click)

        self.root.bind("<F11>", callbacks.toggle_fullscreen)
        self.root.bind("<Escape>", callbacks.on_escape_key)
        self.root.bind("<Delete>", callbacks.on_delete_segment)
        self.root.bind("<plus>", callbacks.on_zoom_in)
        self.root.bind("<equal>", callbacks.on_zoom_in)
        self.root.bind("<minus>", callbacks.on_zoom_out)
        self.root.bind("<Left>", callbacks.on_rotate_left)
        self.root.bind("<Right>", callbacks.on_rotate_right)
        self.root.bind("<Shift-Left>", callbacks.on_rotate_left)
        self.root.bind("<Shift-Right>", callbacks.on_rotate_right)

    def _setup_toolbar_buttons(self, parent, callbacks):
        def _popup(menu, event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        def _add_icon_button(symbol, default_cmd, menu_items):

            btn = ttk.Button(parent, text=symbol, width=4, command=default_cmd)
            btn.pack(side=tk.LEFT, padx=3)

            if menu_items:
                menu = tk.Menu(btn, tearoff=0)
                for label, cmd in menu_items:
                    menu.add_command(label=label, command=cmd)
                btn.bind("<Button-3>", lambda e, m=menu: _popup(m, e))

        def _start_circle(method):
            self.circle_method.set(method)
            self._on_circle_method_change(callbacks)
            callbacks.on_new_circle_mode()

        def _start_arc(method):
            self.arc_method.set(method)
            self._on_arc_method_change(callbacks)
            callbacks.on_new_arc_mode()

        def _start_rectangle(method):
            self.rect_method.set(method)
            self._on_rectangle_method_change(callbacks)
            callbacks.on_new_rectangle_mode()

        def _start_polygon(variant):
            self.polygon_variant.set(variant)
            callbacks.on_polygon_variant_change()
            callbacks.on_new_polygon_mode()

        def _start_linear_dimension(mode):
            callbacks.on_new_linear_dimension_mode(mode)

        _add_icon_button("—", callbacks.on_new_segment_mode, [
            ("Отрезок (2 точки)", callbacks.on_new_segment_mode),
        ])

        _add_icon_button("◯", callbacks.on_new_circle_mode, [
            ("Центр + радиус", lambda: _start_circle("center_radius")),
            ("Центр + диаметр", lambda: _start_circle("center_diameter")),
            ("Диаметр по 2 точкам", lambda: _start_circle("two_points")),
            ("Через 3 точки", lambda: _start_circle("three_points")),
        ])

        _add_icon_button("⌒", callbacks.on_new_arc_mode, [
            ("Три точки", lambda: _start_arc("three_points")),
            ("Центр + углы", lambda: _start_arc("center_angles")),
        ])

        _add_icon_button("▭", callbacks.on_new_rectangle_mode, [
            ("Две точки", lambda: _start_rectangle("two_points")),
            ("Угол + ширина/высота", lambda: _start_rectangle("corner_size")),
            ("Центр + ширина/высота", lambda: _start_rectangle("center_size")),
        ])

        _add_icon_button("⬭", callbacks.on_new_ellipse_mode, [
            ("Центр + оси", callbacks.on_new_ellipse_mode),
        ])

        _add_icon_button("⬟", callbacks.on_new_polygon_mode, [
            ("Вписанный", lambda: _start_polygon("inscribed")),
            ("Описанный", lambda: _start_polygon("circumscribed")),
        ])

        _add_icon_button("~", callbacks.on_new_spline_mode, [
            ("Точки управления", callbacks.on_new_spline_mode),
        ])

        _add_icon_button("⟷", callbacks.on_new_linear_dimension_mode, [
            ("Линейный горизонтальный", lambda: _start_linear_dimension("horizontal")),
            ("Линейный вертикальный", lambda: _start_linear_dimension("vertical")),
            ("Линейный выровненный", lambda: _start_linear_dimension("aligned")),
            ("Радиус", callbacks.on_new_radius_dimension_mode),
            ("Диаметр", callbacks.on_new_diameter_dimension_mode),
            ("Угол", callbacks.on_new_angular_dimension_mode),
        ])

        ttk.Button(parent, text="Удалить", width=8, command=callbacks.on_delete_segment).pack(side=tk.LEFT, padx=4)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        ttk.Button(parent, text="Рука", width=6, command=callbacks.on_hand_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="+", width=3, command=callbacks.on_zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="-", width=3, command=callbacks.on_zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="Вписать", width=8, command=callbacks.on_fit_to_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="↶", width=3, command=callbacks.on_rotate_left).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="↷", width=3, command=callbacks.on_rotate_right).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="0°", width=3, command=callbacks.on_reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        style_mb = ttk.Menubutton(parent, text="Стиль")
        style_menu = tk.Menu(style_mb, tearoff=0)
        style_menu.add_command(label="Основная", command=lambda: callbacks.on_quick_style_set('solid_main'))
        style_menu.add_command(label="Тонкая", command=lambda: callbacks.on_quick_style_set('solid_thin'))
        style_menu.add_command(label="Штриховая", command=lambda: callbacks.on_quick_style_set('dashed'))
        style_menu.add_command(label="Осевая", command=lambda: callbacks.on_quick_style_set('dash_dot_thin'))
        style_menu.add_separator()
        style_menu.add_command(label="Менеджер стилей…", command=callbacks.on_open_style_manager)
        style_mb["menu"] = style_menu
        style_mb.pack(side=tk.LEFT, padx=2)

    def setup_main_menu(self, root, callbacks):

        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Импорт из DXF...", command=callbacks.on_import_dxf)
        file_menu.add_command(label="Экспорт в DXF...", command=callbacks.on_export_dxf)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        style_menu = tk.Menu(menubar, tearoff=0)
        style_menu.add_command(label="Менеджер стилей...", command=callbacks.on_open_style_manager)
        menubar.add_cascade(label="Стили", menu=style_menu)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Рука (Панорама)", command=callbacks.on_hand_mode)
        view_menu.add_separator()
        view_menu.add_command(label="Увеличить (+)", command=callbacks.on_zoom_in)
        view_menu.add_command(label="Уменьшить (-)", command=callbacks.on_zoom_out)
        view_menu.add_command(label="Показать все", command=callbacks.on_fit_to_view)
        view_menu.add_separator()
        view_menu.add_command(label="Повернуть влево", command=callbacks.on_rotate_left)
        view_menu.add_command(label="Повернуть вправо", command=callbacks.on_rotate_right)
        view_menu.add_separator()
        view_menu.add_command(label="Сбросить вид", command=callbacks.on_reset_view)
        menubar.add_cascade(label="Вид", menu=view_menu)

    def setup_status_bar(self, parent):
        self.status_coords = ttk.Label(parent, text="X: 0.00  Y: 0.00", width=20)
        self.status_coords.pack(side=tk.LEFT, padx=5)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.status_zoom = ttk.Label(parent, text="Zoom: 100%", width=15)
        self.status_zoom.pack(side=tk.LEFT, padx=5)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.status_angle = ttk.Label(parent, text="Angle: 0.0°", width=15)
        self.status_angle.pack(side=tk.LEFT, padx=5)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        self.status_layer = ttk.Label(parent, text="Слой: 0", width=15)
        self.status_layer.pack(side=tk.LEFT, padx=5)

        self.status_mode = ttk.Label(parent, text="Режим: Ожидание", anchor=tk.E)
        self.status_mode.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    def create_context_menu(self, root, callbacks):

        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="Редактировать", command=callbacks.on_edit_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Рука", command=callbacks.on_hand_mode)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Показать все", command=callbacks.on_fit_to_view)
        self.context_menu.add_command(label="Сбросить вид", command=callbacks.on_reset_view)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отмена", command=lambda: None)

    def setup_settings_panel(self, parent, callbacks):

        self.coord_system = tk.StringVar(value="cartesian")
        self.angle_units = tk.StringVar(value="degrees")

        self.settings_notebook = ttk.Notebook(parent)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.general_tab = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.general_tab, text="Общие")
        self._setup_general_tab(self.general_tab, callbacks)

        self.context_tab = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.context_tab, text="Контекст")

        self.context_title_var = tk.StringVar(value="—")
        ttk.Label(self.context_tab, textvariable=self.context_title_var).pack(anchor=tk.W, padx=6, pady=(6, 4))

        self.context_hint = ttk.Label(
            self.context_tab,
            text="Выберите один объект или начните построение примитива."
        )
        self.context_hint.pack(anchor=tk.W, padx=6, pady=(0, 6))

        self.context_canvas = tk.Canvas(self.context_tab, highlightthickness=0, borderwidth=0)
        self.context_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.context_pages_container = ttk.Frame(self.context_canvas)
        self.context_canvas_window = self.context_canvas.create_window(
            (0, 0),
            window=self.context_pages_container,
            anchor="nw",
        )
        self.context_pages_container.bind("<Configure>", self._on_context_inner_configure)
        self.context_canvas.bind("<Configure>", self._on_context_canvas_configure)
        self.context_canvas.bind("<Enter>", self._bind_context_mousewheel)
        self.context_canvas.bind("<Leave>", self._unbind_context_mousewheel)

        self._context_pages = {}

        segment_page = ttk.Frame(self.context_pages_container)
        self._context_pages["segment"] = segment_page
        self._setup_segment_tab(segment_page, callbacks)

        circle_page = ttk.Frame(self.context_pages_container)
        self._context_pages["circle"] = circle_page
        self._setup_circle_tab(circle_page, callbacks)

        arc_page = ttk.Frame(self.context_pages_container)
        self._context_pages["arc"] = arc_page
        self._setup_arc_tab(arc_page, callbacks)

        rectangle_page = ttk.Frame(self.context_pages_container)
        self._context_pages["rectangle"] = rectangle_page
        self._setup_rectangle_tab(rectangle_page, callbacks)

        ellipse_page = ttk.Frame(self.context_pages_container)
        self._context_pages["ellipse"] = ellipse_page
        self._setup_ellipse_tab(ellipse_page, callbacks)

        polygon_page = ttk.Frame(self.context_pages_container)
        self._context_pages["polygon"] = polygon_page
        self._setup_polygon_tab(polygon_page, callbacks)

        spline_page = ttk.Frame(self.context_pages_container)
        self._context_pages["spline"] = spline_page
        self._setup_spline_tab(spline_page, callbacks)

        dimension_page = ttk.Frame(self.context_pages_container)
        self._context_pages["dimension"] = dimension_page
        self._setup_dimension_tab(dimension_page, callbacks)

        for page in self._context_pages.values():
            page.pack_forget()

        self._active_context_key = None

        # ── Вкладка «Слои» ──
        self.layers_tab = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.layers_tab, text="Слои")
        self._setup_layers_tab(self.layers_tab, callbacks)

    def set_context_panel(self, key, title=None):

        if getattr(self, "_active_context_key", None) in getattr(self, "_context_pages", {}):
            self._context_pages[self._active_context_key].pack_forget()
        self._active_context_key = None

        if not key:
            self.context_title_var.set(title or "—")
            self.context_hint.pack(anchor=tk.W, padx=6, pady=(0, 6))
            return

        page = self._context_pages.get(key)
        if not page:
            self.context_title_var.set(title or "—")
            self.context_hint.pack(anchor=tk.W, padx=6, pady=(0, 6))
            return

        self.context_title_var.set(title or "Параметры")
        self.context_hint.pack_forget()
        page.pack(fill=tk.BOTH, expand=True)
        self.context_canvas.yview_moveto(0.0)
        self._active_context_key = key

    def _on_context_inner_configure(self, event=None):
        self.context_canvas.configure(scrollregion=self.context_canvas.bbox("all"))

    def _on_context_canvas_configure(self, event):
        self.context_canvas.itemconfigure(self.context_canvas_window, width=event.width)

    def _bind_context_mousewheel(self, event=None):
        self.context_canvas.bind_all("<MouseWheel>", self._on_context_mousewheel)

    def _unbind_context_mousewheel(self, event=None):
        self.context_canvas.unbind_all("<MouseWheel>")

    def _on_context_mousewheel(self, event):
        if self.context_canvas.winfo_exists():
            self.context_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _setup_general_tab(self, parent, callbacks):
        style_frame = ttk.LabelFrame(parent, text="Стиль линии")
        style_frame.pack(padx=5, pady=5, fill=tk.X)
        
        self.prop_preview_canvas = tk.Canvas(style_frame, width=200, height=40, bg="white", relief="sunken", borderwidth=1)
        self.prop_preview_canvas.pack(padx=5, pady=(5, 0))

        self.prop_preview_canvas.bind("<Configure>", lambda e: self.update_style_preview(self.callbacks.state.current_style_name))
        
        self.style_ids = []
        style_names = []

        sorted_items = sorted(GOST_STYLES.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        for key, style in sorted_items:
            style_names.append(style.display_name)
            self.style_ids.append(key)

        self.style_combobox = ttk.Combobox(style_frame, values=style_names, state="readonly")
        
        current = callbacks.state.current_style_name
        if current in self.style_ids:
            idx = self.style_ids.index(current)
            self.style_combobox.current(idx)
        elif self.style_ids:
            self.style_combobox.current(0)
        self.style_combobox.pack(fill=tk.X, padx=5, pady=5)

        self.style_combobox.bind("<<ComboboxSelected>>", callbacks.on_style_selected)
        
        ttk.Button(style_frame, text="Настроить стили...", command=callbacks.on_open_style_manager).pack(fill=tk.X, padx=5, pady=(0, 5))

        dim_style_frame = ttk.LabelFrame(parent, text="Стиль размера")
        dim_style_frame.pack(padx=5, pady=5, fill=tk.X)

        self.dimension_style_ids = []
        dim_style_names = []
        for key, style in sorted(callbacks.state.dimension_styles.items(), key=lambda x: x[1].display_name):
            self.dimension_style_ids.append(key)
            dim_style_names.append(style.display_name)

        self.dimension_style_combobox = ttk.Combobox(dim_style_frame, values=dim_style_names, state="readonly")
        current_dim_style = callbacks.state.current_dimension_style_name
        if current_dim_style in self.dimension_style_ids:
            self.dimension_style_combobox.current(self.dimension_style_ids.index(current_dim_style))
        elif self.dimension_style_ids:
            self.dimension_style_combobox.current(0)
        self.dimension_style_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.dimension_style_combobox.bind("<<ComboboxSelected>>", callbacks.on_dimension_style_selected)

        snap_frame = ttk.LabelFrame(parent, text="Привязки")
        snap_frame.pack(padx=5, pady=5, fill=tk.X)
        
        self.snap_enabled_var = tk.BooleanVar(value=True)
        snap_enable_row = ttk.Frame(snap_frame)
        snap_enable_row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Checkbutton(
            snap_enable_row, 
            text="Включить привязки", 
            variable=self.snap_enabled_var,
            command=callbacks.on_snap_toggle
        ).pack(side=tk.LEFT)
        
        ttk.Button(snap_enable_row, text="⚙", width=3, command=callbacks.on_open_snap_settings).pack(side=tk.RIGHT)
        
        mandatory_frame = ttk.Frame(snap_frame)
        mandatory_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.snap_endpoint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            mandatory_frame, text="□ Конец", 
            variable=self.snap_endpoint_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        self.snap_midpoint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            mandatory_frame, text="△ Середина", 
            variable=self.snap_midpoint_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        self.snap_center_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            mandatory_frame, text="○ Центр", 
            variable=self.snap_center_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        additional_frame = ttk.Frame(snap_frame)
        additional_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.snap_intersection_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            additional_frame, text="× Пересечение", 
            variable=self.snap_intersection_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        special_frame = ttk.Frame(snap_frame)
        special_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.snap_perpendicular_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            special_frame, text="⊥ Перпендикуляр", 
            variable=self.snap_perpendicular_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        self.snap_tangent_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            special_frame, text="◇ Касательная", 
            variable=self.snap_tangent_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)
        
        grid_snap_frame = ttk.Frame(snap_frame)
        grid_snap_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        
        self.snap_grid_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            grid_snap_frame, text="+ К сетке", 
            variable=self.snap_grid_var,
            command=callbacks.on_snap_setting_changed
        ).pack(side=tk.LEFT)

        grid_frame = ttk.LabelFrame(parent, text="Сетка")
        grid_frame.pack(padx=5, pady=5, fill=tk.X)

        self.grid_step_var = tk.StringVar(value="10")
        ttk.Label(grid_frame, text="Шаг:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(grid_frame, textvariable=self.grid_step_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(grid_frame, text="Применить", command=callbacks.on_apply_settings).pack(side=tk.LEFT, padx=5)
        
        color_frame = ttk.LabelFrame(parent, text="Цвета")
        color_frame.pack(padx=5, pady=5, fill=tk.X)

        self.bg_swatch = self._create_color_chooser(color_frame, "Фон:", callbacks.on_choose_bg_color)

        self.grid_swatch = self._create_color_chooser(color_frame, "Сетка:", callbacks.on_choose_grid_color)

        self.segment_swatch = self._create_color_chooser(color_frame, "Линии:", callbacks.on_choose_segment_color)

    def _setup_segment_tab(self, parent, callbacks):

        p1_frame = ttk.LabelFrame(parent, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p1_label1, self.p1_x_entry = self._create_coord_entry(p1_frame, "X₁:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))
        self.p1_label2, self.p1_y_entry = self._create_coord_entry(p1_frame, "Y₁:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))

        p2_frame = ttk.LabelFrame(parent, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p2_label1, self.p2_x_entry = self._create_coord_entry(p2_frame, "X₂:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))
        self.p2_label2, self.p2_y_entry = self._create_coord_entry(p2_frame, "Y₂:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))

        ttk.Radiobutton(parent, text="P2: Декартова (X₂,Y₂)", variable=self.coord_system, value="cartesian", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5, pady=(5,0))
        ttk.Radiobutton(parent, text="P2: Полярная (R₂,θ₂)", variable=self.coord_system, value="polar", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5)

        angle_frame = ttk.LabelFrame(parent, text="Единицы угла")
        angle_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=lambda: (callbacks.update_preview_segment(), callbacks.update_preview_circle(), callbacks.update_preview_arc())).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=lambda: (callbacks.update_preview_segment(), callbacks.update_preview_circle(), callbacks.update_preview_arc())).pack(anchor=tk.W)

    def _setup_circle_tab(self, parent, callbacks):
        circle_frame = ttk.LabelFrame(parent, text="Метод создания окружности")
        circle_frame.pack(padx=5, pady=5, fill=tk.X)

        self.circle_method = tk.StringVar(value="center_radius")

        ttk.Radiobutton(circle_frame, text="Центр и радиус", variable=self.circle_method, value="center_radius",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="Центр и диаметр", variable=self.circle_method, value="center_diameter",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="Две точки (диаметр)", variable=self.circle_method, value="two_points",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="3 точки на окружности", variable=self.circle_method, value="three_points",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        self.circle_input_frame = ttk.LabelFrame(parent, text="Координаты")
        self.circle_input_frame.pack(padx=5, pady=5, fill=tk.X)

        center_frame = ttk.LabelFrame(self.circle_input_frame, text="Центр")
        center_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_center_label1, self.circle_center_x_entry = self._create_coord_entry(center_frame, "X₁:", callbacks.update_preview_circle)
        self.circle_center_label2, self.circle_center_y_entry = self._create_coord_entry(center_frame, "Y₁:", callbacks.update_preview_circle)

        self.circle_param_frame = ttk.Frame(self.circle_input_frame)
        self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
        self.circle_param_label, self.circle_param_entry = self._create_coord_entry(self.circle_param_frame, "R:", callbacks.update_preview_circle)

        self.circle_p2_frame = ttk.LabelFrame(self.circle_input_frame, text="Точка 2")
        self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_p2_label1, self.circle_p2_x_entry = self._create_coord_entry(self.circle_p2_frame, "X₂:", callbacks.update_preview_circle)
        self.circle_p2_label2, self.circle_p2_y_entry = self._create_coord_entry(self.circle_p2_frame, "Y₂:", callbacks.update_preview_circle)

        self.circle_p3_frame = ttk.LabelFrame(self.circle_input_frame, text="Точка 3")
        self.circle_p3_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_p3_label1, self.circle_p3_x_entry = self._create_coord_entry(self.circle_p3_frame, "X₃:", callbacks.update_preview_circle)
        self.circle_p3_label2, self.circle_p3_y_entry = self._create_coord_entry(self.circle_p3_frame, "Y₃:", callbacks.update_preview_circle)

        self.circle_param_frame.pack_forget()
        self.circle_p2_frame.pack_forget()
        self.circle_p3_frame.pack_forget()

        self._update_circle_params_ui()

    def _setup_arc_tab(self, parent, callbacks):
        self.arc_method = tk.StringVar(value="three_points")

        method_frame = ttk.LabelFrame(parent, text="Метод создания дуги")
        method_frame.pack(padx=5, pady=5, fill=tk.X)

        ttk.Radiobutton(method_frame, text="Три точки", variable=self.arc_method, value="three_points",
                        command=lambda: self._on_arc_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Центр, углы", variable=self.arc_method, value="center_angles",
                        command=lambda: self._on_arc_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        self.arc_three_points_frame = ttk.LabelFrame(parent, text="Точки дуги")
        self.arc_three_points_frame.pack(padx=5, pady=5, fill=tk.X)
        self.arc_p1_label1, self.arc_p1_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₁:", callbacks.update_preview_arc)
        self.arc_p1_label2, self.arc_p1_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₁:", callbacks.update_preview_arc)
        self.arc_p2_label1, self.arc_p2_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₂:", callbacks.update_preview_arc)
        self.arc_p2_label2, self.arc_p2_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₂:", callbacks.update_preview_arc)
        self.arc_p3_label1, self.arc_p3_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₃:", callbacks.update_preview_arc)
        self.arc_p3_label2, self.arc_p3_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₃:", callbacks.update_preview_arc)

        self.arc_center_frame = ttk.LabelFrame(parent, text="Центр")
        self.arc_center_x_label, self.arc_center_x_entry = self._create_coord_entry(self.arc_center_frame, "Xc:", callbacks.update_preview_arc)
        self.arc_center_y_label, self.arc_center_y_entry = self._create_coord_entry(self.arc_center_frame, "Yc:", callbacks.update_preview_arc)

        self.arc_radius_frame = ttk.Frame(parent)
        self.arc_radius_label, self.arc_radius_entry = self._create_coord_entry(self.arc_radius_frame, "R:", callbacks.update_preview_arc)

        self.arc_angles_frame = ttk.LabelFrame(parent, text="Углы")
        self.arc_start_label, self.arc_start_angle_entry = self._create_coord_entry(self.arc_angles_frame, "θ₁:", callbacks.update_preview_arc)
        self.arc_end_label, self.arc_end_angle_entry = self._create_coord_entry(self.arc_angles_frame, "θ₂:", callbacks.update_preview_arc)

        self._update_arc_params_ui()

    def _setup_rectangle_tab(self, parent, callbacks):
        self.rect_method = tk.StringVar(value="two_points")

        method_frame = ttk.LabelFrame(parent, text="Метод создания")
        method_frame.pack(padx=5, pady=5, fill=tk.X)

        ttk.Radiobutton(method_frame, text="Две точки", variable=self.rect_method, value="two_points",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Точка, ширина/высота", variable=self.rect_method, value="corner_size",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Центр, ширина/высота", variable=self.rect_method, value="center_size",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        self.rect_two_points_frame = ttk.LabelFrame(parent, text="Точки")
        self.rect_p1_label1, self.rect_p1_x_entry = self._create_coord_entry(self.rect_two_points_frame, "X₁:", callbacks.update_preview_rectangle)
        self.rect_p1_label2, self.rect_p1_y_entry = self._create_coord_entry(self.rect_two_points_frame, "Y₁:", callbacks.update_preview_rectangle)
        self.rect_p2_label1, self.rect_p2_x_entry = self._create_coord_entry(self.rect_two_points_frame, "X₂:", callbacks.update_preview_rectangle)
        self.rect_p2_label2, self.rect_p2_y_entry = self._create_coord_entry(self.rect_two_points_frame, "Y₂:", callbacks.update_preview_rectangle)

        self.rect_corner_frame = ttk.LabelFrame(parent, text="Вершина + размеры")
        self.rect_corner_label1, self.rect_corner_x_entry = self._create_coord_entry(self.rect_corner_frame, "X:", callbacks.update_preview_rectangle)
        self.rect_corner_label2, self.rect_corner_y_entry = self._create_coord_entry(self.rect_corner_frame, "Y:", callbacks.update_preview_rectangle)
        self.rect_width_label, self.rect_width_entry = self._create_coord_entry(self.rect_corner_frame, "W:", callbacks.update_preview_rectangle)
        self.rect_height_label, self.rect_height_entry = self._create_coord_entry(self.rect_corner_frame, "H:", callbacks.update_preview_rectangle)

        self.rect_center_frame = ttk.LabelFrame(parent, text="Центр + размеры")
        self.rect_center_label1, self.rect_center_x_entry = self._create_coord_entry(self.rect_center_frame, "Xc:", callbacks.update_preview_rectangle)
        self.rect_center_label2, self.rect_center_y_entry = self._create_coord_entry(self.rect_center_frame, "Yc:", callbacks.update_preview_rectangle)
        self.rect_center_w_label, self.rect_center_w_entry = self._create_coord_entry(self.rect_center_frame, "W:", callbacks.update_preview_rectangle)
        self.rect_center_h_label, self.rect_center_h_entry = self._create_coord_entry(self.rect_center_frame, "H:", callbacks.update_preview_rectangle)

        corner_frame = ttk.LabelFrame(parent, text="Углы")
        corner_frame.pack(padx=5, pady=5, fill=tk.X)
        self.rect_corner_type = tk.StringVar(value="none")
        ttk.Radiobutton(corner_frame, text="Без обработки", variable=self.rect_corner_type, value="none",
                        command=callbacks.update_preview_rectangle).pack(anchor=tk.W, padx=5, pady=1)
        ttk.Radiobutton(corner_frame, text="Фаска", variable=self.rect_corner_type, value="chamfer",
                        command=callbacks.update_preview_rectangle).pack(anchor=tk.W, padx=5, pady=1)
        ttk.Radiobutton(corner_frame, text="Скругление", variable=self.rect_corner_type, value="fillet",
                        command=callbacks.update_preview_rectangle).pack(anchor=tk.W, padx=5, pady=1)

        val_frame = ttk.Frame(corner_frame)
        val_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(val_frame, text="Размер:").pack(side=tk.LEFT)
        self.rect_corner_value_entry = ttk.Entry(val_frame, width=8)
        self.rect_corner_value_entry.pack(side=tk.LEFT, padx=5)
        self.rect_corner_value_entry.bind("<KeyRelease>", callbacks.update_preview_rectangle)

        self._update_rectangle_params_ui()

    def _setup_ellipse_tab(self, parent, callbacks):
        self.ellipse_method = tk.StringVar(value="center_axes")

        ttk.Label(parent, text="Способ: центр + концы осей").pack(anchor=tk.W, padx=8, pady=(4, 0))

        coords_frame = ttk.LabelFrame(parent, text="Координаты")
        coords_frame.pack(padx=5, pady=5, fill=tk.X)

        center_frame = ttk.LabelFrame(coords_frame, text="Центр")
        center_frame.pack(padx=5, pady=5, fill=tk.X)
        self.ellipse_center_label1, self.ellipse_center_x_entry = self._create_coord_entry(center_frame, "Xc:", callbacks.update_preview_ellipse)
        self.ellipse_center_label2, self.ellipse_center_y_entry = self._create_coord_entry(center_frame, "Yc:", callbacks.update_preview_ellipse)

        axis_a_frame = ttk.LabelFrame(coords_frame, text="Конец оси A")
        axis_a_frame.pack(padx=5, pady=5, fill=tk.X)
        self.ellipse_a_label1, self.ellipse_a_x_entry = self._create_coord_entry(axis_a_frame, "Xa:", callbacks.update_preview_ellipse)
        self.ellipse_a_label2, self.ellipse_a_y_entry = self._create_coord_entry(axis_a_frame, "Ya:", callbacks.update_preview_ellipse)

        axis_b_frame = ttk.LabelFrame(coords_frame, text="Конец оси B")
        axis_b_frame.pack(padx=5, pady=5, fill=tk.X)
        self.ellipse_b_label1, self.ellipse_b_x_entry = self._create_coord_entry(axis_b_frame, "Xb:", callbacks.update_preview_ellipse)
        self.ellipse_b_label2, self.ellipse_b_y_entry = self._create_coord_entry(axis_b_frame, "Yb:", callbacks.update_preview_ellipse)

    def _setup_polygon_tab(self, parent, callbacks):
        self.polygon_method = tk.StringVar(value="center_radius")
        self.polygon_variant = tk.StringVar(value="inscribed")
        self.polygon_sides_var = tk.StringVar(value="5")

        ttk.Label(parent, text="Метод: центр + радиус").pack(anchor=tk.W, padx=8, pady=(4, 0))

        coords_frame = ttk.LabelFrame(parent, text="Координаты")
        coords_frame.pack(padx=5, pady=5, fill=tk.X)

        center_frame = ttk.LabelFrame(coords_frame, text="Центр")
        center_frame.pack(padx=5, pady=5, fill=tk.X)
        self.polygon_center_label1, self.polygon_center_x_entry = self._create_coord_entry(center_frame, "Xc:", callbacks.update_preview_polygon)
        self.polygon_center_label2, self.polygon_center_y_entry = self._create_coord_entry(center_frame, "Yc:", callbacks.update_preview_polygon)

        radius_frame = ttk.Frame(coords_frame)
        radius_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(radius_frame, text="R:").pack(side=tk.LEFT)
        self.polygon_radius_entry = ttk.Entry(radius_frame)
        self.polygon_radius_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.polygon_radius_entry.bind("<KeyRelease>", callbacks.update_preview_polygon)

        variant_frame = ttk.LabelFrame(parent, text="Вариант построения")
        variant_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Radiobutton(variant_frame, text="Вписанный", variable=self.polygon_variant, value="inscribed",
                        command=callbacks.on_polygon_variant_change).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(variant_frame, text="Описанный", variable=self.polygon_variant, value="circumscribed",
                        command=callbacks.on_polygon_variant_change).pack(anchor=tk.W, padx=5, pady=2)

        sides_frame = ttk.LabelFrame(parent, text="Количество углов")
        sides_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Label(sides_frame, text="N:").pack(side=tk.LEFT)
        self.polygon_sides_spin = ttk.Spinbox(sides_frame, from_=3, to=64, textvariable=self.polygon_sides_var, width=6, command=callbacks.on_polygon_sides_change)
        self.polygon_sides_spin.pack(side=tk.LEFT, padx=5)
        self.polygon_sides_spin.bind("<KeyRelease>", callbacks.on_polygon_sides_change)

    def _setup_spline_tab(self, parent, callbacks):
        ttk.Label(parent, text="Метод: набор контрольных точек").pack(anchor=tk.W, padx=8, pady=(4, 0))

        list_frame = ttk.LabelFrame(parent, text="Контрольные точки")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.spline_points_listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        self.spline_points_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.spline_points_listbox.bind('<<ListboxSelect>>', callbacks.on_spline_point_selected)

        manual_frame = ttk.LabelFrame(parent, text="Координаты точки")
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        row = ttk.Frame(manual_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text="X:").pack(side=tk.LEFT)
        self.spline_point_x_entry = ttk.Entry(row, width=10)
        self.spline_point_x_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row, text="Y:").pack(side=tk.LEFT)
        self.spline_point_y_entry = ttk.Entry(row, width=10)
        self.spline_point_y_entry.pack(side=tk.LEFT, padx=5)
        
        add_btns_frame = ttk.Frame(manual_frame)
        add_btns_frame.pack(fill=tk.X, padx=5, pady=(2, 2))
        ttk.Button(add_btns_frame, text="В конец", command=callbacks.on_add_spline_point_manual).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(add_btns_frame, text="Перед выбранной", command=callbacks.on_insert_spline_point_before).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(manual_frame, text="Обновить выбранную", command=callbacks.on_update_selected_spline_point).pack(fill=tk.X, padx=5, pady=(2, 5))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        del_btns_frame = ttk.Frame(btn_frame)
        del_btns_frame.pack(fill=tk.X, pady=2)
        ttk.Button(del_btns_frame, text="Удалить выбранную", command=callbacks.on_remove_selected_spline_point).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(del_btns_frame, text="Очистить все", command=callbacks.on_clear_spline_points).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        
        ttk.Button(btn_frame, text="Завершить (Enter)", command=callbacks.finalize_spline).pack(fill=tk.X, pady=2)

        ttk.Label(parent, text="Выберите точку для редактирования\nЛКМ на холсте - добавить в конец\nПКМ - удалить последнюю").pack(anchor=tk.W, padx=8, pady=4)

    def _setup_dimension_tab(self, parent, callbacks):
        info_frame = ttk.LabelFrame(parent, text="Информация")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        self.dimension_type_var = tk.StringVar(value="—")
        self.dimension_value_var = tk.StringVar(value="—")
        self.dimension_layer_var = tk.StringVar(value="Слой: —")

        ttk.Label(info_frame, textvariable=self.dimension_type_var).pack(anchor=tk.W, padx=5, pady=(4, 2))
        ttk.Label(info_frame, textvariable=self.dimension_value_var).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.dimension_layer_var).pack(anchor=tk.W, padx=5, pady=(2, 4))

        text_frame = ttk.LabelFrame(parent, text="Текст размера")
        text_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(text_frame, text="Переопределение:").pack(anchor=tk.W, padx=5, pady=(4, 2))
        self.dimension_text_override_entry = ttk.Entry(text_frame)
        self.dimension_text_override_entry.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(text_frame, text="Применить текст", command=callbacks.on_apply_dimension_text_override).pack(fill=tk.X, padx=5, pady=(0, 2))
        ttk.Button(text_frame, text="Сбросить переопределение", command=callbacks.on_reset_dimension_text_override).pack(fill=tk.X, padx=5, pady=(0, 5))

        style_frame = ttk.LabelFrame(parent, text="Стиль размера")
        style_frame.pack(fill=tk.X, padx=5, pady=5)
        self.dimension_context_style_combobox = ttk.Combobox(style_frame, state="readonly")
        self.dimension_context_style_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.dimension_context_style_combobox.bind("<<ComboboxSelected>>", callbacks.on_dimension_style_selected)

        sorted_line_styles = sorted(callbacks.state.line_styles.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        self.dimension_line_style_ids = []
        line_style_names = []
        for key, style in sorted_line_styles:
            self.dimension_line_style_ids.append(key)
            line_style_names.append(style.display_name)

        self.dimension_arrow_type_ids = ["closed", "open", "tick"]
        self.dimension_arrow_type_names = ["Закрытая", "Открытая", "Засечка"]
        self.dimension_text_position_ids = ["above", "center", "below"]
        self.dimension_text_position_names = ["Над линией", "На линии", "Под линией"]
        self.dimension_font_names = ["Arial", "Calibri", "Times New Roman", "Tahoma", "Consolas"]

        extension_frame = ttk.LabelFrame(parent, text="Выносные линии")
        extension_frame.pack(fill=tk.X, padx=5, pady=5)
        self.dimension_extension_frame = extension_frame
        self.dimension_extension_note_var = tk.StringVar(value="")
        ttk.Label(extension_frame, textvariable=self.dimension_extension_note_var).pack(anchor=tk.W, padx=5, pady=(4, 0))
        self.dimension_ext_color_swatch = self._create_color_chooser(extension_frame, "Цвет:", callbacks.on_choose_dimension_extension_color)
        ttk.Label(extension_frame, text="Тип линии:").pack(anchor=tk.W, padx=5, pady=(4, 2))
        self.dimension_ext_style_combobox = ttk.Combobox(extension_frame, values=line_style_names, state="readonly")
        self.dimension_ext_style_combobox.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(extension_frame, text="Выход за размерную:").pack(anchor=tk.W, padx=5, pady=(0, 2))
        self.dimension_ext_overrun_entry = ttk.Entry(extension_frame)
        self.dimension_ext_overrun_entry.pack(fill=tk.X, padx=5, pady=(0, 5))

        dim_line_frame = ttk.LabelFrame(parent, text="Размерная линия")
        dim_line_frame.pack(fill=tk.X, padx=5, pady=5)
        self.dimension_dim_color_swatch = self._create_color_chooser(dim_line_frame, "Цвет:", callbacks.on_choose_dimension_dim_color)
        ttk.Label(dim_line_frame, text="Тип линии:").pack(anchor=tk.W, padx=5, pady=(4, 2))
        self.dimension_dim_style_combobox = ttk.Combobox(dim_line_frame, values=line_style_names, state="readonly")
        self.dimension_dim_style_combobox.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(dim_line_frame, text="Расширение за выносные:").pack(anchor=tk.W, padx=5, pady=(0, 2))
        self.dimension_dim_extension_entry = ttk.Entry(dim_line_frame)
        self.dimension_dim_extension_entry.pack(fill=tk.X, padx=5, pady=(0, 5))

        arrow_frame = ttk.LabelFrame(parent, text="Стрелки")
        arrow_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(arrow_frame, text="Тип:").pack(anchor=tk.W, padx=5, pady=(4, 2))
        self.dimension_arrow_type_combobox = ttk.Combobox(arrow_frame, values=self.dimension_arrow_type_names, state="readonly")
        self.dimension_arrow_type_combobox.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(arrow_frame, text="Размер:").pack(anchor=tk.W, padx=5, pady=(0, 2))
        self.dimension_arrow_size_entry = ttk.Entry(arrow_frame)
        self.dimension_arrow_size_entry.pack(fill=tk.X, padx=5, pady=(0, 4))
        self.dimension_arrow_filled_var = tk.BooleanVar(value=True)
        self.dimension_arrow_filled_check = ttk.Checkbutton(arrow_frame, text="Заполненные", variable=self.dimension_arrow_filled_var)
        self.dimension_arrow_filled_check.pack(anchor=tk.W, padx=5, pady=(0, 5))

        text_style_frame = ttk.LabelFrame(parent, text="Размерный текст")
        text_style_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(text_style_frame, text="Шрифт:").pack(anchor=tk.W, padx=5, pady=(4, 2))
        self.dimension_text_font_combobox = ttk.Combobox(text_style_frame, values=self.dimension_font_names, state="readonly")
        self.dimension_text_font_combobox.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(text_style_frame, text="Высота:").pack(anchor=tk.W, padx=5, pady=(0, 2))
        self.dimension_text_height_entry = ttk.Entry(text_style_frame)
        self.dimension_text_height_entry.pack(fill=tk.X, padx=5, pady=(0, 4))
        ttk.Label(text_style_frame, text="Положение:").pack(anchor=tk.W, padx=5, pady=(0, 2))
        self.dimension_text_position_combobox = ttk.Combobox(text_style_frame, values=self.dimension_text_position_names, state="readonly")
        self.dimension_text_position_combobox.pack(fill=tk.X, padx=5, pady=(0, 5))

        appearance_btns = ttk.Frame(parent)
        appearance_btns.pack(fill=tk.X, padx=5, pady=(2, 5))
        ttk.Button(appearance_btns, text="Применить параметры", command=callbacks.on_apply_dimension_appearance).pack(fill=tk.X, pady=(0, 2))
        ttk.Button(appearance_btns, text="Сбросить к стилю", command=callbacks.on_reset_dimension_appearance).pack(fill=tk.X)

        ttk.Label(
            parent,
            text="Создание размеров:\nЛКМ по точкам или объектам,\nПКМ — шаг назад, Enter — завершить при готовности.",
        ).pack(anchor=tk.W, padx=8, pady=4)

    def _setup_layers_tab(self, parent, callbacks):

        # Listbox со слоями
        list_frame = ttk.LabelFrame(parent, text="Слои чертежа")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.layers_listbox = tk.Listbox(list_frame, height=8, exportselection=False)
        self.layers_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.layers_listbox.bind('<<ListboxSelect>>', callbacks.on_layer_selected)
        self.layers_listbox.bind('<Double-Button-1>', callbacks.on_layer_double_click)

        # Кнопки
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(btn_frame, text="Добавить", command=callbacks.on_add_layer).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(btn_frame, text="Удалить", command=callbacks.on_delete_layer).pack(
            side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        ttk.Button(parent, text="Видимость вкл/выкл", command=callbacks.on_toggle_layer_visibility).pack(
            fill=tk.X, padx=5, pady=2)

        ttk.Button(parent, text="Переместить выделенное →", command=callbacks.on_move_to_layer).pack(
            fill=tk.X, padx=5, pady=2)

        # Индикатор активного слоя
        self.active_layer_var = tk.StringVar(value="Активный слой: 0")
        ttk.Label(parent, textvariable=self.active_layer_var).pack(anchor=tk.W, padx=8, pady=(4, 2))

        ttk.Label(parent, text="Двойной клик — сделать активным\nВыбор + «Видимость» — скрыть/показать\nВыбор + «Переместить» — перенести выделенное").pack(
            anchor=tk.W, padx=8, pady=(0, 6))

    def refresh_layers_list(self, state):
        """Обновить Listbox слоёв из state."""
        lb = self.layers_listbox
        sel_idx = lb.curselection()
        lb.delete(0, tk.END)

        for layer in state.layers:
            eye = "👁" if layer.visible else "⊘"
            marker = " ► " if layer.name == state.active_layer else "   "
            lb.insert(tk.END, f"{eye}{marker}{layer.name}")

        if sel_idx and sel_idx[0] < lb.size():
            lb.selection_set(sel_idx[0])

    def setup_info_panel(self, parent):

        self.length_var = tk.StringVar(value="Длина: N/A")

        self.angle_var = tk.StringVar(value="Угол: N/A")

        self.p1_coord_var = tk.StringVar(value="P1: N/A")

        self.p2_coord_var = tk.StringVar(value="P2: N/A")

        self.p3_coord_var = tk.StringVar(value="P3: N/A")

        for var in [self.length_var, self.angle_var, self.p1_coord_var, self.p2_coord_var, self.p3_coord_var]:
            ttk.Label(parent, textvariable=var).pack(side=tk.LEFT, padx=10, pady=2)

        self.hotkey_frame = ttk.Frame(parent)

        self.lbl_enter = ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод")
        self.lbl_enter.pack(side=tk.LEFT, padx=5)
        
        self.lbl_esc = ttk.Label(self.hotkey_frame, text="⎋ Esc - Отмена")
        self.lbl_esc.pack(side=tk.LEFT, padx=5)
    
    def _create_coord_entry(self, parent, label_text, key_release_callback):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        label = ttk.Label(frame, text=label_text, width=4)
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<KeyRelease>", key_release_callback)
        return label, entry
    
    def _create_color_chooser(self, parent, text, command):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=text).pack(side=tk.LEFT, padx=5)
        swatch = tk.Label(frame, width=4, relief='sunken', borderwidth=1)
        swatch.pack(side=tk.RIGHT, padx=5)
        swatch.bind("<Button-1>", lambda e: command())
        return swatch

    def _on_circle_method_change(self, callbacks):

        method = self.circle_method.get()
        callbacks.state.circle_creation_method = method

        self.circle_param_entry.delete(0, tk.END)
        self.circle_p2_x_entry.delete(0, tk.END)
        self.circle_p2_y_entry.delete(0, tk.END)
        self.circle_p3_x_entry.delete(0, tk.END)
        self.circle_p3_y_entry.delete(0, tk.END)

        self._update_circle_params_ui()
        callbacks.update_preview_circle()

    def _update_circle_params_ui(self):

        method = self.circle_method.get()

        if method == 'center_radius':
            self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
            self.circle_param_label.config(text="R:")
            self.circle_p2_frame.pack_forget()
            self.circle_p3_frame.pack_forget()
        elif method == 'center_diameter':
            self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
            self.circle_param_label.config(text="D:")
            self.circle_p2_frame.pack_forget()
            self.circle_p3_frame.pack_forget()
        elif method == 'two_points':
            self.circle_param_frame.pack_forget()
            self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
            self.circle_p3_frame.pack_forget()
        elif method == 'three_points':
            self.circle_param_frame.pack_forget()
            self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
            self.circle_p3_frame.pack(padx=5, pady=5, fill=tk.X)

    def _on_arc_method_change(self, callbacks):

        method = self.arc_method.get()
        callbacks.state.arc_creation_method = method

        for entry in [
            self.arc_p1_x_entry, self.arc_p1_y_entry,
            self.arc_p2_x_entry, self.arc_p2_y_entry,
            self.arc_p3_x_entry, self.arc_p3_y_entry,
            self.arc_center_x_entry, self.arc_center_y_entry,
            self.arc_radius_entry, self.arc_start_angle_entry, self.arc_end_angle_entry
        ]:
            entry.delete(0, tk.END)

        self._update_arc_params_ui()
        callbacks.update_preview_arc()

    def _update_arc_params_ui(self):

        method = self.arc_method.get()

        if method == 'three_points':
            self.arc_three_points_frame.pack(padx=5, pady=5, fill=tk.X)
            self.arc_center_frame.pack_forget()
            self.arc_radius_frame.pack_forget()
            self.arc_angles_frame.pack_forget()
        else:
            self.arc_three_points_frame.pack_forget()
            self.arc_center_frame.pack(padx=5, pady=5, fill=tk.X)
            self.arc_radius_frame.pack(fill=tk.X, padx=5, pady=2)
            self.arc_angles_frame.pack(padx=5, pady=5, fill=tk.X)

    def _on_rectangle_method_change(self, callbacks):
        self.callbacks.state.rectangle_creation_method = self.rect_method.get()
        callbacks.state.points_clicked = 0
        for entry in [
            self.rect_p1_x_entry, self.rect_p1_y_entry,
            self.rect_p2_x_entry, self.rect_p2_y_entry,
            self.rect_corner_x_entry, self.rect_corner_y_entry,
            self.rect_width_entry, self.rect_height_entry,
            self.rect_center_x_entry, self.rect_center_y_entry,
            self.rect_center_w_entry, self.rect_center_h_entry
        ]:
            entry.delete(0, tk.END)
        self._update_rectangle_params_ui()
        callbacks.update_preview_rectangle()

    def _update_rectangle_params_ui(self):
        method = self.rect_method.get()
        self.rect_two_points_frame.pack_forget()
        self.rect_corner_frame.pack_forget()
        self.rect_center_frame.pack_forget()

        if method == 'two_points':
            self.rect_two_points_frame.pack(padx=5, pady=5, fill=tk.X)
        elif method == 'corner_size':
            self.rect_corner_frame.pack(padx=5, pady=5, fill=tk.X)
        elif method == 'center_size':
            self.rect_center_frame.pack(padx=5, pady=5, fill=tk.X)

    def refresh_style_combobox_values(self, styles_dict):

        sorted_items = sorted(styles_dict.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        
        style_names = []
        self.style_ids = [] 
        
        for key, style in sorted_items:
            style_names.append(style.display_name)
            self.style_ids.append(key)
        
        self.style_combobox['values'] = style_names
        
        current_text = self.style_combobox.get()
        
        current_id = self.callbacks.state.current_style_name
        if current_id in self.style_ids:
             idx = self.style_ids.index(current_id)
             self.style_combobox.current(idx)
        elif style_names and current_text != "Разные":
             self.style_combobox.current(0)

    def refresh_dimension_style_combobox_values(self, styles_dict):

        sorted_items = sorted(styles_dict.items(), key=lambda x: x[1].display_name)
        self.dimension_style_ids = []
        names = []
        for key, style in sorted_items:
            self.dimension_style_ids.append(key)
            names.append(style.display_name)

        self.dimension_style_combobox['values'] = names
        self.dimension_context_style_combobox['values'] = names

        current_id = self.callbacks.state.current_dimension_style_name
        if current_id in self.dimension_style_ids:
            idx = self.dimension_style_ids.index(current_id)
            self.dimension_style_combobox.current(idx)
            self.dimension_context_style_combobox.current(idx)

    def refresh_dimension_line_style_combobox_values(self, styles_dict):

        sorted_items = sorted(styles_dict.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        self.dimension_line_style_ids = []
        names = []
        for key, style in sorted_items:
            self.dimension_line_style_ids.append(key)
            names.append(style.display_name)

        self.dimension_ext_style_combobox["values"] = names
        self.dimension_dim_style_combobox["values"] = names

    def set_dimension_line_style_selection(self, combobox, style_name_or_text):

        if style_name_or_text in self.dimension_line_style_ids:
            combobox.current(self.dimension_line_style_ids.index(style_name_or_text))
        else:
            combobox.set(style_name_or_text)

    def set_dimension_option_selection(self, combobox, option_ids, option_names, option_id):

        if option_id in option_ids:
            combobox.current(option_ids.index(option_id))
        else:
            combobox.set(option_id)

    def set_dimension_style_selection(self, style_name_or_text):

        if style_name_or_text in self.dimension_style_ids:
            idx = self.dimension_style_ids.index(style_name_or_text)
            self.dimension_style_combobox.current(idx)
            self.dimension_context_style_combobox.current(idx)
        else:
            self.dimension_style_combobox.set(style_name_or_text)
            self.dimension_context_style_combobox.set(style_name_or_text)

    def set_style_selection(self, style_name_or_text):

        if style_name_or_text in self.callbacks.state.line_styles:
            if style_name_or_text in self.style_ids:
                idx = self.style_ids.index(style_name_or_text)
                self.style_combobox.current(idx)
            self.update_style_preview(style_name_or_text)
        else:
            self.style_combobox.set(style_name_or_text)
            self.prop_preview_canvas.delete("all")

    def _generate_dashed_coords(self, x1, y1, x2, y2, pattern, px_ratio):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return []
        
        ux, uy = dx/length, dy/length
        scaled_pattern = [float(val) * px_ratio for val in pattern]
        
        lines = []
        current_dist = 0
        pat_idx = 0
        
        while current_dist < length:
            segment_len = scaled_pattern[pat_idx % len(scaled_pattern)]
            is_draw = (pat_idx % 2 == 0)
            draw_len = min(segment_len, length - current_dist)
            
            if is_draw:
                lines.append((x1 + ux*current_dist, y1 + uy*current_dist, 
                              x1 + ux*(current_dist+draw_len), y1 + uy*(current_dist+draw_len)))
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
        step = 5
        amplitude = 3
        freq = 0.2
        
        t = 0
        while t < length:
            offset = amplitude * math.sin(t * freq)
            points.extend([x1 + ux*t + nx*offset, y1 + uy*t + ny*offset])
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
        period = 40
        kink_len = 8
        amplitude = 5
        
        current_dist = 0
        while current_dist < length:
            dist_to_next_kink = min(length, current_dist + period)
            points.extend([x1 + ux*dist_to_next_kink, y1 + uy*dist_to_next_kink])
            current_dist = dist_to_next_kink
            
            if current_dist + kink_len <= length:
                d1 = current_dist + kink_len * 0.25
                d2 = current_dist + kink_len * 0.75
                d3 = current_dist + kink_len
                
                points.extend([
                    x1 + ux*d1 - nx*amplitude, y1 + uy*d1 - ny*amplitude,
                    x1 + ux*d2 + nx*amplitude, y1 + uy*d2 + ny*amplitude,
                    x1 + ux*d3, y1 + uy*d3
                ])
                current_dist += kink_len
            else:
                points.extend([x2, y2])
                break
        return points

    def update_style_preview(self, style_name):
        self.prop_preview_canvas.delete("all")
        style = self.callbacks.state.line_styles.get(style_name)
        if not style: return

        w = self.prop_preview_canvas.winfo_width(); w = 200 if w < 10 else w
        h = self.prop_preview_canvas.winfo_height(); cy = h / 2
        x1, y1 = 10, cy; x2, y2 = w-10, cy

        px_ratio = 3.78 
        s_px = self.callbacks.state.base_thickness_mm * px_ratio
        width = max(1, int(s_px)) if style.is_main else max(1, int(s_px / 2))

        dash_pattern = None
        if style.dash_pattern:
            d, g = style.dash_pattern
            if getattr(style, 'base_type', 'solid') == 'dash_dot_dot':
                part = g/5.0; dash_pattern = [d, part, part, part, part, part]
            elif getattr(style, 'base_type', 'solid') == 'dash_dot':
                part = g/3.0; dash_pattern = [d, part, part, part]
            elif style.name == 'dash_dot_dot':
                part = g/5.0; dash_pattern = [d, part, part, part, part, part]
            elif style.name.startswith('dash_dot_'): 
                part = g/3.0; dash_pattern = [d, part, part, part]
            else: 
                dash_pattern = [d, g]

        draw_complex = False; coords = []; smooth = False
        
        base_type = getattr(style, 'base_type', 'solid')
        
        if base_type == 'wave' or style.name == 'solid_wave': 
            coords = self._generate_wave_coords(x1, y1, x2, y2); draw_complex = True; smooth = True
        elif base_type == 'zigzag' or style.name == 'solid_zigzag': 
            coords = self._generate_zigzag_coords(x1, y1, x2, y2); draw_complex = True; smooth = False
        elif dash_pattern:
            segments = self._generate_dashed_coords(x1, y1, x2, y2, dash_pattern, px_ratio)
            for seg in segments: self.prop_preview_canvas.create_line(seg[0], seg[1], seg[2], seg[3], width=width, fill='black', capstyle=tk.ROUND)
            return
        else:
            self.prop_preview_canvas.create_line(x1, y1, x2, y2, width=width, fill='black', capstyle=tk.ROUND)
            return

        if draw_complex and len(coords) >= 4:
            self.prop_preview_canvas.create_line(*coords, width=width, fill='black', capstyle=tk.ROUND, smooth=smooth)
