# ui/main_window.py

'''
Создает окна, кнопки, поля ввода, меню и сам холст (Canvas). 
Он отвечает за компоновку (где какая кнопка лежит), но не за то, что происходит при нажатии (это делегируется в Callbacks).
'''

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
        root.rowconfigure(1, weight=1)

        self.setup_main_menu(root, callbacks)
        
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self._setup_toolbar_buttons(toolbar, callbacks)

        self.canvas = tk.Canvas(root, borderwidth=2, relief="sunken", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=('E', 'N', 'S'), padx=5, pady=5)
        self.setup_settings_panel(settings_panel, callbacks)
        
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.setup_info_panel(info_panel)
        
        status_bar = ttk.Frame(root, relief="sunken", padding="2")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.setup_status_bar(status_bar)

        self.create_context_menu(root, callbacks)
        
        # БИНДЫ
        self.canvas.bind("<Configure>", callbacks.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", callbacks.on_mouse_press)
        self.canvas.bind("<B2-Motion>", callbacks.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-4>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Button-5>", callbacks.on_mouse_wheel)
        self.canvas.bind("<Motion>", callbacks.on_mouse_move_stats)
        self.canvas.bind("<Button-3>", callbacks.show_context_menu) 

        self.root.bind("<F11>", callbacks.toggle_fullscreen)
        self.root.bind("<Escape>", callbacks.on_escape_key)
        
        self.root.bind("<plus>", callbacks.on_zoom_in)
        self.root.bind("<equal>", callbacks.on_zoom_in)
        self.root.bind("<minus>", callbacks.on_zoom_out)
        self.root.bind("<Left>", callbacks.on_rotate_left)
        self.root.bind("<Right>", callbacks.on_rotate_right)
        self.root.bind("<Shift-Left>", callbacks.on_rotate_left)
        self.root.bind("<Shift-Right>", callbacks.on_rotate_right)

    def _setup_toolbar_buttons(self, parent, callbacks):
        ttk.Button(parent, text="Отрезок", command=callbacks.on_new_segment_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Удалить", command=callbacks.on_delete_segment).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(parent, text="Рука", command=callbacks.on_hand_mode).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Лупа+", command=callbacks.on_zoom_in).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Лупа-", command=callbacks.on_zoom_out).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Показать все", command=callbacks.on_fit_to_view).pack(side=tk.LEFT, padx=2)
        ttk.Separator(parent, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        ttk.Button(parent, text="↶", width=3, command=callbacks.on_rotate_left).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="↷", width=3, command=callbacks.on_rotate_right).pack(side=tk.LEFT, padx=2)
        ttk.Button(parent, text="Сброс", command=callbacks.on_reset_view).pack(side=tk.LEFT, padx=2)

    def setup_main_menu(self, root, callbacks):
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
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
        self.status_mode = ttk.Label(parent, text="Режим: Ожидание", anchor=tk.E)
        self.status_mode.pack(side=tk.RIGHT, padx=5, fill=tk.X, expand=True)

    def create_context_menu(self, root, callbacks):
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="Рука", command=callbacks.on_hand_mode)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Показать все", command=callbacks.on_fit_to_view)
        self.context_menu.add_command(label="Сбросить вид", command=callbacks.on_reset_view)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отмена", command=lambda: None)

    def setup_settings_panel(self, parent, callbacks):
        style_frame = ttk.LabelFrame(parent, text="Стиль линии")
        style_frame.pack(padx=5, pady=5, fill=tk.X)
        
        # Фиксированная ширина канваса
        self.prop_preview_canvas = tk.Canvas(style_frame, width=200, height=40, bg="white", relief="sunken", borderwidth=1)
        self.prop_preview_canvas.pack(padx=5, pady=(5, 0))
        # Обновление превью при отрисовке
        self.prop_preview_canvas.bind("<Configure>", lambda e: self.update_style_preview(self.callbacks.state.current_style_name))
        
        # Список стилей
        self.style_ids = [] # Ключи
        style_names = []
        # Сортировка
        sorted_items = sorted(GOST_STYLES.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        for key, style in sorted_items:
            style_names.append(style.display_name)
            self.style_ids.append(key)

        self.style_combobox = ttk.Combobox(style_frame, values=style_names, state="readonly")
        
        # Начальное значение
        current = callbacks.state.current_style_name
        if current in self.style_ids:
            idx = self.style_ids.index(current)
            self.style_combobox.current(idx)
        elif self.style_ids:
            self.style_combobox.current(0)
            
        self.style_combobox.pack(fill=tk.X, padx=5, pady=5)
        self.style_combobox.bind("<<ComboboxSelected>>", callbacks.on_style_selected)
        
        ttk.Button(style_frame, text="Настроить стили...", command=callbacks.on_open_style_manager).pack(fill=tk.X, padx=5, pady=(0, 5))

        # --- КООРДИНАТЫ ---
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
        
        # --- ЕДИНИЦЫ УГЛА ---
        angle_frame = ttk.LabelFrame(parent, text="Единицы угла")
        angle_frame.pack(padx=5, pady=5, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=callbacks.update_preview_segment).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=callbacks.update_preview_segment).pack(anchor=tk.W)
        
        # --- СЕТКА ---
        grid_frame = ttk.LabelFrame(parent, text="Сетка")
        grid_frame.pack(padx=5, pady=5, fill=tk.X)
        self.grid_step_var = tk.StringVar(value="10")
        ttk.Label(grid_frame, text="Шаг:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(grid_frame, textvariable=self.grid_step_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(grid_frame, text="Применить", command=callbacks.on_apply_settings).pack(side=tk.LEFT, padx=5)
        
        # --- ЦВЕТА ---
        color_frame = ttk.LabelFrame(parent, text="Цвета")
        color_frame.pack(padx=5, pady=5, fill=tk.X)
        self.bg_swatch = self._create_color_chooser(color_frame, "Фон:", callbacks.on_choose_bg_color)
        self.grid_swatch = self._create_color_chooser(color_frame, "Сетка:", callbacks.on_choose_grid_color)
        self.segment_swatch = self._create_color_chooser(color_frame, "Линии:", callbacks.on_choose_segment_color)

    def setup_info_panel(self, parent):
        self.length_var = tk.StringVar(value="Длина: N/A")
        self.angle_var = tk.StringVar(value="Угол: N/A")
        self.p1_coord_var = tk.StringVar(value="P1: N/A")
        self.p2_coord_var = tk.StringVar(value="P2: N/A")
        for var in [self.length_var, self.angle_var, self.p1_coord_var, self.p2_coord_var]:
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
        kink_len = 12
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