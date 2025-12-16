import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import math
import copy
import uuid

class StyleManagerWindow(tk.Toplevel):
    def __init__(self, parent, state, on_update_callback):
        super().__init__(parent)
        self.title("Менеджер стилей линий (ЕСКД)")
        self.geometry("750x620")
        
        self.state = state
        self.on_update_callback = on_update_callback
        
        self.preview_zoom = 2.0 
        self.px_ratio = self.state.mm_to_px_ratio * self.preview_zoom
        
        self.transient(parent)
        self.grab_set()

        top_frame = ttk.LabelFrame(self, text="Общие настройки чертежа", padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Базовая толщина S (мм):").pack(side=tk.LEFT)
        self.global_s_var = tk.StringVar(value=str(state.base_thickness_mm))
        self.spin_s = ttk.Spinbox(top_frame, from_=0.5, to=1.4, increment=0.1, textvariable=self.global_s_var, width=6)
        self.spin_s.pack(side=tk.LEFT, padx=10)
        self.spin_s.bind("<KeyRelease>", self.update_preview)
        self.spin_s.bind("<<Increment>>", self.delayed_update)
        self.spin_s.bind("<<Decrement>>", self.delayed_update)

        center_frame = ttk.Frame(self)
        center_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)

        left_panel = ttk.Frame(center_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        ttk.Label(left_panel, text="Стили линий:").pack(anchor=tk.W)
        self.style_listbox = tk.Listbox(left_panel, width=30, height=15, exportselection=False)
        self.style_listbox.pack(fill=tk.Y, expand=True, pady=5)
        self.style_listbox.bind("<<ListboxSelect>>", self.on_style_select)
        
        list_btn_frame = ttk.Frame(left_panel)
        list_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(list_btn_frame, text="+ Копия", command=self.add_style).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        self.btn_delete = ttk.Button(list_btn_frame, text="Удалить", command=self.delete_style)
        self.btn_delete.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        right_panel = ttk.LabelFrame(center_frame, text="Параметры выбранного стиля", padding="15")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(right_panel, text="Название:").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        self.entry_name = ttk.Entry(right_panel, textvariable=self.name_var)
        self.entry_name.pack(fill=tk.X, pady=(0, 10))

        self.is_main_var = tk.BooleanVar()
        self.chk_is_main = ttk.Checkbutton(right_panel, text="Основная толщина (S)", variable=self.is_main_var, command=self.update_preview)
        self.chk_is_main.pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(right_panel, text=f"Предпросмотр (Масштаб {int(self.preview_zoom*100)}%):").pack(anchor=tk.W, pady=(15, 5))
        self.preview_canvas = tk.Canvas(right_panel, height=100, bg="white", relief="sunken", borderwidth=1)
        self.preview_canvas.pack(fill=tk.X, pady=0)
        self.preview_canvas.bind("<Configure>", self.update_preview)

        self.dash_frame = ttk.LabelFrame(right_panel, text="Параметры штриховки (мм)", padding=10)
        
        ttk.Label(self.dash_frame, text="Штрих:").grid(row=0, column=0, padx=5)
        self.dash_val = tk.StringVar()
        self.spin_dash = ttk.Spinbox(self.dash_frame, from_=0.1, to=100, increment=0.5, textvariable=self.dash_val, width=6)
        self.spin_dash.grid(row=0, column=1, padx=5)
        self.spin_dash.bind("<KeyRelease>", self.update_preview)
        self.spin_dash.bind("<<Increment>>", self.delayed_update)
        self.spin_dash.bind("<<Decrement>>", self.delayed_update)

        ttk.Label(self.dash_frame, text="Пробел:").grid(row=0, column=2, padx=5)
        self.gap_val = tk.StringVar()
        self.spin_gap = ttk.Spinbox(self.dash_frame, from_=0.1, to=100, increment=0.5, textvariable=self.gap_val, width=6)
        self.spin_gap.grid(row=0, column=3, padx=5)
        self.spin_gap.bind("<KeyRelease>", self.update_preview)
        self.spin_gap.bind("<<Increment>>", self.delayed_update)
        self.spin_gap.bind("<<Decrement>>", self.delayed_update)

        self.kinks_frame = ttk.LabelFrame(right_panel, text="Параметры изломов", padding=10)
        ttk.Label(self.kinks_frame, text="Кол-во изломов:").grid(row=0, column=0, padx=5)
        self.kinks_val = tk.StringVar()
        self.spin_kinks = ttk.Spinbox(self.kinks_frame, from_=1, to=100, increment=1, textvariable=self.kinks_val, width=6)
        self.spin_kinks.grid(row=0, column=1, padx=5)
        self.spin_kinks.bind("<KeyRelease>", self.update_preview)
        self.spin_kinks.bind("<<Increment>>", self.delayed_update)
        self.spin_kinks.bind("<<Decrement>>", self.delayed_update)

        self.wave_frame = ttk.LabelFrame(right_panel, text="Параметры волны", padding=10)
        ttk.Label(self.wave_frame, text="Амплитуда:").grid(row=0, column=0, padx=5)
        self.wave_amp_val = tk.StringVar()
        self.spin_wave_amp = ttk.Spinbox(self.wave_frame, from_=0.5, to=50, increment=0.5, textvariable=self.wave_amp_val, width=6)
        self.spin_wave_amp.grid(row=0, column=1, padx=5)
        self.spin_wave_amp.bind("<KeyRelease>", self.update_preview)
        self.spin_wave_amp.bind("<<Increment>>", self.delayed_update)
        self.spin_wave_amp.bind("<<Decrement>>", self.delayed_update)

        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Button(btn_frame, text="Закрыть", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Применить", command=self.apply_changes).pack(side=tk.RIGHT, padx=10)

        self.refresh_list()

    def delayed_update(self, event=None):
        self.after(10, self.update_preview)

    def refresh_list(self, select_key=None):
        self.style_listbox.delete(0, tk.END)
        self.style_keys = []
        sorted_styles = sorted(self.state.line_styles.items(), key=lambda x: (x[1].is_custom, x[1].display_name))
        for key, style in sorted_styles:
            name = style.display_name
            if style.is_custom: name += " (Польз.)"
            self.style_listbox.insert(tk.END, name)
            self.style_keys.append(key)

        target_key = select_key if select_key else self.state.current_style_name
        try:
            idx = self.style_keys.index(target_key)
            self.style_listbox.selection_set(idx)
            self.style_listbox.see(idx)
            self.on_style_select(None)
        except:
            if self.style_keys:
                self.style_listbox.selection_set(0)
                self.on_style_select(None)

    def add_style(self):
        idx = self.style_listbox.curselection()
        if not idx: return
        key = self.style_keys[idx[0]]
        original = self.state.line_styles[key]
        new_key = f"custom_{uuid.uuid4().hex[:8]}"
        new_style = copy.deepcopy(original)
        new_style.name = new_key
        new_style.display_name = f"Копия {original.display_name}"
        new_style.is_custom = True
        if new_style.limits:
            new_style.limits = (0.1, 200.0, 0.1, 200.0)
        self.state.line_styles[new_key] = new_style
        self.refresh_list(select_key=new_key)

    def delete_style(self):
        idx = self.style_listbox.curselection()
        if not idx: return
        key = self.style_keys[idx[0]]
        style = self.state.line_styles[key]
        if not style.is_custom:
            messagebox.showwarning("Ошибка", "Нельзя удалять базовые стили ГОСТ!")
            return
        if messagebox.askyesno("Удаление", f"Удалить стиль '{style.display_name}'?"):
            default_style = 'solid_main'
            for seg in self.state.segments:
                if seg.style_name == key: seg.style_name = default_style
            if self.state.current_style_name == key: self.state.current_style_name = default_style
            del self.state.line_styles[key]
            self.refresh_list(select_key=default_style)
            self.on_update_callback()

    def on_style_select(self, event):
        idx = self.style_listbox.curselection()
        if not idx: return
        key = self.style_keys[idx[0]]
        style = self.state.line_styles[key]
        
        self.name_var.set(style.display_name)
        self.is_main_var.set(style.is_main)
        
        if style.is_custom:
            self.entry_name.config(state='normal')
            self.btn_delete.config(state='normal')
            self.chk_is_main.config(state='normal')
        else:
            self.entry_name.config(state='readonly')
            self.btn_delete.config(state='disabled')
            self.chk_is_main.config(state='disabled')
        
        self.dash_frame.pack_forget()
        self.kinks_frame.pack_forget()
        self.wave_frame.pack_forget()
        
        if style.limits: 
            self.dash_frame.pack(fill=tk.X, pady=15, side=tk.TOP, before=self.preview_canvas)
            min_d, max_d, min_g, max_g = style.limits
            self.spin_dash.config(from_=min_d, to=max_d, state='normal')
            self.spin_gap.config(from_=min_g, to=max_g, state='normal')
            if style.dash_pattern:
                self.dash_val.set(str(style.dash_pattern[0]))
                self.gap_val.set(str(style.dash_pattern[1]))
        
        if style.base_type == 'zigzag':
            self.kinks_frame.pack(fill=tk.X, pady=15, side=tk.TOP, before=self.preview_canvas)
            kinks = getattr(style, 'kinks_count', None)
            if kinks is not None:
                self.kinks_val.set(str(kinks))
            else:
                self.kinks_val.set('2')
            self.spin_kinks.config(state='normal')
        
        if style.base_type == 'wave':
            self.wave_frame.pack(fill=tk.X, pady=15, side=tk.TOP, before=self.preview_canvas)
            amp = getattr(style, 'wave_amplitude', None)
            if amp is not None:
                self.wave_amp_val.set(str(amp))
            else:
                self.wave_amp_val.set('3.0')
            self.spin_wave_amp.config(state='normal')
        
        self.update_preview()

    def _generate_dashed_coords(self, x1, y1, x2, y2, pattern, px_ratio):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return []
        
        ux, uy = dx/length, dy/length
        scaled_pattern = [float(val) * self.px_ratio for val in pattern]
        
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

    def _generate_wave_coords(self, x1, y1, x2, y2, wave_amplitude=None):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = []
        step = 5 * self.preview_zoom
        
        base_amp = wave_amplitude if wave_amplitude is not None else 3.0
        amplitude = base_amp * self.preview_zoom
        freq = 0.2 / self.preview_zoom
        
        if step < 0.1: step = 0.1
        
        t = 0
        while t < length:
            offset = amplitude * math.sin(t * freq)
            points.extend([x1 + ux*t + nx*offset, y1 + uy*t + ny*offset])
            t += step
        points.extend([x2, y2])
        return points

    def _generate_zigzag_coords(self, x1, y1, x2, y2, kinks_count=None):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        
        points = [x1, y1]
        kink_len = 8 * self.preview_zoom
        amplitude = 5 * self.preview_zoom
        
        if kinks_count is not None and kinks_count > 0:
            total_kinks_len = kinks_count * kink_len
            
            if total_kinks_len < length:
                gap = (length - total_kinks_len) / (kinks_count + 1)
                
                current_dist = 0
                for _ in range(kinks_count):
                    current_dist += gap
                    bx = x1 + ux * current_dist
                    by = y1 + uy * current_dist
                    points.extend([bx, by])
                    
                    d1 = current_dist + kink_len * 0.25
                    d2 = current_dist + kink_len * 0.75
                    d3 = current_dist + kink_len
                    
                    points.extend([
                        x1 + ux*d1 - nx*amplitude, y1 + uy*d1 - ny*amplitude,
                        x1 + ux*d2 + nx*amplitude, y1 + uy*d2 + ny*amplitude,
                        x1 + ux*d3, y1 + uy*d3
                    ])
                    current_dist += kink_len
                
                points.extend([x2, y2])
                return points
            else:
                max_kinks = max(1, int((length - kink_len) / (kink_len * 1.5)))
                return self._generate_zigzag_coords(x1, y1, x2, y2, kinks_count=max_kinks)
        
        period = 40 * self.preview_zoom
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

    def update_preview(self, event=None):
        self.preview_canvas.delete("all")
        idx = self.style_listbox.curselection()
        if not idx: return
        key = self.style_keys[idx[0]]
        style = self.state.line_styles[key]

        try: val_str = self.global_s_var.get().replace(',', '.'); s_mm = float(val_str)
        except ValueError: s_mm = self.state.base_thickness_mm

        is_main = self.is_main_var.get()
        s_px = s_mm * self.px_ratio
        width = max(1, int(s_px)) if is_main else max(1, int(s_px / 2))

        dash_pattern = None
        if style.limits:
            try:
                d = float(self.dash_val.get().replace(',', '.'))
                g = float(self.gap_val.get().replace(',', '.'))
                
                if style.base_type == 'dash_dot_dot': 
                    part = g/5.0; dash_pattern = [d, part, part, part, part, part]
                elif style.base_type == 'dash_dot': 
                    part = g/3.0; dash_pattern = [d, part, part, part]
                else: 
                    dash_pattern = [d, g]
            except ValueError: pass 

        w = self.preview_canvas.winfo_width(); w = 400 if w < 10 else w
        h = self.preview_canvas.winfo_height(); h = 100 if h < 10 else h
        cy = h / 2; x1, y1 = 20, cy; x2, y2 = w - 20, cy

        draw_complex = False; coords = []; smooth = False
        
        if style.base_type == 'wave':
            try:
                wave_amp = float(self.wave_amp_val.get().replace(',', '.'))
            except ValueError:
                wave_amp = getattr(style, 'wave_amplitude', None) or 3.0
            coords = self._generate_wave_coords(x1, y1, x2, y2, wave_amplitude=wave_amp)
            draw_complex = True; smooth = True
        elif style.base_type == 'zigzag':
            try:
                kinks = int(self.kinks_val.get())
            except ValueError:
                kinks = getattr(style, 'kinks_count', None) or 2
            coords = self._generate_zigzag_coords(x1, y1, x2, y2, kinks_count=kinks)
            draw_complex = True; smooth = False
        elif dash_pattern:
            segments = self._generate_dashed_coords(x1, y1, x2, y2, dash_pattern, self.px_ratio)
            for seg in segments: self.preview_canvas.create_line(seg[0], seg[1], seg[2], seg[3], width=width, fill='black', capstyle=tk.ROUND)
            return
        else: self.preview_canvas.create_line(x1, y1, x2, y2, width=width, fill='black', capstyle=tk.ROUND); return

        if draw_complex and len(coords) >= 4:
            self.preview_canvas.create_line(*coords, width=width, fill='black', capstyle=tk.ROUND, smooth=smooth)

    def apply_changes(self):
        try: self.state.base_thickness_mm = max(0.5, min(float(self.global_s_var.get().replace(',', '.')), 1.4))
        except ValueError: pass

        idx = self.style_listbox.curselection()
        if idx:
            key = self.style_keys[idx[0]]
            style = self.state.line_styles[key]
            
            if style.is_custom:
                new_name = self.name_var.get()
                if new_name: style.display_name = new_name
                style.is_main = self.is_main_var.get()
            
            if style.limits:
                try:
                    d = float(self.dash_val.get().replace(',', '.')); g = float(self.gap_val.get().replace(',', '.'))
                    min_d, max_d, min_g, max_g = style.limits
                    style.dash_pattern = (max(min_d, min(d, max_d)), max(min_g, min(g, max_g)))
                except ValueError: pass
            
            if style.base_type == 'zigzag':
                try:
                    kinks = int(self.kinks_val.get())
                    style.kinks_count = max(1, kinks)
                except ValueError: 
                    pass
            
            if style.base_type == 'wave':
                try:
                    amp = float(self.wave_amp_val.get().replace(',', '.'))
                    style.wave_amplitude = max(0.5, amp)
                except ValueError: 
                    pass

        self.on_update_callback()
        self.destroy()
