# ui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import math
from logic.geometry import Point, Segment
import sv_ttk

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
        self.points_clicked = 0
        self.is_fullscreen = False
        self.active_p1 = None
        self.active_p2 = None
        self.bg_color, self.grid_color, self.segment_color = '#2b2b2b', '#404040', '#ff8080'

        # === Панели интерфейса ===
        toolbar = ttk.Frame(root, padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(toolbar, text="Отрезок", command=self.on_new_segment_mode).pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(toolbar, text="Удалить", command=self.on_delete_segment).pack(side=tk.LEFT, padx=5, pady=2)

        self.canvas = tk.Canvas(root, bg=self.bg_color, borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky=('W', 'E', 'N', 'S'), padx=5, pady=5)
        
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=('E', 'N', 'S'), padx=5, pady=5)
        
        info_panel = ttk.Frame(root, padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        
        self.setup_settings_panel(settings_panel)
        self.setup_info_panel(info_panel)
        
        # === Логика камеры и привязки событий ===
        self.pan_x, self.pan_y, self.zoom = 0, 0, 5.0
        self.grid_step = 10
        self._drag_start_x, self._drag_start_y = 0, 0
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<ButtonPress-2>", self.on_mouse_press)
        self.canvas.bind("<B2-Motion>", self.on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.root.bind("<F11>", self.toggle_fullscreen)
        
        self.set_app_state('IDLE')

    def setup_settings_panel(self, parent):
        self.coord_system = tk.StringVar(value="cartesian")
        self.angle_units = tk.StringVar(value="degrees")
        p1_frame = ttk.LabelFrame(parent, text="Точка 1 (P1)")
        p1_frame.pack(padx=5, pady=5, fill=tk.X)
        _, self.p1_x_entry = self.create_coord_entry(p1_frame, "X₁:")
        _, self.p1_y_entry = self.create_coord_entry(p1_frame, "Y₁:")
        p2_frame = ttk.LabelFrame(parent, text="Точка 2 (P2)")
        p2_frame.pack(padx=5, pady=5, fill=tk.X)
        self.p2_label1, self.p2_x_entry = self.create_coord_entry(p2_frame, "X₂:")
        self.p2_label2, self.p2_y_entry = self.create_coord_entry(p2_frame, "Y₂:")
        ttk.Radiobutton(parent, text="P2: Декартова (X₂, Y₂)", variable=self.coord_system, value="cartesian", command=self.on_coord_system_change).pack(anchor=tk.W)
        ttk.Radiobutton(parent, text="P2: Полярная (R₂, θ₂)", variable=self.coord_system, value="polar", command=self.on_coord_system_change).pack(anchor=tk.W)
        angle_frame = ttk.LabelFrame(parent, text="Единицы угла")
        angle_frame.pack(padx=5, pady=10, fill=tk.X)
        ttk.Radiobutton(angle_frame, text="Градусы", variable=self.angle_units, value="degrees", command=self.redraw_all).pack(anchor=tk.W)
        ttk.Radiobutton(angle_frame, text="Радианы", variable=self.angle_units, value="radians", command=self.redraw_all).pack(anchor=tk.W)
        grid_frame = ttk.LabelFrame(parent, text="Сетка")
        grid_frame.pack(padx=5, pady=10, fill=tk.X)
        self.grid_step_var = tk.StringVar(value="10")
        ttk.Label(grid_frame, text="Шаг:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Entry(grid_frame, textvariable=self.grid_step_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(grid_frame, text="Применить", command=self.on_apply_settings).pack(side=tk.LEFT, padx=5)
        color_frame = ttk.LabelFrame(parent, text="Цвета и Тема")
        color_frame.pack(padx=5, pady=10, fill=tk.X)
        self.bg_swatch = self.create_color_chooser(color_frame, "Фон:", self.bg_color, self.on_choose_bg_color)
        self.grid_swatch = self.create_color_chooser(color_frame, "Сетка:", self.grid_color, self.on_choose_grid_color)
        self.segment_swatch = self.create_color_chooser(color_frame, "Отрезок:", self.segment_color, self.on_choose_segment_color)
        ttk.Button(color_frame, text="Сменить тему", command=self.toggle_theme).pack(fill=tk.X, pady=(10, 2))
    
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
        
        if is_creating:
            for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
                entry.config(state='normal')
            self.points_clicked = 0
            self.root.bind("<Return>", self.finalize_segment)
            self.root.bind("<Escape>", self.cancel_creation)
            self.canvas.bind("<Button-1>", self.on_lmb_click)
            self.canvas.bind("<Button-3>", self.on_rmb_click)
            self.hotkey_frame.pack(side=tk.RIGHT, padx=5)
        else: # IDLE state
            # ИСПРАВЛЕНИЕ: Объединяем логику в один цикл с правильным порядком
            for entry in [self.p1_x_entry, self.p1_y_entry, self.p2_x_entry, self.p2_y_entry]:
                entry.delete(0, tk.END)
                entry.config(state='disabled')
            
            self.root.unbind("<Return>")
            self.root.unbind("<Escape>")
            self.canvas.unbind("<Button-1>")
            self.canvas.unbind("<Button-3>")
            self.hotkey_frame.pack_forget()
            self.preview_segment = None
            self.redraw_all()
            
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def toggle_theme(self):
        if sv_ttk.get_theme() == "dark":
            sv_ttk.set_theme("light")
            self.bg_color, self.grid_color, self.segment_color = 'white', '#e0e0e0', 'red'
        else:
            sv_ttk.set_theme("dark")
            self.bg_color, self.grid_color, self.segment_color = '#2b2b2b', '#404040', '#ff8080'
        
        self.canvas.config(bg=self.bg_color)
        self.bg_swatch.config(background=self.bg_color)
        self.grid_swatch.config(background=self.grid_color)
        self.segment_swatch.config(background=self.segment_color)
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
            final_segment = Segment(self.preview_segment.p1, self.preview_segment.p2, color=self.segment_color)
            self.segments.append(final_segment)
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
        if new_system == 'polar': self.p2_label1.config(text="R₂:"); self.p2_label2.config(text="θ₂:")
        else: self.p2_label1.config(text="X₂:"); self.p2_label2.config(text="Y₂:")
        try:
            val1 = float(self.p2_x_entry.get()); val2 = float(self.p2_y_entry.get())
            p2 = Point()
            if self.coord_system.get() == 'cartesian':
                angle = val2
                if self.angle_units.get() == 'degrees': angle = math.radians(angle)
                p2.set_from_polar(val1, angle)
            else: p2 = Point(val1, val2)
        except (ValueError, tk.TclError): return
        self._update_p2_entries(p2)
        self.redraw_all()

    def on_lmb_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        if self.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.points_clicked = 1
        elif self.points_clicked == 1:
            p2_point = Point(wx, wy)
            self._update_p2_entries(p2_point)
            self.points_clicked = 2
        self.update_preview_segment()
    
    def on_rmb_click(self, event):
        if self.points_clicked == 2:
            self.p2_x_entry.delete(0, tk.END); self.p2_y_entry.delete(0, tk.END)
            self.points_clicked = 1
        elif self.points_clicked == 1:
            self.p1_x_entry.delete(0, tk.END); self.p1_y_entry.delete(0, tk.END)
            self.points_clicked = 0
        self.update_preview_segment()

    def on_mouse_wheel(self, event):
        world_before_zoom_x, world_before_zoom_y = self.screen_to_world(event.x, event.y)
        if hasattr(event, 'delta') and event.delta != 0:
            zoom_factor = 1.2 if event.delta > 0 else 1 / 1.2
        elif event.num == 4:
            zoom_factor = 1.2
        elif event.num == 5:
            zoom_factor = 1 / 1.2
        else: return
        self.zoom *= zoom_factor
        self.zoom = max(0.1, min(self.zoom, 100))
        screen_after_zoom_x, screen_after_zoom_y = self.world_to_screen(world_before_zoom_x, world_before_zoom_y)
        pan_dx = event.x - screen_after_zoom_x
        pan_dy = event.y - screen_after_zoom_y
        self.pan_x += pan_dx; self.pan_y += pan_dy
        self.redraw_all()

    def _create_points_from_entries(self):
        p1 = Point(float(self.p1_x_entry.get()), float(self.p1_y_entry.get()))
        p2 = Point()
        val1 = float(self.p2_x_entry.get()); val2 = float(self.p2_y_entry.get())
        if self.coord_system.get() == 'cartesian': p2 = Point(val1, val2)
        else:
            angle = val2
            if self.angle_units.get() == 'degrees': angle = math.radians(angle)
            p2.set_from_polar(val1, angle)
        return p1, p2

    def _update_p1_entries(self, x, y):
        self.p1_x_entry.delete(0, tk.END); self.p1_x_entry.insert(0, f"{x:.2f}")
        self.p1_y_entry.delete(0, tk.END); self.p1_y_entry.insert(0, f"{y:.2f}")

    def _update_p2_entries(self, p2_point):
        entries = [self.p2_x_entry, self.p2_y_entry]
        is_polar = (self.coord_system.get() == 'polar')
        if is_polar:
            r, theta = p2_point.get_polar_coords()
            if self.angle_units.get() == 'degrees': theta = math.degrees(theta)
            values = [r, theta]
        else: values = [p2_point.x, p2_point.y]
        for entry, value in zip(entries, values):
            entry.config(state='normal'); entry.delete(0, tk.END); entry.insert(0, f"{value:.2f}")
            if self.app_state == 'IDLE': entry.config(state='disabled')

    def redraw_all(self):
        self.canvas.delete("all"); self.draw_grid_and_axes()
        self.update_info_panel()
        if self.active_p1: self.draw_point(self.active_p1)
        if self.active_p2: self.draw_point(self.active_p2)
        for segment in self.segments: self.draw_segment(segment, width=4)
        if self.preview_segment: self.draw_segment(self.preview_segment, width=2, color='blue')
    
    def update_info_panel(self):
        self.active_p1, self.active_p2 = None, None
        length, angle_rad = None, None
        if self.app_state == 'CREATING_SEGMENT':
            try: self.active_p1 = Point(float(self.p1_x_entry.get()), float(self.p1_y_entry.get()))
            except (ValueError, tk.TclError): pass
            try:
                p1_for_p2, self.active_p2 = self._create_points_from_entries()
                if self.active_p1 is None: self.active_p1 = p1_for_p2
            except (ValueError, tk.TclError): pass
        elif self.segments:
            last_segment = self.segments[-1]
            self.active_p1, self.active_p2 = last_segment.p1, last_segment.p2
        p1, p2 = self.active_p1, self.active_p2
        if p1: self.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
        else: self.p1_coord_var.set("P1: N/A")
        if p2:
            if self.coord_system.get() == 'polar':
                r, theta = p2.get_polar_coords()
                unit_sym = "°" if self.angle_units.get() == 'degrees' else " rad"
                if self.angle_units.get() == 'degrees': theta = math.degrees(theta)
                self.p2_coord_var.set(f"P2(r={r:.2f}, θ={theta:.2f}{unit_sym})")
            else: self.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
        else: self.p2_coord_var.set("P2: N/A")
        if p1 and p2: length, angle_rad = Segment(p1, p2).length, Segment(p1, p2).angle
        if length is not None: self.length_var.set(f"Длина: {length:.2f}")
        else: self.length_var.set("Длина: N/A")
        if angle_rad is not None:
            if self.angle_units.get() == 'degrees': val, sym = math.degrees(angle_rad), "°"
            else: val, sym = angle_rad, " rad"
            self.angle_var.set(f"Угол: {val:.2f}{sym}")
        else: self.angle_var.set("Угол: N/A")

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
        x_axis_pos_y = self.world_to_screen(0,0)[1]
        if 0 < x_axis_pos_y < height: self.canvas.create_text(width - 10, x_axis_pos_y - 10, text="X", font=("Arial", 10), anchor='se', fill='gray')
        y_axis_pos_x = self.world_to_screen(0,0)[0]
        if 0 < y_axis_pos_x < width: self.canvas.create_text(y_axis_pos_x + 10, 10, text="Y", font=("Arial", 10), anchor='nw', fill='gray')

    def draw_segment(self, segment, width, color=None):
        draw_color = color if color else segment.color
        sx1, sy1 = self.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.world_to_screen(segment.p2.x, segment.p2.y)
        self.canvas.create_line(sx1, sy1, sx2, sy2, fill=draw_color, width=width)
    
    def draw_point(self, point, size=4, color='black'):
        x, y = self.world_to_screen(point.x, point.y)
        self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)

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