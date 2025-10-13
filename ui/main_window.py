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