# app/callbacks.py

import tkinter as tk
from tkinter import messagebox, colorchooser
import math
from logic.geometry import Point, Segment

class Callbacks:
    def __init__(self, root, state, view):
        self.root = root    # Глобальная настройка
        self.state = state  # Модель
        self.view = view    # Представление
        
        self._drag_start_x = 0
        self._drag_start_y = 0

    # Управление состоянием приложения
    def set_app_state(self, mode):
        self.state.app_mode = mode
        is_creating = (mode == 'CREATING_SEGMENT')
        entry_state = 'normal' if is_creating else 'disabled'
        
        entries = [
            self.view.p1_x_entry, self.view.p1_y_entry,
            self.view.p2_x_entry, self.view.p2_y_entry
        ]
        
        if is_creating: # CREATING_SEGMENT
            for entry in entries: entry.config(state=entry_state)
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_segment)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click)
            self.view.canvas.bind("<Button-3>", self.on_rmb_click)
            self.view.hotkey_frame.pack(side=tk.RIGHT, padx=5)
        else: # IDLE
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
            
    # ОБРАБОТЧИКИ РАБОЧЕГО ПРОЦЕССА
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
            final_segment = Segment(
                self.state.preview_segment.p1, 
                self.state.preview_segment.p2, 
                color=self.state.segment_color
            )
            self.state.segments.append(final_segment)
            self.set_app_state('IDLE')

    def on_escape_key(self, event=None):
        if self.state.app_mode == 'CREATING_SEGMENT':
            self.cancel_creation()
        elif self.state.app_mode == 'IDLE':
            if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
                self.root.destroy()

    def cancel_creation(self): self.set_app_state('IDLE')
    
    def on_delete_segment(self, event=None):
        if self.state.segments:
            self.state.segments.pop()
            self.redraw_all()

    # ОБРАБОТЧИКИ ПАНЕЛИ НАСТРОЕК
    def on_apply_settings(self):
        try:
            new_step = int(self.view.grid_step_var.get())
            if new_step <= 0: raise ValueError
            self.state.grid_step = new_step
            self.redraw_all()
        except ValueError:
            messagebox.showerror("Ошибка", "Шаг сетки должен быть целым положительным числом.")

    # Вызывается при смене маркера в выборе системы координат
    def on_coord_system_change(self):
        new_system = self.view.coord_system.get()
        if new_system == 'polar':
            self.view.p2_label1.config(text="R₂:")
            self.view.p2_label2.config(text="θ₂:")
        else:
            self.view.p2_label1.config(text="X₂:")
            self.view.p2_label2.config(text="Y₂:")
            
        try:
            # Получаем текущие значения из полей (это старые данные до переключения)
            val1 = float(self.view.p2_x_entry.get())
            val2 = float(self.view.p2_y_entry.get())
            
            # Нам нужна P1, чтобы правильно сконвертировать
            try:
                p1_x = float(self.view.p1_x_entry.get())
                p1_y = float(self.view.p1_y_entry.get())
            except ValueError:
                p1_x, p1_y = 0.0, 0.0 # Если P1 еще не задана, считаем от (0,0)

            p2 = Point()
            
            # Логика переключения:
            if new_system == 'cartesian':
                # Мы переключились НА Декартову -> значит были в Полярной.
                # val1 - это R, val2 - это Угол.
                # Нужно вычислить P2 относительно P1.
                angle = val2
                if self.view.angle_units.get() == 'degrees': angle = math.radians(angle)
                
                p2.x = p1_x + val1 * math.cos(angle)
                p2.y = p1_y + val1 * math.sin(angle)
            else:
                # Мы переключились НА Полярную -> значит были в Декартовой.
                # val1 - это X, val2 - это Y (абсолютные).
                p2 = Point(val1, val2)
                
        except (ValueError, tk.TclError):
            return
            
        self._update_p2_entries(p2)
        self.redraw_all()

    # ОБРАБОТЧКИ МЫШИ
    def on_lmb_click(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            p2_point = Point(wx, wy)
            self._update_p2_entries(p2_point)
            self.state.points_clicked = 2
        self.update_preview_segment()
    
    def on_rmb_click(self, event):
        if self.view.p2_x_entry.get() or self.view.p2_y_entry.get():
            self.view.p2_x_entry.delete(0, tk.END)
            self.view.p2_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1 
        elif self.view.p1_x_entry.get() or self.view.p1_y_entry.get():
            self.view.p1_x_entry.delete(0, tk.END)
            self.view.p1_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_segment()

    def on_mouse_press(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y

    def on_mouse_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.state.pan_x += dx
        self.state.pan_y += dy
        self._drag_start_x, self._drag_start_y = event.x, event.y
        self.redraw_all()

    def on_mouse_wheel(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        if hasattr(event, 'delta') and event.delta != 0:
            zoom_factor = 1.2 if event.delta > 0 else 1 / 1.2
        elif event.num == 4: zoom_factor = 1.2
        elif event.num == 5: zoom_factor = 1 / 1.2
        else: return
        
        self.state.zoom = max(0.1, min(self.state.zoom * zoom_factor, 100))
        
        sx_after, sy_after = self.world_to_screen(wx, wy)
        self.state.pan_x += event.x - sx_after
        self.state.pan_y += event.y - sy_after
        self.redraw_all()

    def on_canvas_resize(self, event): self.redraw_all()

    # ОБРАБОТЧИКИ КАСТОМИЗАЦИИ
    def toggle_fullscreen(self, event=None):
        self.state.is_fullscreen = not self.state.is_fullscreen
        self.root.attributes("-fullscreen", self.state.is_fullscreen)

    def on_choose_bg_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет фона", initialcolor=self.state.bg_color)
        if color_hex:
            self.state.bg_color = color_hex
            self.view.canvas.config(bg=self.state.bg_color)
            self.view.bg_swatch.config(background=self.state.bg_color)

    def on_choose_grid_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет сетки", initialcolor=self.state.grid_color)
        if color_hex:
            self.state.grid_color = color_hex
            self.view.grid_swatch.config(background=self.state.grid_color)
            self.redraw_all()
            
    def on_choose_segment_color(self):
        _, color_hex = colorchooser.askcolor(title="Выберите цвет отрезков", initialcolor=self.state.segment_color)
        if color_hex:
            self.state.segment_color = color_hex
            self.view.segment_swatch.config(background=self.state.segment_color)
            self.redraw_all()

    def initialize_view(self):
        self.view.canvas.config(background=self.state.bg_color)
        self.view.bg_swatch.config(background=self.state.bg_color)
        self.view.grid_swatch.config(background=self.state.grid_color)
        self.view.segment_swatch.config(background=self.state.segment_color)
        self.set_app_state(self.state.app_mode)

    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    def _create_points_from_entries(self):
        p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
        
        val1 = float(self.view.p2_x_entry.get())
        val2 = float(self.view.p2_y_entry.get())
        
        p2 = Point()
        if self.view.coord_system.get() == 'cartesian':
            # Декартова система - абсолютные координаты
            p2 = Point(val1, val2)
        else:
            # Полярная система - ОТНОСИТЕЛЬНЫЕ координаты (от P1)
            r = val1
            angle = val2
            if self.view.angle_units.get() == 'degrees': angle = math.radians(angle)
            
            # Исправленная логика: прибавляем смещение к P1
            p2.x = p1.x + r * math.cos(angle)
            p2.y = p1.y + r * math.sin(angle)
            
        return p1, p2

    def _update_p1_entries(self, x, y):
        self.view.p1_x_entry.delete(0, tk.END); self.view.p1_x_entry.insert(0, f"{x:.2f}")
        self.view.p1_y_entry.delete(0, tk.END); self.view.p1_y_entry.insert(0, f"{y:.2f}")

    def _update_p2_entries(self, p2_point):
        entries = [self.view.p2_x_entry, self.view.p2_y_entry]
        is_polar = (self.view.coord_system.get() == 'polar')
        
        if is_polar:
            # Нам нужно рассчитать полярные координаты вектора P1->P2
            try:
                p1_x = float(self.view.p1_x_entry.get())
                p1_y = float(self.view.p1_y_entry.get())
            except ValueError:
                p1_x, p1_y = 0.0, 0.0
            
            dx = p2_point.x - p1_x
            dy = p2_point.y - p1_y
            
            r = math.sqrt(dx**2 + dy**2)
            theta = math.atan2(dy, dx)
            
            if self.view.angle_units.get() == 'degrees': theta = math.degrees(theta)
            values = [r, theta]
        else:
            values = [p2_point.x, p2_point.y]
            
        for entry, value in zip(entries, values):
            entry.config(state='normal'); entry.delete(0, tk.END); entry.insert(0, f"{value:.2f}")
            if self.state.app_mode == 'IDLE': entry.config(state='disabled')

    # ПРЕОБРАЗОВАНИЯ КООРДИНАТ
    def world_to_screen(self, world_x, world_y):
        cx = self.view.canvas.winfo_width() / 2
        cy = self.view.canvas.winfo_height() / 2
        return (cx + self.state.pan_x + (world_x * self.state.zoom), 
                cy + self.state.pan_y - (world_y * self.state.zoom))

    def screen_to_world(self, screen_x, screen_y):
        cx = self.view.canvas.winfo_width() / 2
        cy = self.view.canvas.winfo_height() / 2
        return ((screen_x - cx - self.state.pan_x) / self.state.zoom, 
                -(screen_y - cy - self.state.pan_y) / self.state.zoom)
    
    # ЛОГИКА ОТРИСОВКИ
    def redraw_all(self):
        self.view.canvas.delete("all")
        self.draw_grid_and_axes()
        self.update_info_panel()
        
        if self.state.active_p1: self.draw_point(self.state.active_p1)
        if self.state.active_p2: self.draw_point(self.state.active_p2)
        
        for segment in self.state.segments: self.draw_segment(segment, width=4)
        if self.state.preview_segment: self.draw_segment(self.state.preview_segment, width=2, color='blue')
    
    def update_info_panel(self):
        self.state.active_p1, self.state.active_p2 = None, None

        if self.state.app_mode == 'CREATING_SEGMENT':
            try: self.state.active_p1 = Point(float(self.view.p1_x_entry.get()), float(self.view.p1_y_entry.get()))
            except (ValueError, tk.TclError): pass
            try:
                # Используем обновленный метод создания точек
                p1_for_p2, self.state.active_p2 = self._create_points_from_entries()
                if self.state.active_p1 is None: self.state.active_p1 = p1_for_p2
            except (ValueError, tk.TclError): pass
        elif self.state.segments:
            pass
            
        p1, p2 = self.state.active_p1, self.state.active_p2
        
        if p1: self.view.p1_coord_var.set(f"P1({p1.x:.2f}, {p1.y:.2f})")
        else: self.view.p1_coord_var.set("P1: N/A")
        
        if p2:
            if self.view.coord_system.get() == 'polar':
                # Для инфо-панели тоже показываем относительные полярные координаты
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
            if self.view.angle_units.get() == 'degrees':
                self.view.angle_var.set(f"Угол: {math.degrees(angle):.2f}°")
            else:
                self.view.angle_var.set(f"Угол: {angle:.2f} rad")
        else:
            self.view.length_var.set("Длина: N/A")
            self.view.angle_var.set("Угол: N/A")

    def draw_grid_and_axes(self):
        w, h = self.view.canvas.winfo_width(), self.view.canvas.winfo_height()
        if w < 2 or h < 2: return
        
        world_tl_x, world_tl_y = self.screen_to_world(0, 0)
        world_br_x, world_br_y = self.screen_to_world(w, h)
        
        start_x = math.ceil(world_tl_x / self.state.grid_step) * self.state.grid_step
        for wx in range(start_x, int(world_br_x), self.state.grid_step):
            sx, _ = self.world_to_screen(wx, 0)
            self.view.canvas.create_line(sx, 0, sx, h, fill='black' if wx==0 else self.state.grid_color, width=2 if wx==0 else 1)
            
        start_y = math.ceil(world_br_y / self.state.grid_step) * self.state.grid_step
        for wy in range(start_y, int(world_tl_y), self.state.grid_step):
            _, sy = self.world_to_screen(0, wy)
            self.view.canvas.create_line(0, sy, w, sy, fill='black' if wy==0 else self.state.grid_color, width=2 if wy==0 else 1)
        
        sx, sy = self.world_to_screen(0,0)
        if 0 < sx < w: self.view.canvas.create_text(sx + 10, 10, text="Y", font=("Arial", 10), anchor='nw', fill='gray')
        if 0 < sy < h: self.view.canvas.create_text(w - 10, sy - 10, text="X", font=("Arial", 10), anchor='se', fill='gray')

    def draw_segment(self, segment, width, color=None):
        draw_color = color if color else segment.color
        sx1, sy1 = self.world_to_screen(segment.p1.x, segment.p1.y)
        sx2, sy2 = self.world_to_screen(segment.p2.x, segment.p2.y)
        self.view.canvas.create_line(sx1, sy1, sx2, sy2, fill=draw_color, width=width)
    
    def draw_point(self, point, size=4, color='black'):
        x, y = self.world_to_screen(point.x, point.y)
        self.view.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)