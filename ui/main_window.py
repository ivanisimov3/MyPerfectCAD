# ui/main_window.py

import tkinter as tk
from tkinter import ttk

class MainWindow:
    def __init__(self, root, callbacks):
        self.root = root
        root.title("MyPerfectCAD")
        root.minsize(950, 600)
        
        # Сетка: 
        # Row 0: Toolbar
        # Row 1: Canvas (растягивается)
        # Row 2: Info Panel (свойства отрезка)
        # Row 3: Status Bar (общая инфа)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # 1. ГЛАВНОЕ МЕНЮ
        self.setup_main_menu(root, callbacks)
        
        # 2. ПАНЕЛЬ ИНСТРУМЕНТОВ
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        
        self._setup_toolbar_buttons(toolbar, callbacks)

        # 3. ХОЛСТ
        self.canvas = tk.Canvas(root, borderwidth=2, relief="sunken", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        # 4. ПАНЕЛЬ НАСТРОЕК (Справа)
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=('E', 'N', 'S'), padx=5, pady=5)
        self.setup_settings_panel(settings_panel, callbacks)
        
        # 5. ИНФО-ПАНЕЛЬ (Свойства объекта)
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.setup_info_panel(info_panel)
        
        # 6. СТРОКА СОСТОЯНИЯ (Внизу)
        status_bar = ttk.Frame(root, relief="sunken", padding="2")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.setup_status_bar(status_bar)

        # 7. КОНТЕКСТНОЕ МЕНЮ
        self.create_context_menu(root, callbacks)
        
        # БИНДЫ
        self.canvas.bind("<Configure>", callbacks.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", callbacks.on_mouse_press)
        self.canvas.bind("<B2-Motion>", callbacks.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-4>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-5>", callbacks.on_mouse_wheel)
        
        # Отслеживание мыши для координат в статус-баре
        self.canvas.bind("<Motion>", callbacks.on_mouse_move_stats)
        
        # Правая кнопка мыши (Контекстное меню) - биндим на root, чтобы работало везде, 
        # но контроллер сам решит, показывать или нет (в зависимости от режима)
        self.canvas.bind("<Button-3>", callbacks.show_context_menu) 

        self.root.bind("<F11>", callbacks.toggle_fullscreen)
        self.root.bind("<Escape>", callbacks.on_escape_key)
        
        # Клавиатурные сокращения (Зум, Поворот)
        self.root.bind("<plus>", callbacks.on_zoom_in)
        self.root.bind("<equal>", callbacks.on_zoom_in)
        self.root.bind("<minus>", callbacks.on_zoom_out)
        self.root.bind("<Left>", callbacks.on_rotate_left)
        self.root.bind("<Right>", callbacks.on_rotate_right)
        self.root.bind("<Shift-Left>", callbacks.on_rotate_left)
        self.root.bind("<Shift-Right>", callbacks.on_rotate_right)

    def _setup_toolbar_buttons(self, parent, callbacks):
        ttk.Button(parent, text="Отрезок", command=callbacks.on_new_segment_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Рука", command=callbacks.on_hand_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Удалить", command=callbacks.on_delete_segment).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(parent, text="Лупа+", command=callbacks.on_zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Лупа-", command=callbacks.on_zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Показать все", command=callbacks.on_fit_to_view).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(parent, text="↶", width=3, command=callbacks.on_rotate_left).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="↷", width=3, command=callbacks.on_rotate_right).pack(side=tk.LEFT, padx=2)
        # Кнопка сброса
        ttk.Button(parent, text="Сброс", command=callbacks.on_reset_view).pack(side=tk.LEFT, padx=2)

    def setup_main_menu(self, root, callbacks):
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        # Меню "Файл" (для приличия)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Меню "Вид" (Требование задания)
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
        # Создаем лейблы для отображения информации
        self.status_coords = ttk.Label(parent, text="X: 0.00  Y: 0.00", width=20)
        self.status_coords.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        self.status_zoom = ttk.Label(parent, text="Zoom: 100%", width=15)
        self.status_zoom.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        self.status_angle = ttk.Label(parent, text="Angle: 0.0°", width=15)
        self.status_angle.pack(side=tk.LEFT, padx=5)
        
        self.status_mode = ttk.Label(parent, text="Режим: Ожидание", anchor=tk.E)
        self.status_mode.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    def create_context_menu(self, root, callbacks):
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="Рука", command=callbacks.on_hand_mode)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Показать все", command=callbacks.on_fit_to_view)
        self.context_menu.add_command(label="Сбросить вид", command=callbacks.on_reset_view)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отмена", command=lambda: None) # Просто закрыть меню

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
        # Сохраняем ссылки на лейблы в self, чтобы обращаться к ним из контроллера
        self.lbl_enter = ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод")
        self.lbl_enter.pack(side=tk.LEFT, padx=5)
        
        self.lbl_esc = ttk.Label(self.hotkey_frame, text="⎋ Esc - Отмена")
        self.lbl_esc.pack(side=tk.LEFT, padx=5)
    
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