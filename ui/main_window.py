# ui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import math
from logic.geometry import Point, Segment

class MainWindow:
    def __init__(self, root):
        self.root = root
        root.title("MyPerfectCAD: ЛР №1")
        root.minsize(950, 600)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # === Состояние приложения и цвета ===
        self.app_state = 'IDLE'
        self.segments = []
        self.preview_segment = None
        self.bg_color, self.grid_color, self.segment_color = 'white', '#e0e0e0', 'red'

        # === Панель инструментов ===
        toolbar = ttk.LabelFrame(root, text="Инструменты", padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(toolbar, text="Отрезок", command=self.on_new_segment_mode).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(toolbar, text="Удалить", command=self.on_delete_segment).pack(side=tk.LEFT, padx=5, pady=2)

        # === Рабочая область ===
        self.canvas = tk.Canvas(root, bg=self.bg_color, borderwidth=2, relief="sunken")
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        # === Панель настроек ===
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=('E', 'N', 'S'), padx=5, pady=5)
        
        self.coord_system = tk.StringVar(value="cartesian")
        self.angle_units = tk.StringVar(value="degrees")

        # --- Координаты ---
        p1_frame = ttk.LabelFrame(settings_panel, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        _, self.p1_x_entry = self.create_coord_entry(p1_frame, "X₁:")
        _, self.p1_y_entry = self.create_coord_entry(p1_frame, "Y₁:")
        
        p2_frame = ttk.LabelFrame(settings_panel, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        # Сохраняем Label'ы для P2, чтобы менять их текст
        self.p2_label1, self.p2_x_entry = self.create_coord_entry(p2_frame, "X₂:")
        self.p2_label2, self.p2_y_entry = self.create_coord_entry(p2_frame, "Y₂:")
        
        # --- Переключатели систем координат ---
        ttk.Radiobutton(settings_panel, text="P2: Декартова (X₂, Y₂)", variable=self.coord_system, value="cartesian", command=self.on_coord_system_change).pack(anchor=tk.W)
        ttk.Radiobutton(settings_panel, text="P2: Полярная (R₂, θ₂)", variable=self.coord_system, value="polar", command=self.on_coord_system_change).pack(anchor=tk.W)
        
        # --- Переключатели единиц угла ---
        angle_frame = ttk.LabelFrame(settings_panel, text="Единицы угла")
        angle_frame.pack(padx=5, pady=10, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=self.redraw_all).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=self.redraw_all).pack(anchor=tk.W)

        # --- Настройка сетки ---
        grid_frame = ttk.LabelFrame(settings_panel, text="Сетка")
        grid_frame.pack(padx=5, pady=10, fill=tk.X)
        self.grid_step_var = tk.StringVar(value="10")
        ttk.Label(grid_frame, text="Шаг:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(grid_frame, textvariable=self.grid_step_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(grid_frame, text="Применить", command=self.on_apply_settings).pack(side=tk.LEFT, padx=5)

        # --- Настройки цвета ---
        color_frame = ttk.LabelFrame(settings_panel, text="Цвета")
        color_frame.pack(padx=5, pady=10, fill=tk.X)
        self.bg_swatch = self.create_color_chooser(color_frame, "Фон:", self.bg_color, self.on_choose_bg_color)
        self.grid_swatch = self.create_color_chooser(color_frame, "Сетка:", self.grid_color, self.on_choose_grid_color)
        self.segment_swatch = self.create_color_chooser(color_frame, "Отрезок:", self.segment_color, self.on_choose_segment_color)
        
        # === Информационная панель ===
        info_panel = ttk.LabelFrame(root, text="Информация", padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.length_var = tk.StringVar(value="Длина: N/A")
        self.angle_var = tk.StringVar(value="Угол: N/A")
        self.p1_coord_var = tk.StringVar(value="P1: N/A")
        self.p2_coord_var = tk.StringVar(value="P2: N/A")
        for var in [self.length_var, self.angle_var, self.p1_coord_var, self.p2_coord_var]:
            ttk.Label(info_panel, textvariable=var).pack(side=tk.LEFT, padx=10, pady=2)
        self.hotkey_frame = ttk.Frame(info_panel)
        ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод").pack(side=tk.LEFT, padx=5)
        ttk.Label(self.hotkey_frame, text="⎋ Esc - Отмена").pack(side=tk.LEFT, padx=5)
        
        # === Логика камеры и привязки событий ===
        self.pan_x, self.pan_y, self.zoom = 0, 0, 5.0
        self.grid_step = 10
        self._drag_start_x, self._drag_start_y = 0, 0
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", self.on_mouse_press)
        self.canvas.bind("<B2-Motion>", self.on_mouse_drag)
        self.set_app_state('IDLE')

    # --- Методы создания виджетов ---
    def create_coord_entry(self, parent, label_text):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        label = ttk.Label(frame, text=label_text, width=4)
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<KeyRelease>", self.update_preview_segment)
        return label, entry
        
    def create_color_chooser(self, parent, text, initial_color, command):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=text).pack(side=tk.LEFT, padx=5)
        swatch = tk.Label(frame, background=initial_color, width=4, relief='sunken', borderwidth=1)
        swatch.pack(side=tk.RIGHT, padx=5)
        swatch.bind("<Button-1>", lambda e: command())
        return swatch

    # --- Обработчики и логика ---
    def on_apply_settings(self):
        try:
            new_step = int(self.grid_step_var.get())
            if new_step <= 0: raise ValueError
            self.grid_step = new_step
            self.redraw_all()
        except ValueError:
            messagebox.showerror("Ошибка", "Шаг сетки должен быть целым положительным числом.")

    def set_app_state(self, state):
        self.app_state = state
        is_creating = (state == 'CREATING_SEGMENT')
        entry_state = 'normal' if is_creating else 'disabled'
        
        for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
            entry.config(state=entry_state)
            
        if is_creating:
            self.root.bind("<Return>", self.finalize_segment)
            self.root.bind("<Escape>", self.cancel_creation)
            self.hotkey_frame.pack(side=tk.RIGHT, padx=5)
        else:
            for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
                entry.delete(0, tk.END)
            self.root.unbind("<Return>")
            self.root.unbind("<Escape>")
            self.hotkey_frame.pack_forget()
            self.preview_segment = None
            self.redraw_all()
            
    def on_new_segment_mode(self, event=None):
        self.set_app_state('CREATING_SEGMENT')
        self.p1_x_entry.focus_set()
        
    def update_preview_segment(self, event=None):
        try:
            p1, p2 = self._create_points_from_entries()
            self.preview_segment = Segment(p1, p2)
        except (ValueError, tk.TclError):
            self.preview_segment = None
        self.redraw_all()

    def finalize_segment(self, event=None):
        if self.preview_segment:
            self.segments.append(self.preview_segment)
            self.set_app_state('IDLE')

    def cancel_creation(self, event=None): self.set_app_state('IDLE')
    def on_delete_segment(self, event=None):
        if self.segments:
            self.segments.pop()
            self.redraw_all()

    def on_choose_bg_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет фона", initialcolor=self.bg_color)
        if color_hex:
            self.bg_color = color_hex
            self.canvas.config(bg=self.bg_color)
            self.bg_swatch.config(background=self.bg_color)

    def on_choose_grid_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет сетки", initialcolor=self.grid_color)
        if color_hex:
            self.grid_color = color_hex
            self.grid_swatch.config(background=self.grid_color)
            self.redraw_all()
            
    def on_choose_segment_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет отрезков", initialcolor=self.segment_color)
        if color_hex:
            self.segment_color = color_hex
            self.segment_swatch.config(background=self.segment_color)
            self.redraw_all()

    def on_coord_system_change(self):
        new_system = self.coord_system.get()
        # Меняем подписи у полей ввода P2
        if new_system == 'polar':
            self.p2_label1.config(text="R₂:")
            self.p2_label2.config(text="θ₂:")
        else:
            self.p2_label1.config(text="X₂:")
            self.p2_label2.config(text="Y₂:")
        
        try:
            # P1 всегда читается как декартова
            p1 = Point(float(self.p1_x_entry.get()), float(self.p1_y_entry.get()))
            # P2 читается в старой системе
            val1 = float(self.p2_x_entry.get())
            val2 = float(self.p2_y_entry.get())
            p2 = Point()
            if self.coord_system.get() == 'cartesian': # Если новая - декартова, значит старая - полярная
                angle = val2
                if self.angle_units.get() == 'degrees': angle = math.radians(angle)
                p2.set_from_polar(val1, angle)
            else: # Если новая - полярная, значит старая - декартова
                p2 = Point(val1, val2)
        except (ValueError, tk.TclError): return # Не конвертируем, если поля пустые/некорректные

        # Обновляем значения полей P2 в новой системе
        self._update_p2_entries(p2)

    # --- Вспомогательные методы ---
    def _create_points_from_entries(self):
        p1 = Point(float(self.p1_x_entry.get()), float(self.p1_y_entry.get()))
        p2 = Point()
        val1 = float(self.p2_x_entry.get())
        val2 = float(self.p2_y_entry.get())
        if self.coord_system.get() == 'cartesian':
            p2 = Point(val1, val2)
        else:
            angle = val2
            if self.angle_units.get() == 'degrees': angle = math.radians(angle)
            p2.set_from_polar(val1, angle)
        return p1, p2

    def _update_p2_entries(self, p2_point):
        """Обновляет только поля для P2."""
        entries = [self.p2_x_entry, self.p2_y_entry]
        is_polar = (self.coord_system.get() == 'polar')
        
        if is_polar:
            r, theta = p2_point.get_polar_coords()
            if self.angle_units.get() == 'degrees': theta = math.degrees(theta)
            values = [r, theta]
        else:
            values = [p2_point.x, p2_point.y]

        for entry, value in zip(entries, values):
            entry.config(state='normal')
            entry.delete(0, tk.END)
            entry.insert(0, f"{value:.2f}")
            if self.app_state == 'IDLE': entry.config(state='disabled')

    # --- Логика отрисовки и информации ---
    def redraw_all(self):
        self.canvas.delete("all")
        self.draw_grid_and_axes()
        active_segment = self.preview_segment if self.preview_segment else self.segments[-1] if self.segments else None
        self.update_info_panel(active_segment)
        for segment in self.segments:
            self.draw_segment(segment, color=self.segment_color, width=4) # Увеличена толщина
        if self.preview_segment:
            self.draw_segment(self.preview_segment, color='blue', width=2)
    
    def update_info_panel(self, segment):
        if segment is None:
            self.length_var.set("Длина: N/A"); self.angle_var.set("Угол: N/A")
            self.p1_coord_var.set("P1: N/A"); self.p2_coord_var.set("P2: N/A")
            return
            
        # Обновляем инфо о P1 (всегда декартова)
        self.p1_coord_var.set(f"P1({segment.p1.x:.2f}, {segment.p1.y:.2f})")
        
        # Обновляем инфо о P2 (в зависимости от выбранной системы)
        if self.coord_system.get() == 'polar':
            r, theta = segment.p2.get_polar_coords()
            unit = self.angle_units.get()
            angle_unit_symbol = "°" if unit == 'degrees' else " rad"
            if unit == 'degrees': theta = math.degrees(theta)
            self.p2_coord_var.set(f"P2(r={r:.2f}, θ={theta:.2f}{angle_unit_symbol})")
        else:
            self.p2_coord_var.set(f"P2({segment.p2.x:.2f}, {segment.p2.y:.2f})")
        
        length = segment.length
        angle_rad = segment.angle
        if self.angle_units.get() == 'degrees':
            angle_val = math.degrees(angle_rad)
            unit_symbol = "°"
        else:
            angle_val = angle_rad
            unit_symbol = " rad"
        self.length_var.set(f"Длина: {length:.2f}")
        self.angle_var.set(f"Угол: {angle_val:.2f}{unit_symbol}")

    def draw_grid_and_axes(self):
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 2 or height < 2: return
        world_tl_x, world_tl_y = self.screen_to_world(0, 0)
        world_br_x, world_br_y = self.screen_to_world(width, height)
        start_x = math.ceil(world_tl_x / self.grid_step) * self.grid_step
        for wx in range(start_x, int(world_br_x), self.grid_step):
            sx, _ = self.world_to_screen(wx, 0)
            self.canvas.create_line(sx, 0, sx, height, fill='black' if wx==0 else self.grid_color, width=2 if wx==0 else 1)
        start_y = math.ceil(world_br_y / self.grid_step) * self.grid_step
        for wy in range(start_y, int(world_tl_y), self.grid_step):
            _, sy = self.world_to_screen(0, wy)
            self.canvas.create_line(0, sy, width, sy, fill='black' if wy==0 else self.grid_color, width=2 if wy==0 else 1)
        
        # Отрисовка подписей осей X и Y
        x_axis_pos_y = self.world_to_screen(0,0)[1]
        if 0 < x_axis_pos_y < height:
             self.canvas.create_text(width - 10, x_axis_pos_y + 10, text="X", font=("Arial", 10), anchor='se')
        y_axis_pos_x = self.world_to_screen(0,0)[0]
        if 0 < y_axis_pos_x < width:
            self.canvas.create_text(y_axis_pos_x + 10, 10, text="Y", font=("Arial", 10), anchor='nw')

    def draw_segment(self, segment, color, width):
        sx1, sy1 = self.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.world_to_screen(segment.p2.x, segment.p2.y)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=width)

    def world_to_screen(self, world_x, world_y):
        center_x = self.canvas.winfo_width() / 2; center_y = self.canvas.winfo_height() / 2
        return (center_x + self.pan_x + (world_x * self.zoom), center_y + self.pan_y - (world_y * self.zoom))

    def screen_to_world(self, screen_x, screen_y):
        center_x = self.canvas.winfo_width() / 2; center_y = self.canvas.winfo_height() / 2
        return ((screen_x - center_x - self.pan_x) / self.zoom, -(screen_y - center_y - self.pan_y) / self.zoom)

    def on_canvas_resize(self, event): self.redraw_all()
    def on_mouse_press(self, event): self._drag_start_x, self._drag_start_y = event.x, event.y
    def on_mouse_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.pan_x += dx; self.pan_y += dy
        self._drag_start_x, self._drag_start_y = event.x, event.y
        self.redraw_all()