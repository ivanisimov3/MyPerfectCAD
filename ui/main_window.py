# ui/main_window.py
# 
# Модуль отвечает за создание интерфейса приложения CAD
# Создает окна, кнопки, поля ввода, меню и холст (Canvas)
# Отвечает только за расположение элементов (layout), 
# логика обработки событий делегируется в callbacks

import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser 
import math
from logic.styles import GOST_STYLES

# Главный класс интерфейса приложения
class MainWindow:
    def __init__(self, root, callbacks):
        # root - основное окно Tkinter
        # callbacks - объект с функциями-обработчиками событий
        self.root = root
        self.callbacks = callbacks 
        
        # Установка заголовка и минимальных размеров окна
        root.title("MyPerfectCAD")
        root.minsize(950, 600)
        
        # Настройка сеточной раскладки - левая колонка с весом 1 будет растягиваться
        root.columnconfigure(0, weight=1)
        # Правая колонка: фиксированная ширина панели настроек (чтобы не "дрыгалось" окно)
        self.sidebar_width = 360
        root.columnconfigure(1, weight=0, minsize=self.sidebar_width)
        # Средняя строка с весом 1 будет занимать оставшееся пространство
        root.rowconfigure(1, weight=1)

        # Создание меню (Файл, Стили, Вид и т.д.)
        self.setup_main_menu(root, callbacks)
        
        # === ПАНЕЛЬ ИНСТРУМЕНТОВ (верхняя часть) ===
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self._setup_toolbar_buttons(toolbar, callbacks)

        # === ОСНОВНОЙ ХОЛСТ ДЛЯ РИСОВАНИЯ (слева) ===
        self.canvas = tk.Canvas(root, borderwidth=2, relief="sunken", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        # === ПАНЕЛЬ НАСТРОЕК (справа) ===
        # Делаем внешний контейнер фиксированной ширины — так вкладки/контент не смогут менять ширину окна
        self.sidebar_container = tk.Frame(root, width=self.sidebar_width)
        self.sidebar_container.grid(row=1, column=1, sticky=('N', 'S', 'E', 'W'), padx=5, pady=5)
        # Внутри контейнера используется pack(), поэтому отключаем pack-propagation,
        # иначе контейнер (и, следом, окно) будет менять ширину от контента.
        self.sidebar_container.pack_propagate(False)
        # На всякий случай также отключаем grid-propagation (если поменяем layout позже)
        self.sidebar_container.grid_propagate(False)

        settings_panel = ttk.LabelFrame(self.sidebar_container, text="Настройки", padding="5")
        settings_panel.pack(fill=tk.BOTH, expand=True)
        self.setup_settings_panel(settings_panel, callbacks)
        
        # === ИНФОРМАЦИОННАЯ ПАНЕЛЬ (снизу, под холстом) ===
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.setup_info_panel(info_panel)
        
        # === СТРОКА СОСТОЯНИЯ (самая нижняя) ===
        status_bar = ttk.Frame(root, relief="sunken", padding="2")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.setup_status_bar(status_bar)

        # Контекстное меню (ПКМ на холст)
        self.create_context_menu(root, callbacks)
        
        # === ПРИВЯЗКИ СОБЫТИЙ (key bindings) ===
        # События мыши на холсте
        self.canvas.bind("<Configure>", callbacks.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", callbacks.on_mouse_press)
        self.canvas.bind("<B2-Motion>", callbacks.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-4>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-5>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Motion>", callbacks.on_mouse_move_stats)
        self.canvas.bind("<Button-3>", callbacks.show_context_menu) 

        # События клавиатуры
        self.root.bind("<F11>", callbacks.toggle_fullscreen)
        self.root.bind("<Escape>", callbacks.on_escape_key)
        self.root.bind("<plus>", callbacks.on_zoom_in)
        self.root.bind("<equal>", callbacks.on_zoom_in)
        self.root.bind("<minus>", callbacks.on_zoom_out)
        self.root.bind("<Left>", callbacks.on_rotate_left)
        self.root.bind("<Right>", callbacks.on_rotate_right)
        self.root.bind("<Shift-Left>", callbacks.on_rotate_left)
        self.root.bind("<Shift-Right>", callbacks.on_rotate_right)

    # Создание кнопок на верхней панели инструментов
    def _setup_toolbar_buttons(self, parent, callbacks):
        def _add_menu_button(text, items):
            mb = ttk.Menubutton(parent, text=text)
            menu = tk.Menu(mb, tearoff=0)
            for label, cmd in items:
                if label in (None, "", "—"):
                    menu.add_separator()
                else:
                    menu.add_command(label=label, command=cmd)
            mb["menu"] = menu
            mb.pack(side=tk.LEFT, padx=2)
            return mb

        # === Примитивы (все 7 в одном меню) ===
        _add_menu_button("Примитивы", [
            ("Отрезок", callbacks.on_new_segment_mode),
            ("Окружность", callbacks.on_new_circle_mode),
            ("Эллипс", callbacks.on_new_ellipse_mode),
            ("Дуга", callbacks.on_new_arc_mode),
            ("Прямоугольник", callbacks.on_new_rectangle_mode),
            ("Многоугольник", callbacks.on_new_polygon_mode),
            ("Сплайн", callbacks.on_new_spline_mode),
        ])
        ttk.Button(parent, text="Del", width=5, command=callbacks.on_delete_segment).pack(side=tk.LEFT, padx=4)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        # === Навигация/вид ===
        ttk.Button(parent, text="Рука", width=6, command=callbacks.on_hand_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="+", width=3, command=callbacks.on_zoom_in).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="-", width=3, command=callbacks.on_zoom_out).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="Fit", width=4, command=callbacks.on_fit_to_view).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="↶", width=3, command=callbacks.on_rotate_left).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="↷", width=3, command=callbacks.on_rotate_right).pack(side=tk.LEFT, padx=1)
        ttk.Button(parent, text="0°", width=3, command=callbacks.on_reset_view).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)

        # === Стили (быстрый выбор) ===
        _add_menu_button("Стиль", [
            ("Основная", lambda: callbacks.on_quick_style_set('solid_main')),
            ("Тонкая", lambda: callbacks.on_quick_style_set('solid_thin')),
            ("Штриховая", lambda: callbacks.on_quick_style_set('dashed')),
            ("Осевая", lambda: callbacks.on_quick_style_set('dash_dot_thin')),
            ("—", None),
            ("Менеджер стилей…", callbacks.on_open_style_manager),
        ])

    # Создание главного меню приложения
    def setup_main_menu(self, root, callbacks):

        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Выход", command=root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Меню "Стили" - управление стилями линий
        style_menu = tk.Menu(menubar, tearoff=0)
        style_menu.add_command(label="Менеджер стилей...", command=callbacks.on_open_style_manager)
        menubar.add_cascade(label="Стили", menu=style_menu)
        
        # Меню "Вид" - навигация и масштабирование
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

    # Строка состояния внизу окна - показывает текущие координаты, масштаб и угол поворота
    def setup_status_bar(self, parent):
        # Координаты курсора (X, Y)
        self.status_coords = ttk.Label(parent, text="X: 0.00  Y: 0.00", width=20)
        self.status_coords.pack(side=tk.LEFT, padx=5)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        # Текущий масштаб
        self.status_zoom = ttk.Label(parent, text="Zoom: 100%", width=15)
        self.status_zoom.pack(side=tk.LEFT, padx=5)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=2)

        # Угол поворота вида (в градусах)
        self.status_angle = ttk.Label(parent, text="Angle: 0.0°", width=15)
        self.status_angle.pack(side=tk.LEFT, padx=5)

        # Текущий режим работы (рисование, панорама, ожидание и т.д.)
        self.status_mode = ttk.Label(parent, text="Режим: Ожидание", anchor=tk.E)
        self.status_mode.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    # Контекстное меню, которое появляется при ПКМ на холсте
    def create_context_menu(self, root, callbacks):

        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="Рука", command=callbacks.on_hand_mode)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Показать все", command=callbacks.on_fit_to_view)
        self.context_menu.add_command(label="Сбросить вид", command=callbacks.on_reset_view)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отмена", command=lambda: None)

    # Панель справа с настройками (стили, координаты, сетка, цвета и т.д.)
    def setup_settings_panel(self, parent, callbacks):

        # Инициализируем переменные, используемые в разных вкладках
        self.coord_system = tk.StringVar(value="cartesian")
        self.angle_units = tk.StringVar(value="degrees")

        # Две вкладки:
        # - "Общие" (всегда доступна)
        # - "Контекст" (текущий инструмент построения / один выбранный объект)
        self.settings_notebook = ttk.Notebook(parent)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Общие ---
        self.general_tab = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.general_tab, text="Общие")
        self._setup_general_tab(self.general_tab, callbacks)

        # --- Контекст ---
        self.context_tab = ttk.Frame(self.settings_notebook)
        self.settings_notebook.add(self.context_tab, text="Контекст")

        self.context_title_var = tk.StringVar(value="—")
        ttk.Label(self.context_tab, textvariable=self.context_title_var).pack(anchor=tk.W, padx=6, pady=(6, 4))

        self.context_hint = ttk.Label(
            self.context_tab,
            text="Выберите один объект или начните построение примитива."
        )
        self.context_hint.pack(anchor=tk.W, padx=6, pady=(0, 6))

        self.context_pages_container = ttk.Frame(self.context_tab)
        self.context_pages_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Создаем "страницы" контекста (по одной на примитив) и скрываем их до необходимости
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

        for page in self._context_pages.values():
            page.pack_forget()

        self._active_context_key = None

    def set_context_panel(self, key, title=None):
        """Показывает контекстную панель примитива (или скрывает, если key=None)."""
        # Прячем текущую
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
        self._active_context_key = key

    def _setup_general_tab(self, parent, callbacks):
        # === РАЗДЕЛ: СТИЛЬ ЛИНИИ ===
        style_frame = ttk.LabelFrame(parent, text="Стиль линии")
        style_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # Превью выбранного стиля линии (визуальное представление)
        # Размер фиксирован - 200x40 пикселей
        self.prop_preview_canvas = tk.Canvas(style_frame, width=200, height=40, bg="white", relief="sunken", borderwidth=1)
        self.prop_preview_canvas.pack(padx=5, pady=(5, 0))

        # При перерисовке холста обновляем превью текущего стиля
        self.prop_preview_canvas.bind("<Configure>", lambda e: self.update_style_preview(self.callbacks.state.current_style_name))
        
        # Выпадающий список стилей - отсортирован (встроенные стили вверху)
        self.style_ids = []
        style_names = []

        # Сортируем стили: сначала встроенные, потом пользовательские
        sorted_items = sorted(GOST_STYLES.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        for key, style in sorted_items:
            style_names.append(style.display_name)
            self.style_ids.append(key)

        # Комбобокс для выбора стиля (только для чтения - список)
        self.style_combobox = ttk.Combobox(style_frame, values=style_names, state="readonly")
        
        # Установка начального значения (текущий выбранный стиль)
        current = callbacks.state.current_style_name
        if current in self.style_ids:
            idx = self.style_ids.index(current)
            self.style_combobox.current(idx)
        elif self.style_ids:
            self.style_combobox.current(0)
        self.style_combobox.pack(fill=tk.X, padx=5, pady=5)

        # При выборе стиля вызываем callback
        self.style_combobox.bind("<<ComboboxSelected>>", callbacks.on_style_selected)


        # === РАЗДЕЛ: КОЛИЧЕСТВО ИЗЛМОВ ИЛИ ВОЛН ===
        # Скрыто по умолчанию, показывается только для определенных стилей
        self.kinks_frame = ttk.Frame(style_frame)
        self.lbl_kinks = ttk.Label(self.kinks_frame, text="Кол-во:")
        self.lbl_kinks.pack(side=tk.LEFT)

        # Поле для ввода количества
        self.kinks_var = tk.StringVar()
        self.spin_kinks = ttk.Spinbox(self.kinks_frame, from_=1, to=100, textvariable=self.kinks_var, width=5, command=callbacks.on_kinks_changed)
        self.spin_kinks.pack(side=tk.RIGHT)

        # События при изменении значения
        self.spin_kinks.bind("<Return>", callbacks.on_kinks_changed)
        self.spin_kinks.bind("<<Increment>>", lambda e: callbacks.on_kinks_changed())
        self.spin_kinks.bind("<<Decrement>>", lambda e: callbacks.on_kinks_changed())
        
        # Кнопка для открытия менеджера стилей (подробная настройка)
        ttk.Button(style_frame, text="Настроить стили...", command=callbacks.on_open_style_manager).pack(fill=tk.X, padx=5, pady=(0, 5))


        
        

        # === РАЗДЕЛ: СЕТКА ===
        grid_frame = ttk.LabelFrame(parent, text="Сетка")
        grid_frame.pack(padx=5, pady=5, fill=tk.X)

        # Шаг сетки в единицах рисунка
        self.grid_step_var = tk.StringVar(value="10")
        ttk.Label(grid_frame, text="Шаг:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(grid_frame, textvariable=self.grid_step_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(grid_frame, text="Применить", command=callbacks.on_apply_settings).pack(side=tk.LEFT, padx=5)
        

        # === РАЗДЕЛ: ЦВЕТА ===
        color_frame = ttk.LabelFrame(parent, text="Цвета")
        color_frame.pack(padx=5, pady=5, fill=tk.X)

        # Выбор цвета фона холста
        self.bg_swatch = self._create_color_chooser(color_frame, "Фон:", callbacks.on_choose_bg_color)

        # Выбор цвета сетки
        self.grid_swatch = self._create_color_chooser(color_frame, "Сетка:", callbacks.on_choose_grid_color)

        # Выбор цвета линий
        self.segment_swatch = self._create_color_chooser(color_frame, "Линии:", callbacks.on_choose_segment_color)

    def _setup_segment_tab(self, parent, callbacks):
        # === РАЗДЕЛ: КООРДИНАТЫ ОТРЕЗКОВ ===

        # ТОЧКА 1 (P1) - начало отрезка
        p1_frame = ttk.LabelFrame(parent, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p1_label1, self.p1_x_entry = self._create_coord_entry(p1_frame, "X₁:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))
        self.p1_label2, self.p1_y_entry = self._create_coord_entry(p1_frame, "Y₁:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))

        # ТОЧКА 2 (P2) - конец отрезка
        p2_frame = ttk.LabelFrame(parent, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p2_label1, self.p2_x_entry = self._create_coord_entry(p2_frame, "X₂:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))
        self.p2_label2, self.p2_y_entry = self._create_coord_entry(p2_frame, "Y₂:", lambda e: (callbacks.update_preview_segment(), callbacks.update_preview_circle()))

        # Радиокнопки для выбора системы координат второй точки
        ttk.Radiobutton(parent, text="P2: Декартова (X₂,Y₂)", variable=self.coord_system, value="cartesian", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5, pady=(5,0))
        ttk.Radiobutton(parent, text="P2: Полярная (R₂,θ₂)", variable=self.coord_system, value="polar", command=callbacks.on_coord_system_change).pack(anchor=tk.W, padx=5)

        # === РАЗДЕЛ: ЕДИНИЦЫ УГЛА ===
        angle_frame = ttk.LabelFrame(parent, text="Единицы угла")
        angle_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=lambda: (callbacks.update_preview_segment(), callbacks.update_preview_circle(), callbacks.update_preview_arc())).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=lambda: (callbacks.update_preview_segment(), callbacks.update_preview_circle(), callbacks.update_preview_arc())).pack(anchor=tk.W)

    def _setup_circle_tab(self, parent, callbacks):
        # === РАЗДЕЛ: МЕТОД СОЗДАНИЯ ОКРУЖНОСТИ ===
        circle_frame = ttk.LabelFrame(parent, text="Метод создания окружности")
        circle_frame.pack(padx=5, pady=5, fill=tk.X)

        # Переменная для выбора метода создания окружности
        self.circle_method = tk.StringVar(value="center_radius")

        # Радиокнопки для выбора метода
        ttk.Radiobutton(circle_frame, text="Центр и радиус", variable=self.circle_method, value="center_radius",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="Центр и диаметр", variable=self.circle_method, value="center_diameter",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="Две точки (диаметр)", variable=self.circle_method, value="two_points",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(circle_frame, text="3 точки на окружности", variable=self.circle_method, value="three_points",
                       command=lambda: self._on_circle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        # === РАЗДЕЛ: ПОЛЯ ВВОДА ДЛЯ ОКРУЖНОСТЕЙ ===
        self.circle_input_frame = ttk.LabelFrame(parent, text="Координаты")
        self.circle_input_frame.pack(padx=5, pady=5, fill=tk.X)

        # Поля для центра (X₁, Y₁) - используются для всех методов
        center_frame = ttk.LabelFrame(self.circle_input_frame, text="Центр")
        center_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_center_label1, self.circle_center_x_entry = self._create_coord_entry(center_frame, "X₁:", callbacks.update_preview_circle)
        self.circle_center_label2, self.circle_center_y_entry = self._create_coord_entry(center_frame, "Y₁:", callbacks.update_preview_circle)

        # Поле для радиуса/диаметра
        self.circle_param_frame = ttk.Frame(self.circle_input_frame)
        self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
        self.circle_param_label, self.circle_param_entry = self._create_coord_entry(self.circle_param_frame, "R:", callbacks.update_preview_circle)

        # Поля для второй точки (X₂, Y₂) - для методов two_points и three_points
        self.circle_p2_frame = ttk.LabelFrame(self.circle_input_frame, text="Точка 2")
        self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_p2_label1, self.circle_p2_x_entry = self._create_coord_entry(self.circle_p2_frame, "X₂:", callbacks.update_preview_circle)
        self.circle_p2_label2, self.circle_p2_y_entry = self._create_coord_entry(self.circle_p2_frame, "Y₂:", callbacks.update_preview_circle)

        # Поля для третьей точки (X₃, Y₃) - только для three_points
        self.circle_p3_frame = ttk.LabelFrame(self.circle_input_frame, text="Точка 3")
        self.circle_p3_frame.pack(padx=5, pady=5, fill=tk.X)
        self.circle_p3_label1, self.circle_p3_x_entry = self._create_coord_entry(self.circle_p3_frame, "X₃:", callbacks.update_preview_circle)
        self.circle_p3_label2, self.circle_p3_y_entry = self._create_coord_entry(self.circle_p3_frame, "Y₃:", callbacks.update_preview_circle)

        # По умолчанию показываем только центр
        self.circle_param_frame.pack_forget()
        self.circle_p2_frame.pack_forget()
        self.circle_p3_frame.pack_forget()

        # Обновляем интерфейс для текущего метода
        self._update_circle_params_ui()

    def _setup_arc_tab(self, parent, callbacks):
        # Переменная метода построения
        self.arc_method = tk.StringVar(value="three_points")

        method_frame = ttk.LabelFrame(parent, text="Метод создания дуги")
        method_frame.pack(padx=5, pady=5, fill=tk.X)

        ttk.Radiobutton(method_frame, text="Три точки", variable=self.arc_method, value="three_points",
                        command=lambda: self._on_arc_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Центр, углы", variable=self.arc_method, value="center_angles",
                        command=lambda: self._on_arc_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        # Блок ввода для метода три точки
        self.arc_three_points_frame = ttk.LabelFrame(parent, text="Точки дуги")
        self.arc_three_points_frame.pack(padx=5, pady=5, fill=tk.X)
        self.arc_p1_label1, self.arc_p1_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₁:", callbacks.update_preview_arc)
        self.arc_p1_label2, self.arc_p1_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₁:", callbacks.update_preview_arc)
        self.arc_p2_label1, self.arc_p2_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₂:", callbacks.update_preview_arc)
        self.arc_p2_label2, self.arc_p2_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₂:", callbacks.update_preview_arc)
        self.arc_p3_label1, self.arc_p3_x_entry = self._create_coord_entry(self.arc_three_points_frame, "X₃:", callbacks.update_preview_arc)
        self.arc_p3_label2, self.arc_p3_y_entry = self._create_coord_entry(self.arc_three_points_frame, "Y₃:", callbacks.update_preview_arc)

        # Блок ввода для метода центр+углы
        self.arc_center_frame = ttk.LabelFrame(parent, text="Центр")
        self.arc_center_x_label, self.arc_center_x_entry = self._create_coord_entry(self.arc_center_frame, "Xc:", callbacks.update_preview_arc)
        self.arc_center_y_label, self.arc_center_y_entry = self._create_coord_entry(self.arc_center_frame, "Yc:", callbacks.update_preview_arc)

        self.arc_radius_frame = ttk.Frame(parent)
        self.arc_radius_label, self.arc_radius_entry = self._create_coord_entry(self.arc_radius_frame, "R:", callbacks.update_preview_arc)

        self.arc_angles_frame = ttk.LabelFrame(parent, text="Углы")
        self.arc_start_label, self.arc_start_angle_entry = self._create_coord_entry(self.arc_angles_frame, "θ₁:", callbacks.update_preview_arc)
        self.arc_end_label, self.arc_end_angle_entry = self._create_coord_entry(self.arc_angles_frame, "θ₂:", callbacks.update_preview_arc)

        # Изначально показываем три точки
        self._update_arc_params_ui()

    def _setup_rectangle_tab(self, parent, callbacks):
        # Переменная метода построения
        self.rect_method = tk.StringVar(value="two_points")

        method_frame = ttk.LabelFrame(parent, text="Метод создания")
        method_frame.pack(padx=5, pady=5, fill=tk.X)

        ttk.Radiobutton(method_frame, text="Две точки", variable=self.rect_method, value="two_points",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Точка, ширина/высота", variable=self.rect_method, value="corner_size",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(method_frame, text="Центр, ширина/высота", variable=self.rect_method, value="center_size",
                        command=lambda: self._on_rectangle_method_change(callbacks)).pack(anchor=tk.W, padx=5, pady=2)

        # Блок для метода "две точки"
        self.rect_two_points_frame = ttk.LabelFrame(parent, text="Точки")
        self.rect_p1_label1, self.rect_p1_x_entry = self._create_coord_entry(self.rect_two_points_frame, "X₁:", callbacks.update_preview_rectangle)
        self.rect_p1_label2, self.rect_p1_y_entry = self._create_coord_entry(self.rect_two_points_frame, "Y₁:", callbacks.update_preview_rectangle)
        self.rect_p2_label1, self.rect_p2_x_entry = self._create_coord_entry(self.rect_two_points_frame, "X₂:", callbacks.update_preview_rectangle)
        self.rect_p2_label2, self.rect_p2_y_entry = self._create_coord_entry(self.rect_two_points_frame, "Y₂:", callbacks.update_preview_rectangle)

        # Блок для метода "угол + размеры"
        self.rect_corner_frame = ttk.LabelFrame(parent, text="Вершина + размеры")
        self.rect_corner_label1, self.rect_corner_x_entry = self._create_coord_entry(self.rect_corner_frame, "X:", callbacks.update_preview_rectangle)
        self.rect_corner_label2, self.rect_corner_y_entry = self._create_coord_entry(self.rect_corner_frame, "Y:", callbacks.update_preview_rectangle)
        self.rect_width_label, self.rect_width_entry = self._create_coord_entry(self.rect_corner_frame, "W:", callbacks.update_preview_rectangle)
        self.rect_height_label, self.rect_height_entry = self._create_coord_entry(self.rect_corner_frame, "H:", callbacks.update_preview_rectangle)

        # Блок для метода "центр + размеры"
        self.rect_center_frame = ttk.LabelFrame(parent, text="Центр + размеры")
        self.rect_center_label1, self.rect_center_x_entry = self._create_coord_entry(self.rect_center_frame, "Xc:", callbacks.update_preview_rectangle)
        self.rect_center_label2, self.rect_center_y_entry = self._create_coord_entry(self.rect_center_frame, "Yc:", callbacks.update_preview_rectangle)
        self.rect_center_w_label, self.rect_center_w_entry = self._create_coord_entry(self.rect_center_frame, "W:", callbacks.update_preview_rectangle)
        self.rect_center_h_label, self.rect_center_h_entry = self._create_coord_entry(self.rect_center_frame, "H:", callbacks.update_preview_rectangle)

        # Блок настроек углов
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

        # Изначально показываем "две точки"
        self._update_rectangle_params_ui()

    def _setup_ellipse_tab(self, parent, callbacks):
        # Пока поддерживается один метод: центр и две оси
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
        # Способ: центр и радиус описанной/вписанной окружности
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

        manual_frame = ttk.LabelFrame(parent, text="Добавить вручную")
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        row = ttk.Frame(manual_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(row, text="X:").pack(side=tk.LEFT)
        self.spline_point_x_entry = ttk.Entry(row, width=10)
        self.spline_point_x_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(row, text="Y:").pack(side=tk.LEFT)
        self.spline_point_y_entry = ttk.Entry(row, width=10)
        self.spline_point_y_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(manual_frame, text="Добавить точку", command=callbacks.on_add_spline_point_manual).pack(fill=tk.X, padx=5, pady=(2, 0))

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Удалить последнюю", command=callbacks.on_remove_last_spline_point).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Очистить", command=callbacks.on_clear_spline_points).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="Завершить (Enter)", command=callbacks.finalize_spline).pack(fill=tk.X, pady=2)

        ttk.Label(parent, text="ЛКМ на холсте добавляет точку.\nПКМ убирает последнюю. Enter завершает.").pack(anchor=tk.W, padx=8, pady=4)

    # Информационная панель - показывает параметры текущего отрезка в реальном времени
    def setup_info_panel(self, parent):

        # Длина отрезка
        self.length_var = tk.StringVar(value="Длина: N/A")

        # Угол отрезка (в градусах или радианах, в зависимости от выбора)
        self.angle_var = tk.StringVar(value="Угол: N/A")

        # Координаты первой точки
        self.p1_coord_var = tk.StringVar(value="P1: N/A")

        # Координаты второй точки
        self.p2_coord_var = tk.StringVar(value="P2: N/A")

        # Координаты третьей точки
        self.p3_coord_var = tk.StringVar(value="P3: N/A")

        # Создание меток с этими переменными
        for var in [self.length_var, self.angle_var, self.p1_coord_var, self.p2_coord_var, self.p3_coord_var]:
            ttk.Label(parent, textvariable=var).pack(side=tk.LEFT, padx=10, pady=2)


         # === ГОРЯЧИЕ КЛАВИШИ ===
        self.hotkey_frame = ttk.Frame(parent)

        # Enter - подтвердить ввод
        self.lbl_enter = ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод")
        self.lbl_enter.pack(side=tk.LEFT, padx=5)
        
        # Escape - отмена
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
        """Обработчик изменения метода создания окружности."""
        method = self.circle_method.get()
        callbacks.state.circle_creation_method = method

        # Очищаем поля при смене метода
        self.circle_param_entry.delete(0, tk.END)
        self.circle_p2_x_entry.delete(0, tk.END)
        self.circle_p2_y_entry.delete(0, tk.END)
        self.circle_p3_x_entry.delete(0, tk.END)
        self.circle_p3_y_entry.delete(0, tk.END)

        self._update_circle_params_ui()
        callbacks.update_preview_circle()

    def _update_circle_params_ui(self):
        """Обновляет интерфейс параметров окружности в зависимости от метода."""
        method = self.circle_method.get()

        if method == 'center_radius':
            # Показываем центр и радиус
            self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
            self.circle_param_label.config(text="R:")
            self.circle_p2_frame.pack_forget()
            self.circle_p3_frame.pack_forget()
        elif method == 'center_diameter':
            # Показываем центр и диаметр
            self.circle_param_frame.pack(fill=tk.X, padx=5, pady=2)
            self.circle_param_label.config(text="D:")
            self.circle_p2_frame.pack_forget()
            self.circle_p3_frame.pack_forget()
        elif method == 'two_points':
            # Показываем центр и вторую точку
            self.circle_param_frame.pack_forget()
            self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
            self.circle_p3_frame.pack_forget()
        elif method == 'three_points':
            # Показываем центр, вторую и третью точки
            self.circle_param_frame.pack_forget()
            self.circle_p2_frame.pack(padx=5, pady=5, fill=tk.X)
            self.circle_p3_frame.pack(padx=5, pady=5, fill=tk.X)

    def _on_arc_method_change(self, callbacks):
        """Обработчик смены метода построения дуги."""
        method = self.arc_method.get()
        callbacks.state.arc_creation_method = method

        # Очищаем поля
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
        """Показывает нужные поля в зависимости от метода построения дуги."""
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
        # Очищаем все поля
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


    # --- ОБНОВЛЕНИЕ ИНТЕРФЕЙСА ---

    def refresh_style_combobox_values(self, styles_dict):
        """Обновляет список стилей в выпадающем меню."""
        sorted_items = sorted(styles_dict.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        
        style_names = []
        self.style_ids = [] 
        
        for key, style in sorted_items:
            style_names.append(style.display_name)
            self.style_ids.append(key)
        
        self.style_combobox['values'] = style_names
        
        # Восстанавливаем выбор (или сбрасываем)
        current_text = self.style_combobox.get()
        
        # Пробуем найти текущий стиль по тексту или по ID
        current_id = self.callbacks.state.current_style_name
        if current_id in self.style_ids:
             idx = self.style_ids.index(current_id)
             self.style_combobox.current(idx)
        elif style_names and current_text != "Разные":
             self.style_combobox.current(0)

    def set_style_selection(self, style_name_or_text):
        """Устанавливает текст в выпадающем списке и обновляет превью."""
        # Если передан ID стиля
        if style_name_or_text in self.callbacks.state.line_styles:
            if style_name_or_text in self.style_ids:
                idx = self.style_ids.index(style_name_or_text)
                self.style_combobox.current(idx)
            self.update_style_preview(style_name_or_text)
        else:
            # Если передано "Разные"
            self.style_combobox.set(style_name_or_text)
            self.prop_preview_canvas.delete("all")

    # --- ГЕНЕРАТОРЫ (Те же, что и везде) ---
    def _generate_dashed_coords(self, x1, y1, x2, y2, pattern, px_ratio):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return []
        
        # ТЕПЕРЬ ЭТО ОТДЕЛЬНЫЕ СТРОКИ
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
        
        # ТЕПЕРЬ ЭТО ОТДЕЛЬНЫЕ СТРОКИ
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
        
        # ТЕПЕРЬ ЭТО ОТДЕЛЬНЫЕ СТРОКИ
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
            # Дублирующая проверка (для надежности)
            # Сначала проверяем base_type (новое)
            if getattr(style, 'base_type', 'solid') == 'dash_dot_dot':
                part = g/5.0; dash_pattern = [d, part, part, part, part, part]
            elif getattr(style, 'base_type', 'solid') == 'dash_dot':
                part = g/3.0; dash_pattern = [d, part, part, part]
            # Если base_type не помог, проверяем имя (старое)
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