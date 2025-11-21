# app/callbacks.py

import tkinter as tk
from tkinter import messagebox, colorchooser
import math
from logic.geometry import Point, Segment
from logic.converter import CoordinateConverter # Импортируем новые модули
from ui.renderer import Renderer

class Callbacks:
    def __init__(self, root, state, view):
        self.root = root
        self.state = state
        self.view = view
        
        # Будут инициализированы в initialize_view, когда Canvas будет готов
        self.converter = None
        self.renderer = None
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    def initialize_view(self):
        # Инициализация вспомогательных систем
        self.converter = CoordinateConverter(self.state, self.view.canvas)
        self.renderer = Renderer(self.view.canvas, self.state, self.converter)
        
        # Применение начальных цветов
        self.view.canvas.config(background=self.state.bg_color)
        self.view.bg_swatch.config(background=self.state.bg_color)
        self.view.grid_swatch.config(background=self.state.grid_color)
        self.view.segment_swatch.config(background=self.state.segment_color)
        
        self.set_app_state(self.state.app_mode)

    def set_app_state(self, mode):
        self.state.app_mode = mode
        is_creating = (mode == 'CREATING_SEGMENT')
        entry_state = 'normal' if is_creating else 'disabled'
        
        entries = [self.view.p1_x_entry, self.view.p1_y_entry, self.view.p2_x_entry, self.view.p2_y_entry]
        
        if is_creating:
            for entry in entries: entry.config(state=entry_state)
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_segment)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click)
            self.view.canvas.bind("<Button-3>", self.on_rmb_click)
            self.view.hotkey_frame.pack(side=tk.RIGHT, padx=5)
        else:
            for entry in entries:
                entry.delete(0, tk.END)
                entry.config(state=entry_state)
            self.root.unbind("<Return>")
            self.view.canvas.unbind("<Button-1>")
            self.view.canvas.unbind("<Button-3>")
            self.view.hotkey_frame.pack_forget()
            self.state.preview_segment = None
            self.state.active_p1 = None
            self.state.active_p2 = None
            self.redraw_all()

    # --- ОБРАБОТЧИКИ ---
    def on_new_segment_mode(self, event=None):
        self.set_app_state('CREATING_SEGMENT')
        self.view.p1_x_entry.focus_set()

    def update_preview_segment(self, event=None):
        try:
            p1, p2 = self._create_points_from_entries()
            self.state.preview_segment = Segment(p1, p2)
        except (ValueError, tk.TclError):
            self.state.preview_segment = None
        self.redraw_all()

    def finalize_segment(self, event=None):
        if self.state.preview_segment:
            final_segment = Segment(self.state.preview_segment.p1, self.state.preview_segment.p2, color=self.state.segment_color)
            self.state.segments.append(final_segment)
            self.set_app_state('IDLE')

    def on_escape_key(self, event=None):
        if self.state.app_mode == 'CREATING_SEGMENT': self.set_app_state('IDLE')
        elif self.state.app_mode == 'IDLE' and messagebox.askyesno("Выход", "Выйти из программы?"): self.root.destroy()

    def on_delete_segment(self, event=None):
        if self.state.segments:
            self.state.segments.pop()
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
            if new_system == 'cartesian': # Были в полярной
                angle = math.radians(val2) if self.view.angle_units.get() == 'degrees' else val2
                p2.x = p1_x + val1 * math.cos(angle)
                p2.y = p1_y + val1 * math.sin(angle)
            else: # Были в декартовой
                p2 = Point(val1, val2)
        except (ValueError, tk.TclError): return
        
        self._update_p2_entries(p2)
        self.redraw_all()

    # --- МЫШЬ ---
    def on_lmb_click(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            self._update_p2_entries(Point(wx, wy))
            self.state.points_clicked = 2
        self.update_preview_segment()

    def on_rmb_click(self, event):
        # Логика очистки полей
        if self.view.p2_x_entry.get(): 
            self.view.p2_x_entry.delete(0, tk.END); self.view.p2_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.p1_x_entry.get():
            self.view.p1_x_entry.delete(0, tk.END); self.view.p1_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_segment()

    def on_mouse_press(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y

    def on_mouse_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.state.pan_x += dx; self.state.pan_y += dy
        self._drag_start_x, self._drag_start_y = event.x, event.y
        self.redraw_all()

    def on_mouse_wheel(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        factor = 1.2 if (hasattr(event, 'delta') and event.delta > 0) or event.num == 4 else 1/1.2
        self.state.zoom = max(0.1, min(self.state.zoom * factor, 100))
        
        sx_new, sy_new = self.converter.world_to_screen(wx, wy)
        self.state.pan_x += event.x - sx_new
        self.state.pan_y += event.y - sy_new
        self.redraw_all()

    def on_canvas_resize(self, event): self.redraw_all()
    
    def toggle_fullscreen(self, event=None):
        self.state.is_fullscreen = not self.state.is_fullscreen
        self.root.attributes("-fullscreen", self.state.is_fullscreen)

    # --- ЦВЕТА ---
    def on_choose_bg_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.bg_color)
        if c: 
            self.state.bg_color = c
            self.view.canvas.config(bg=c); self.view.bg_swatch.config(bg=c)

    def on_choose_grid_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.grid_color)
        if c: self.state.grid_color = c; self.view.grid_swatch.config(bg=c); self.redraw_all()

    def on_choose_segment_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.segment_color)
        if c: self.state.segment_color = c; self.view.segment_swatch.config(bg=c); self.redraw_all()

    # --- ЛОГИКА ДАННЫХ ---
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

    # --- ГЛАВНЫЙ МЕТОД ОТРИСОВКИ ---
    def redraw_all(self):
        # Теперь это просто делегирование
        self.update_info_panel()
        if self.renderer:
            self.renderer.render_scene()
    
    def update_info_panel(self):
        self.state.active_p1, self.state.active_p2 = None, None
        if self.state.app_mode == 'CREATING_SEGMENT':
            try: self.state.active_p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
            except (ValueError, tk.TclError): pass
            try:
                p1_for_p2, self.state.active_p2 = self._create_points_from_entries()
                if self.state.active_p1 is None: self.state.active_p1 = p1_for_p2
            except (ValueError, tk.TclError): pass
            
        p1, p2 = self.state.active_p1, self.state.active_p2
        
        if p1: self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
        else: self.view.p1_coord_var.set("P1: N/A")
        
        if p2:
            if self.view.coord_system.get() == 'polar':
                dx = p2.x - (p1.x if p1 else 0)
                dy = p2.y - (p1.y if p1 else 0)
                r = math.sqrt(dx**2 + dy**2)
                theta = math.atan2(dy, dx)
                unit = self.view.angle_units.get()
                sym = "°" if unit == 'degrees' else " rad"
                if unit == 'degrees': theta = math.degrees(theta)
                self.view.p2_coord_var.set(f"P2(r={r:.2f}, θ={theta:.2f}{sym})")
            else: self.view.p2_coord_var.set(f"P2({p2.x:.2f}, {p2.y:.2f})")
        else: self.view.p2_coord_var.set("P2: N/A")

        if p1 and p2:
            seg = Segment(p1, p2)
            self.view.length_var.set(f"Длина: {seg.length:.2f}")
            angle = seg.angle
            val = math.degrees(angle) if self.view.angle_units.get() == 'degrees' else angle
            sym = "°" if self.view.angle_units.get() == 'degrees' else " rad"
            self.view.angle_var.set(f"Угол: {val:.2f}{sym}")
        else:
            self.view.length_var.set("Длина: N/A"); self.view.angle_var.set("Угол: N/A")