# ui/main_window.py

import tkinter as tk
from tkinter import ttk

class MainWindow:
    def __init__(self, root, callbacks):
        self.root = root
        root.title("MyPerfectCAD")
        root.minsize(950, 600)
        
        # Приоритет при изменении размеров приложения
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # ПАНЕЛИ ИНТЕРФЕЙСА
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)

        self.canvas = tk.Canvas(root, borderwidth=2, relief="sunken")
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=('E', 'N', 'S'), padx=5, pady=5)
        
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)

        # Кнопки на панели инструментов
        ttk.Button(toolbar, text="Отрезок", command=callbacks.on_new_segment_mode).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(toolbar, text="Удалить", command=callbacks.on_delete_segment).pack(side=tk.LEFT, padx=5, pady=2)
        
        # Настраиваемые виджеты
        self.setup_settings_panel(settings_panel, callbacks)
        self.setup_info_panel(info_panel)
        
        # Передаем вызовы соответствующим обработчикам в callbacks
        self.canvas.bind("<Configure>", callbacks.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", callbacks.on_mouse_press)
        self.canvas.bind("<B2-Motion>", callbacks.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-4>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-5>", callbacks.on_mouse_wheel)
        self.root.bind("<F11>", callbacks.toggle_fullscreen)
        self.root.bind("<Escape>", callbacks.on_escape_key)

    # Создает все элементы на панели настроек
    def setup_settings_panel(self, parent, callbacks):
        self.coord_system = tk.StringVar(value="cartesian")
        self.angle_units = tk.StringVar(value="degrees")
        
        p1_frame = ttk.LabelFrame(parent, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        _, self.p1_x_entry = self._create_coord_entry(p1_frame, "X₁:", callbacks.update_preview_segment)
        _, self.p1_y_entry = self._create_coord_entry(p1_frame, "Y₁:", callbacks.update_preview_segment)
        
        p2_frame = ttk.LabelFrame(parent, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p2_label1, self.p2_x_entry = self._create_coord_entry(p2_frame, "X₂:", callbacks.update_preview_segment)
        self.p2_label2, self.p2_y_entry = self._create_coord_entry(p2_frame, "Y₂:", callbacks.update_preview_segment)
        
        ttk.Radiobutton(parent, text="P2: Декартова (X₂, Y₂)", variable=self.coord_system, value="cartesian", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5, pady=(5,0))
        ttk.Radiobutton(parent, text="P2: Полярная (R₂, θ₂)", variable=self.coord_system, value="polar", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5)
        
        angle_frame = ttk.LabelFrame(parent, text="Единицы угла")
        angle_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=callbacks.update_preview_segment).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=callbacks.update_preview_segment).pack(anchor=tk.W)
        
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
        self.segment_swatch = self._create_color_chooser(color_frame, "Отрезок:", callbacks.on_choose_segment_color)

    # Создает все элементы на информационной панели
    def setup_info_panel(self, parent):
        self.length_var = tk.StringVar(value="Длина: N/A")
        self.angle_var = tk.StringVar(value="Угол: N/A")
        self.p1_coord_var = tk.StringVar(value="P1: N/A")
        self.p2_coord_var = tk.StringVar(value="P2: N/A")
        for var in [self.length_var, self.angle_var, self.p1_coord_var, self.p2_coord_var]:
            ttk.Label(parent, textvariable=var).pack(side=tk.LEFT, padx=10, pady=2)
        self.hotkey_frame = ttk.Frame(parent)
        ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод").pack(side=tk.LEFT, padx=5)
        ttk.Label(self.hotkey_frame, text="⎋ Esc - Отмена").pack(side=tk.LEFT, padx=5)
    
    # Вспомогательный метод для создания пары Label + Entry
    def _create_coord_entry(self, parent, label_text, key_release_callback):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        label = ttk.Label(frame, text=label_text, width=4)
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<KeyRelease>", key_release_callback)
        return label, entry
    
    # Вспомогательный метод для создания блока выбора цвета
    def _create_color_chooser(self, parent, text, command):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=text).pack(side=tk.LEFT, padx=5)
        swatch = tk.Label(frame, width=4, relief='sunken', borderwidth=1)
        swatch.pack(side=tk.RIGHT, padx=5)
        swatch.bind("<Button-1>", lambda e: command())
        return swatch

    # # Стало:
    # def on_mouse_wheel(self, event):
    #     world_before_zoom_x, world_before_zoom_y = self.screen_to_world(event.x, event.y)
    #     if hasattr(event, 'delta') and event.delta != 0: # Для Windows и macOS
    #         zoom_factor = 1 / 1.2 if event.delta > 0 else 1.2 # Вверх -> отдалить, Вниз -> приблизить
    #     elif event.num == 4: # Для Linux
    #         zoom_factor = 1 / 1.2 # Вверх -> отдалить
    #     elif event.num == 5: # Для Linux
    #         zoom_factor = 1.2 # Вниз -> приблизить
    #     else: return
        
    #     self.zoom *= zoom_factor
    #     self.zoom = max(0.1, min(self.zoom, 100))
    #     screen_after_zoom_x, screen_after_zoom_y = self.world_to_screen(world_before_zoom_x, world_before_zoom_y)
    #     pan_dx = event.x - screen_after_zoom_x
    #     pan_dy = event.y - screen_after_zoom_y
    #     self.pan_x += pan_dx; self.pan_y += pan_dy
    #     self.redraw_all()
    
    # def update_info_panel(self):
    #     self.active_p1, self.active_p2 = None, None
    #     length, angle_rad = None, None
    #     if self.app_state == 'CREATING_SEGMENT':
    #         try: self.active_p1 = Point(float(self.p1_x_entry.get()), float(self.p1_y_entry.get()))
    #         except (ValueError, tk.TclError): pass
    #         try:
    #             p1_for_p2, self.active_p2 = self._create_points_from_entries()
    #             if self.active_p1 is None: self.active_p1 = p1_for_p2
    #         except (ValueError, tk.TclError): pass
    #     elif self.segments:
    #         # Не показываем точки последнего отрезка в режиме IDLE
    #         pass
    #     p1, p2 = self.active_p1, self.active_p2
    #     if p1: self.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
    #     else: self.p1_coord_var.set("P1: N/A")
    #     if p2:
    #         if self.coord_system.get() == 'polar':
    #             r, theta = p2.get_polar_coords()
    #             unit_sym = "°" if self.angle_units.get() == 'degrees' else " rad"
    #             if self.angle_units.get() == 'degrees': theta = math.degrees(theta)
    #             self.p2_coord_var.set(f"P2(r={r:.2f}, θ={theta:.2f}{unit_sym})")
    #         else: self.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
    #     else: self.p2_coord_var.set("P2: N/A")
    #     if p1 and p2: length, angle_rad = Segment(p1, p2).length, Segment(p1, p2).angle
    #     if length is not None: self.length_var.set(f"Длина: {length:.2f}")
    #     else: self.length_var.set("Длина: N/A")
    #     if angle_rad is not None:
    #         if self.angle_units.get() == 'degrees': val, sym = math.degrees(angle_rad), "°"
    #         else: val, sym = angle_rad, " rad"
    #         self.angle_var.set(f"Угол: {val:.2f}{sym}")
    #     else: self.angle_var.set("Угол: N/A")

    # def draw_grid_and_axes(self):
    #     width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
    #     if width < 2 or height < 2: return
    #     world_tl_x, world_tl_y = self.screen_to_world(0, 0)
    #     world_br_x, world_br_y = self.screen_to_world(width, height)
    #     start_x = math.ceil(world_tl_x / self.grid_step) * self.grid_step
    #     for wx in range(start_x, int(world_br_x), self.grid_step):
    #         sx, _ = self.world_to_screen(wx, 0)
    #         self.canvas.create_line(sx, 0, sx, height, fill='black' if wx==0 else self.grid_color, width=2 if wx==0 else 1)
    #     start_y = math.ceil(world_br_y / self.grid_step) * self.grid_step
    #     for wy in range(start_y, int(world_tl_y), self.grid_step):
    #         _, sy = self.world_to_screen(0, wy)
    #         self.canvas.create_line(0, sy, width, sy, fill='black' if wy==0 else self.grid_color, width=2 if wy==0 else 1)
    #     x_axis_pos_y = self.world_to_screen(0,0)[1]
    #     if 0 < x_axis_pos_y < height: self.canvas.create_text(width - 10, x_axis_pos_y - 10, text="X", font=("Arial", 10), anchor='se', fill='gray')
    #     y_axis_pos_x = self.world_to_screen(0,0)[0]
    #     if 0 < y_axis_pos_x < width: self.canvas.create_text(y_axis_pos_x + 10, 10, text="Y", font=("Arial", 10), anchor='nw', fill='gray')