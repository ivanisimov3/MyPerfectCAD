# ui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser ### ИЗМЕНЕНИЕ: Добавлен colorchooser
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
        
        self.bg_color = 'white'
        self.grid_color = '#e0e0e0'
        self.segment_color = 'red'

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
        self._previous_coord_system = "cartesian"

        p1_frame = ttk.LabelFrame(settings_panel, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p1_x_entry = self.create_coord_entry(p1_frame, "X₁ / R₁:")
        self.p1_y_entry = self.create_coord_entry(p1_frame, "Y₁ / θ₁:")
        p2_frame = ttk.LabelFrame(settings_panel, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p2_x_entry = self.create_coord_entry(p2_frame, "X₂ / R₂:")
        self.p2_y_entry = self.create_coord_entry(p2_frame, "Y₂ / θ₂:")
        ttk.Radiobutton(settings_panel, text="Декартова", variable=self.coord_system, value="cartesian", command=self.on_coord_system_change).pack(anchor=tk.W)
        ttk.Radiobutton(settings_panel, text="Полярная", variable=self.coord_system, value="polar", command=self.on_coord_system_change).pack(anchor=tk.W)
        angle_frame = ttk.LabelFrame(settings_panel, text="Единицы угла")
        angle_frame.pack(padx=5, pady=10, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=self.redraw_all).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=self.redraw_all).pack(anchor=tk.W)

        # === Настройки цвета ===
        color_frame = ttk.LabelFrame(settings_panel, text="Цвета")
        color_frame.pack(padx=5, pady=10, fill=tk.X)
        ttk.Button(color_frame, text="Цвет фона", command=self.on_choose_bg_color).pack(fill=tk.X, pady=2)
        ttk.Button(color_frame, text="Цвет сетки", command=self.on_choose_grid_color).pack(fill=tk.X, pady=2)
        ttk.Button(color_frame, text="Цвет отрезка", command=self.on_choose_segment_color).pack(fill=tk.X, pady=2)
        
        # === Информационная панель ===
        info_panel = ttk.LabelFrame(root, text="Информация", padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        self.length_var = tk.StringVar(value="Длина: N/A")
        self.angle_var = tk.StringVar(value="Угол: N/A")
        ttk.Label(info_panel, textvariable=self.length_var).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Label(info_panel, textvariable=self.angle_var).pack(side=tk.LEFT, padx=5, pady=2)
        self.hotkey_frame = ttk.Frame(info_panel)
        ttk.Label(self.hotkey_frame, text="⏎ Enter - Ввод").pack(side=tk.LEFT, padx=5)
        ttk.Label(self.hotkey_frame, text="⎋ Esc - Отмена").pack(side=tk.LEFT, padx=5)
        
        # === Логика камеры и привязки событий ===
        self.pan_x, self.pan_y, self.zoom = 0, 0, 5.0
        self._drag_start_x, self._drag_start_y = 0, 0
        self.grid_step = 10
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", self.on_mouse_press)
        self.canvas.bind("<B2-Motion>", self.on_mouse_drag)
        self.set_app_state('IDLE')

    def create_coord_entry(self, parent, label_text):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(frame, text=label_text, width=8).pack(side=tk.LEFT)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<KeyRelease>", self.update_preview_segment)
        return entry

    def set_app_state(self, state):
        self.app_state = state
        if state == 'CREATING_SEGMENT':
            for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
                entry.config(state='normal')
            self.root.bind("<Return>", self.finalize_segment)
            self.root.bind("<Escape>", self.cancel_creation)
            self.hotkey_frame.pack(side=tk.RIGHT, padx=5)
        elif state == 'IDLE':
            for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
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
            p1_val1 = float(self.p1_x_entry.get())
            p1_val2 = float(self.p1_y_entry.get())
            p2_val1 = float(self.p2_x_entry.get())
            p2_val2 = float(self.p2_y_entry.get())
        except ValueError:
            self.preview_segment = None
            self.redraw_all()
            return
        p1, p2 = self._create_points_from_entries()
        self.preview_segment = Segment(p1, p2)
        self.redraw_all()

    def finalize_segment(self, event=None):
        if self.preview_segment:
            self.segments.append(self.preview_segment)
            self.set_app_state('IDLE')

    def cancel_creation(self, event=None):
        self.set_app_state('IDLE')

    def on_delete_segment(self, event=None):
        if self.segments:
            self.segments.pop()
            self.redraw_all()

    def on_choose_bg_color(self):
        color_code = colorchooser.askcolor(title="Выберите цвет фона")
        if color_code and color_code[1]:
            self.bg_color = color_code[1]
            self.canvas.config(bg=self.bg_color)
            self.redraw_all()

    def on_choose_grid_color(self):
        color_code = colorchooser.askcolor(title="Выберите цвет сетки")
        if color_code and color_code[1]:
            self.grid_color = color_code[1]
            self.redraw_all()
            
    def on_choose_segment_color(self):
        color_code = colorchooser.askcolor(title="Выберите цвет отрезков")
        if color_code and color_code[1]:
            self.segment_color = color_code[1]
            self.redraw_all()

    def redraw_all(self):
        self.canvas.delete("all")
        self.draw_grid_and_axes()
        active_segment = self.preview_segment if self.preview_segment else self.segments[-1] if self.segments else None
        self.update_info_panel(active_segment)
        for segment in self.segments:
            self.draw_segment(segment, color=self.segment_color, width=3)
        if self.preview_segment:
            self.draw_segment(self.preview_segment, color='blue', width=2)
    
    def update_info_panel(self, segment):
        if segment is None:
            self.length_var.set("Длина: N/A")
            self.angle_var.set("Угол: N/A")
            return
        
        length = segment.length
        angle = segment.angle
        
        if self.angle_units.get() == 'degrees':
            angle = math.degrees(angle)
            unit_symbol = "°"
        else:
            unit_symbol = " rad"
            
        self.length_var.set(f"Длина: {length:.2f}")
        self.angle_var.set(f"Угол: {angle:.2f}{unit_symbol}")

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

    def draw_segment(self, segment, color, width):
        sx1, sy1 = self.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.world_to_screen(segment.p2.x, segment.p2.y)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=color, width=width)
        
    def on_coord_system_change(self):
        new_system = self.coord_system.get()
        if new_system == self._previous_coord_system: return
        try: p1, p2 = self._create_points_from_entries(system=self._previous_coord_system)
        except ValueError: return
        if new_system == "polar":
            r1, theta1 = p1.get_polar_coords(); r2, theta2 = p2.get_polar_coords()
            if self.angle_units.get() == 'degrees': theta1, theta2 = math.degrees(theta1), math.degrees(theta2)
            self._update_entries(r1, theta1, r2, theta2)
        else: self._update_entries(p1.x, p1.y, p2.x, p2.y)
        self._previous_coord_system = new_system

    def _create_points_from_entries(self, system=None):
        current_system = system or self.coord_system.get()
        p1_val1, p1_val2 = float(self.p1_x_entry.get()), float(self.p1_y_entry.get())
        p2_val1, p2_val2 = float(self.p2_x_entry.get()), float(self.p2_y_entry.get())
        p1, p2 = Point(), Point()
        if current_system == 'cartesian': p1, p2 = Point(p1_val1, p1_val2), Point(p2_val1, p2_val2)
        else:
            angle1, angle2 = p1_val2, p2_val2
            if self.angle_units.get() == 'degrees': angle1, angle2 = math.radians(angle1), math.radians(angle2)
            p1.set_from_polar(p1_val1, angle1); p2.set_from_polar(p2_val1, angle2)
        return p1, p2

    def _update_entries(self, p1_v1, p1_v2, p2_v1, p2_v2):
        entries = [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]
        values = [p1_v1, p1_v2, p2_v1, p2_v2]
        for entry, value in zip(entries, values):
            entry.config(state='normal'); entry.delete(0, tk.END); entry.insert(0, f"{value:.2f}")
            if self.app_state == 'IDLE': entry.config(state='disabled')

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
