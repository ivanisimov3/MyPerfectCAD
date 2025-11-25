# ui/style_manager.py

'''
Модальное окно, которое будет открываться при нажатии на пункт меню. 
В этом окне можно выбрать любой стиль из базы и изменить его параметры.
'''

import tkinter as tk
from tkinter import ttk
import math

class StyleManagerWindow(tk.Toplevel):
    def __init__(self, parent, state, on_update_callback):
        super().__init__(parent)
        self.title("Менеджер стилей линий (ЕСКД)")
        self.geometry("750x580") # Чуть выше, чтобы все влезло
        
        self.state = state
        self.on_update_callback = on_update_callback
        
        self.preview_zoom = 2.0 
        self.px_ratio = self.state.mm_to_px_ratio * self.preview_zoom
        
        self.transient(parent)
        self.grab_set()

        # --- ВЕРХ: ОБЩИЕ НАСТРОЙКИ ---
        top_frame = ttk.LabelFrame(self, text="Общие настройки чертежа", padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Базовая толщина S (мм):").pack(side=tk.LEFT)
        
        self.global_s_var = tk.StringVar(value=str(state.base_thickness_mm))
        
        self.spin_s = ttk.Spinbox(top_frame, from_=0.5, to=1.4, increment=0.1, textvariable=self.global_s_var, width=6)
        self.spin_s.pack(side=tk.LEFT, padx=10)
        self.spin_s.bind("<KeyRelease>", self.update_preview)
        self.spin_s.bind("<<Increment>>", self.delayed_update)
        self.spin_s.bind("<<Decrement>>", self.delayed_update)

        # --- ЦЕНТР ---
        center_frame = ttk.Frame(self)
        center_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)

        # ЛЕВО: СПИСОК
        left_panel = ttk.Frame(center_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        ttk.Label(left_panel, text="Стили линий:").pack(anchor=tk.W)
        self.style_listbox = tk.Listbox(left_panel, width=30, height=15, exportselection=False)
        self.style_listbox.pack(fill=tk.Y, expand=True, pady=5)
        self.style_listbox.bind("<<ListboxSelect>>", self.on_style_select)
        
        # ПРАВО: РЕДАКТОР
        right_panel = ttk.LabelFrame(center_frame, text="Параметры выбранного стиля", padding="15")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 1. Название
        ttk.Label(right_panel, text="Название:").pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(right_panel, textvariable=self.name_var, state='readonly').pack(fill=tk.X, pady=(0, 10))

        # 2. Тип
        self.type_info_var = tk.StringVar()
        ttk.Label(right_panel, textvariable=self.type_info_var, foreground="gray").pack(anchor=tk.W, pady=(0, 5))

        # 3. Превью (Теперь оно ВЫШЕ настроек штриха)
        ttk.Label(right_panel, text=f"Предпросмотр (Масштаб {int(self.preview_zoom*100)}%):").pack(anchor=tk.W, pady=(15, 5))
        self.preview_canvas = tk.Canvas(right_panel, height=100, bg="white", relief="sunken", borderwidth=1)
        self.preview_canvas.pack(fill=tk.X, pady=0)
        
        # ВАЖНО: Привязываем перерисовку к изменению размера канваса.
        # Это исправляет баг "короткой линии" при первом открытии.
        self.preview_canvas.bind("<Configure>", self.update_preview)

        # 4. Настройки пунктира (Теперь СНИЗУ)
        self.dash_frame = ttk.LabelFrame(right_panel, text="Параметры штриховки (мм)", padding=10)
        # Мы не пакуем его здесь, это делает on_style_select
        
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

        # --- НИЗ: КНОПКИ ---
        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(btn_frame, text="Закрыть", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="Применить", command=self.apply_changes).pack(side=tk.RIGHT, padx=10)

        # Загрузка данных
        self.style_keys = []
        for key, style in self.state.line_styles.items():
            self.style_listbox.insert(tk.END, style.display_name)
            self.style_keys.append(key)

        try:
            current_idx = self.style_keys.index(state.current_style_name)
            self.style_listbox.selection_set(current_idx)
            self.on_style_select(None)
        except ValueError:
            self.style_listbox.selection_set(0)
            self.on_style_select(None)

    def delayed_update(self, event=None):
        self.after(10, self.update_preview)

    def on_style_select(self, event):
        idx = self.style_listbox.curselection()
        if not idx: return
        
        key = self.style_keys[idx[0]]
        style = self.state.line_styles[key]
        
        self.name_var.set(style.display_name)
        
        if style.is_main:
            self.type_info_var.set("Тип: Основная (S)")
        else:
            self.type_info_var.set("Тип: Тонкая (S/2)")
        
        if style.limits: 
            # ПАКУЕМ СНИЗУ (после превью)
            self.dash_frame.pack(fill=tk.X, pady=15, side=tk.TOP)
            
            min_d, max_d, min_g, max_g = style.limits
            self.spin_dash.config(from_=min_d, to=max_d, state='normal')
            self.spin_gap.config(from_=min_g, to=max_g, state='normal')
            
            if style.dash_pattern:
                self.dash_val.set(str(style.dash_pattern[0]))
                self.gap_val.set(str(style.dash_pattern[1]))
        else:
            self.dash_frame.pack_forget() 
        
        self.update_preview()

    # --- ГЕНЕРАТОРЫ ---
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

    def _generate_wave_coords(self, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0: return [x1, y1, x2, y2]
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        points = []
        
        step = 5 * (self.preview_zoom)
        amplitude = 3 * (self.preview_zoom)
        freq = 0.2 / (self.preview_zoom)
        
        if step < 0.1: step = 0.1
        
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
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        points = [x1, y1]
        
        period = 40 * self.preview_zoom
        kink_len = 12 * self.preview_zoom
        amplitude = 5 * self.preview_zoom
        
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

        try:
            val_str = self.global_s_var.get().replace(',', '.')
            s_mm = float(val_str)
        except ValueError:
            s_mm = self.state.base_thickness_mm

        s_px = s_mm * self.px_ratio
        if style.is_main:
            width = max(1, int(s_px))
        else:
            width = max(1, int(s_px / 2))

        dash_pattern = None
        if style.limits:
            try:
                d_str = self.dash_val.get().replace(',', '.')
                g_str = self.gap_val.get().replace(',', '.')
                d = float(d_str)
                g = float(g_str)
                
                if style.name == 'dash_dot_dot':
                    part = g / 5.0
                    dash_pattern = [d, part, part, part, part, part]
                elif style.name.startswith('dash_dot_'):
                    part = g / 3.0
                    dash_pattern = [d, part, part, part]
                else:
                    dash_pattern = [d, g]
            except ValueError:
                pass 

        # ДИНАМИЧЕСКАЯ ШИРИНА:
        # winfo_width() возвращает реальную ширину. Если окно не отрисовано, может вернуть 1.
        # Поэтому мы биндимся на <Configure>, чтобы перерисовать, когда ширина станет нормальной.
        w = self.preview_canvas.winfo_width()
        if w < 10: w = 400 # Фолбэк для самого первого кадра
        
        h = self.preview_canvas.winfo_height()
        if h < 10: h = 100
        cy = h / 2
        
        x1, y1 = 20, cy
        x2, y2 = w - 20, cy

        draw_complex = False
        coords = []
        smooth = False

        if style.name == 'solid_wave':
            coords = self._generate_wave_coords(x1, y1, x2, y2)
            draw_complex = True
            smooth = True
        elif style.name == 'solid_zigzag':
            coords = self._generate_zigzag_coords(x1, y1, x2, y2)
            draw_complex = True
            smooth = False
        elif dash_pattern:
            segments = self._generate_dashed_coords(x1, y1, x2, y2, dash_pattern, self.px_ratio)
            for seg in segments:
                self.preview_canvas.create_line(seg[0], seg[1], seg[2], seg[3], width=width, fill='black', capstyle=tk.ROUND)
            return
        else:
            self.preview_canvas.create_line(x1, y1, x2, y2, width=width, fill='black', capstyle=tk.ROUND)
            return

        if draw_complex and len(coords) >= 4:
            self.preview_canvas.create_line(*coords, width=width, fill='black', capstyle=tk.ROUND, smooth=smooth)

    def apply_changes(self):
        try:
            new_s = float(self.global_s_var.get().replace(',', '.'))
            new_s = max(0.5, min(new_s, 1.4))
            self.state.base_thickness_mm = new_s
        except ValueError: pass

        idx = self.style_listbox.curselection()
        if idx:
            key = self.style_keys[idx[0]]
            style = self.state.line_styles[key]
            
            if style.limits:
                try:
                    d = float(self.dash_val.get().replace(',', '.'))
                    g = float(self.gap_val.get().replace(',', '.'))
                    min_d, max_d, min_g, max_g = style.limits
                    
                    new_dash = max(min_d, min(d, max_d))
                    new_gap = max(min_g, min(g, max_g))
                    
                    style.dash_pattern = (new_dash, new_gap)
                except ValueError: pass

        self.on_update_callback()
        self.destroy()