# app/callbacks.py

'''
Этот файл решает, что делать, если пользователь нажал кнопку мыши, покрутил колесико или нажал "Enter". 
Он меняет данные в state и дает команду renderer перерисовать экран. 
Он связывает кнопки из main_window с действиями.
'''

import tkinter as tk
from tkinter import messagebox, colorchooser
import math
from logic.geometry import Point, Segment
from logic.converter import CoordinateConverter
from ui.renderer import Renderer
from logic.styles import GOST_STYLES

class Callbacks:
    def __init__(self, root, state, view):
        self.root = root
        self.state = state
        self.view = view
        
        # Ссылки на вспомогательные модули
        self.converter = None
        self.renderer = None
        
        # Переменные для логики перетаскивания холста
        self._drag_start_x = 0
        self._drag_start_y = 0

    # Инициализирует вспомогательные контроллеры (конвертер, рендерер) и применяет стартовые настройки цветов
    def initialize_view(self):
        self.converter = CoordinateConverter(self.state, self.view.canvas)
        self.renderer = Renderer(self.view.canvas, self.state, self.converter)
        
        self.view.canvas.config(background=self.state.bg_color)
        self.view.bg_swatch.config(background=self.state.bg_color)
        self.view.grid_swatch.config(background=self.state.grid_color)
        self.view.segment_swatch.config(background=self.state.current_color)
        
        self.set_app_state(self.state.app_mode)

    # Управляет машиной состояний приложения, переключая интерфейс между режимом ожидания, создания, панорамирования
    def set_app_state(self, mode):
        self.state.app_mode = mode
        is_creating = (mode == 'CREATING_SEGMENT')
        is_panning = (mode == 'PANNING')
        
        # Управление доступностью полей ввода
        entry_state = 'normal' if is_creating else 'disabled'
        entries = [self.view.p1_x_entry, self.view.p1_y_entry, self.view.p2_x_entry, self.view.p2_y_entry]
        
        # Сбрасываем старые бинды ЛКМ и курсор
        self.view.canvas.unbind("<Button-1>")
        self.view.canvas.unbind("<B1-Motion>")
        self.view.canvas.unbind("<ButtonRelease-1>")
        self.view.canvas.config(cursor="") # Cтандартный курсор
        self.root.unbind("<Return>")
        
        # Очищаем поля, если мы не создаем отрезок
        if not is_creating:
            for entry in entries:
                entry.delete(0, tk.END)
                entry.config(state=entry_state)
            self.state.preview_segment = None
            self.state.active_p1 = None
            self.state.active_p2 = None

        if is_creating or is_panning:
            self.view.hotkey_frame.pack(side=tk.RIGHT, padx=5)
            self.view.lbl_esc.pack(side=tk.LEFT, padx=5)
            
            if is_creating:
                self.view.lbl_enter.pack(side=tk.LEFT, padx=5)
            else:
                self.view.lbl_enter.pack_forget()
        else:
            self.view.hotkey_frame.pack_forget()

        # ЛОГИКА ДЛЯ РЕЖИМОВ
        if is_creating:
            for entry in entries: entry.config(state=entry_state)
            self.state.points_clicked = 0
            self.root.bind("<Return>", self.finalize_segment)
            self.view.canvas.bind("<Button-1>", self.on_lmb_click)
            self.view.canvas.config(cursor="crosshair") # Курсор-прицел 
            
        elif is_panning:
            # В режиме "Рука" ЛКМ работает так же, как СКМ
            self.view.canvas.bind("<Button-1>", self.on_mouse_press)
            self.view.canvas.bind("<B1-Motion>", self.on_mouse_drag)
            self.view.canvas.config(cursor="fleur") # Курсор перемещения

        else:
            self.view.canvas.bind("<Button-1>", self.on_selection_click)
            self.view.canvas.config(cursor="arrow") # Обычная стрелка
        
        self.redraw_all()

    # ### НОВОЕ: Обработка клика для выделения
    def on_selection_click(self, event):
        # 1. Получаем мировые координаты клика
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        
        # 2. Ищем ближайший отрезок
        # Порог чувствительности (сколько пикселей от мыши до линии считается попаданием)
        hit_threshold_pixels = 8 
        # Переводим порог в мировые единицы (делим на зум), чтобы точность была одинаковой при любом приближении
        hit_threshold_world = hit_threshold_pixels / self.state.zoom
        
        found_segment = None
        # Проходим по всем сегментам и ищем тот, до которого расстояние меньше порога
        for segment in self.state.segments:
            dist = segment.distance_to_point(wx, wy)
            if dist < hit_threshold_world:
                found_segment = segment
                # Можно прервать поиск на первом найденном (или искать самый близкий, если их несколько)
                break 
        
        # 3. Обновляем выделение
        if found_segment:
            # Если попали в линию -> Выделяем ТОЛЬКО её (для множественного нужен Ctrl)
            self.state.selected_segments = [found_segment]
            
            # --- СИНХРОНИЗАЦИЯ ИНТЕРФЕЙСА ---
            # Когда выделили линию, нужно, чтобы в панели "Стиль" показался её текущий стиль
            style_obj = self.state.line_styles.get(found_segment.style_name)
            if style_obj:
                self.view.style_combobox.set(style_obj.display_name)
                # Обновляем и цвет в панели (если надо)
                self.view.segment_swatch.config(bg=found_segment.color)
                self.state.current_color = found_segment.color
                self.state.current_style_name = found_segment.style_name
                
        else:
            # Если кликнули в пустоту -> Снимаем выделение
            self.state.selected_segments = []
            
        self.redraw_all()

    # Активирует режим создания нового отрезка при нажатии кнопки на панели инструментов
    def on_new_segment_mode(self, event=None):
        self.set_app_state('CREATING_SEGMENT')
        self.view.p1_x_entry.focus_set()

    # Активирует режим "Рука"
    def on_hand_mode(self, event=None):
        self.set_app_state('PANNING')
        self.view.canvas.focus_set()

    # Динамически обновляет временный отрезок (превью) при вводе координат или движении мыши
    def update_preview_segment(self, event=None):
        try:
            p1, p2 = self._create_points_from_entries()
            self.state.preview_segment = Segment(
                p1, p2, 
                style_name=self.state.current_style_name,
                color=self.state.current_color
            )
        except (ValueError, tk.TclError):
            self.state.preview_segment = None
        self.redraw_all()

    # Завершает построение отрезка, сохраняя его в список готовых объектов
    def finalize_segment(self, event=None):
        if self.state.preview_segment:
            final_segment = Segment(
                self.state.preview_segment.p1, 
                self.state.preview_segment.p2, 
                style_name=self.state.current_style_name, # Берем текущий стиль
                color=self.state.current_color
            )
            self.state.segments.append(final_segment)
            self.set_app_state('IDLE')

    # Обрабатывает нажатие клавиши ESC (отмена построения, панорамирования или выход из программы)
    def on_escape_key(self, event=None):
        # Если мы что-то создаем ИЛИ панорамируем — выходим в режим ожидания
        if self.state.app_mode in ['CREATING_SEGMENT', 'PANNING']: 
            self.set_app_state('IDLE')
        elif self.state.app_mode == 'IDLE' and messagebox.askyesno("Выход", "Выйти из программы?"): 
            self.root.destroy()

    # Удаляет последний построенный отрезок
    def on_delete_segment(self, event=None):
        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                if seg in self.state.segments:
                    self.state.segments.remove(seg)
            self.state.selected_segments = [] # Очищаем список выделения
        elif self.state.segments:
            self.state.segments.pop()
        self.redraw_all()

    # Применяет настройки шага сетки из панели настроек
    def on_apply_settings(self):
        try:
            new_step = int(self.view.grid_step_var.get())
            if new_step <= 0: raise ValueError
            self.state.grid_step = new_step
            self.redraw_all()
        except ValueError: messagebox.showerror("Ошибка", "Шаг сетки должен быть > 0")

    # Обрабатывает переключение системы координат (Декартова/Полярная), пересчитывая значения в полях ввода
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
            if new_system == 'cartesian': # Переход ИЗ полярной В декартову
                angle = math.radians(val2) if self.view.angle_units.get() == 'degrees' else val2
                p2.x = p1_x + val1 * math.cos(angle)
                p2.y = p1_y + val1 * math.sin(angle)
            else: # Переход ИЗ декартовой В полярную
                p2 = Point(val1, val2)
        except (ValueError, tk.TclError): return
        
        self._update_p2_entries(p2)
        self.redraw_all()

    # Обрабатывает клик левой кнопкой мыши: задает первую или вторую точку построения
    def on_lmb_click(self, event):
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        if self.state.points_clicked == 0:
            self._update_p1_entries(wx, wy)
            self.state.points_clicked = 1
        elif self.state.points_clicked == 1:
            self._update_p2_entries(Point(wx, wy))
            self.state.points_clicked = 2
        self.update_preview_segment()

    # Обрабатывает клик правой кнопкой мыши: сбрасывает текущую точку
    def on_rmb_click(self, event):
        if self.view.p2_x_entry.get(): 
            self.view.p2_x_entry.delete(0, tk.END); self.view.p2_y_entry.delete(0, tk.END)
            self.state.points_clicked = 1
        elif self.view.p1_x_entry.get():
            self.view.p1_x_entry.delete(0, tk.END); self.view.p1_y_entry.delete(0, tk.END)
            self.state.points_clicked = 0
        self.update_preview_segment()

    # Запоминает позицию мыши для начала панорамирования
    def on_mouse_press(self, event):
        self._drag_start_x, self._drag_start_y = event.x, event.y

    # Осуществляет панорамирование (сдвиг) холста при движении мыши с зажатым колесиком
    def on_mouse_drag(self, event):
        dx, dy = event.x - self._drag_start_x, event.y - self._drag_start_y
        self.state.pan_x += dx; self.state.pan_y += dy
        self._drag_start_x, self._drag_start_y = event.x, event.y
        self.redraw_all()

    # Универсальный внутренний метод для применения зума относительно конкретной точки экрана
    def _perform_zoom(self, factor, center_screen_x, center_screen_y):
        # Запоминаем, какая мировая координата была под курсором ДО зума
        wx, wy = self.converter.screen_to_world(center_screen_x, center_screen_y)
        
        # Применяем зум 
        self.state.zoom = max(0.1, min(self.state.zoom * factor, 1000.0))
        
        # Вычисляем, где эта мировая точка оказалась бы на экране ПОСЛЕ зума, если бы мы не двигали камеру
        sx_new, sy_new = self.converter.world_to_screen(wx, wy)
        
        # Корректируем смещение, чтобы вернуть точку под курсор
        self.state.pan_x += center_screen_x - sx_new
        self.state.pan_y += center_screen_y - sy_new
        
        self.redraw_all()

    # Обработка колесика мыши (Зуммируем к позиции курсора)
    def on_mouse_wheel(self, event):
        factor = 1.2 if (hasattr(event, 'delta') and event.delta > 0) or event.num == 4 else 1/1.2
        self._perform_zoom(factor, event.x, event.y)

    # Зум Плюс (к центру экрана)
    def on_zoom_in(self, event=None):
        cx, cy = self.view.canvas.winfo_width() / 2, self.view.canvas.winfo_height() / 2
        self._perform_zoom(1.2, cx, cy)
        self.view.canvas.focus_set()

    # Зум Минус (от центра экрана)
    def on_zoom_out(self, event=None):
        cx, cy = self.view.canvas.winfo_width() / 2, self.view.canvas.winfo_height() / 2
        self._perform_zoom(1/1.2, cx, cy)
        self.view.canvas.focus_set()

    # Вписать чертеж в экран
    def on_fit_to_view(self, event=None):
        if not self.state.segments:
            # Если пусто, сбрасываем в дефолт
            self.state.pan_x, self.state.pan_y = 0, 0
            self.state.zoom = 10.0
            self.redraw_all()
            self.view.canvas.focus_set()
            return

        # Ищем границы (Bounding Box) всех отрезков
        xs = [s.p1.x for s in self.state.segments] + [s.p2.x for s in self.state.segments]
        ys = [s.p1.y for s in self.state.segments] + [s.p2.y for s in self.state.segments]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        # Размеры сцены и центральная точка
        world_w = max_x - min_x
        world_h = max_y - min_y
        center_wx = (min_x + max_x) / 2
        center_wy = (min_y + max_y) / 2
        
        # Размеры экрана (с отступом 10% чтобы не прилипало к краям)
        screen_w = self.view.canvas.winfo_width() * 0.9
        screen_h = self.view.canvas.winfo_height() * 0.9
        
        # Вычисляем нужный зум (берем минимальный, чтобы влезло и по ширине, и по высоте)
        if world_w == 0: world_w = 1
        if world_h == 0: world_h = 1
        
        scale_x = screen_w / world_w
        scale_y = screen_h / world_h
        self.state.zoom = min(scale_x, scale_y)
        
        # Центрируем камеру: Pan должен компенсировать координаты центра сцены
        # Формула выводится из уравнения: screen_center = canvas_center + pan + world_center * zoom
        # Нам нужно, чтобы screen_center совпадал с canvas_center.
        # 0 = pan + world * zoom  =>  pan = -world * zoom
        self.state.pan_x = -center_wx * self.state.zoom
        self.state.pan_y = center_wy * self.state.zoom 
        
        self.redraw_all()
        self.view.canvas.focus_set()

    def rotate_view(self, angle_delta_deg, event=None):
        # Проверяем, зажат ли Shift
        # В Tkinter event.state содержит маску модификаторов. 1 - это Shift (бит 0x0001).
        is_shift = False
        if event and (event.state & 0x0001): 
            is_shift = True
            
        if is_shift:
            # Логика Shift: Шаг 90 градусов
            current_deg = math.degrees(self.state.rotation)
            # Округляем текущий угол до кратного 90
            snapped_deg = round(current_deg / 90) * 90
            
            # Если мы уже на 90, сразу шагаем к следующему.
            # Если мы были на 45, snapped станет 0 (или 90), и мы выровняемся.
            if abs(snapped_deg - current_deg) < 1.0:
                target_deg = snapped_deg + (90 if angle_delta_deg > 0 else -90)
            else:
                # Если угол был "кривой" (например, 13 градусов), Shift сначала выровняет его
                target_deg = snapped_deg
                
            self.state.rotation = math.radians(target_deg)
        else:
            # Плавный поворот
            self.state.rotation += math.radians(angle_delta_deg)
            
        self.redraw_all()
        self.view.canvas.focus_set() # Сброс фокуса

    def on_rotate_left(self, event=None):
        self.rotate_view(1, event) # Против часовой

    def on_rotate_right(self, event=None):
        self.rotate_view(-1, event) # По часовой

    # Перерисовывает сцену при изменении размеров окна
    def on_canvas_resize(self, event): self.redraw_all()
    
    # Переключает полноэкранный режим по клавише F11
    def toggle_fullscreen(self, event=None):
        self.state.is_fullscreen = not self.state.is_fullscreen
        self.root.attributes("-fullscreen", self.state.is_fullscreen)

    # Открывает диалог выбора цвета фона
    def on_choose_bg_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.bg_color)
        if c: 
            self.state.bg_color = c
            self.view.canvas.config(bg=c); self.view.bg_swatch.config(bg=c)

    # Открывает диалог выбора цвета сетки
    def on_choose_grid_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.grid_color)
        if c: self.state.grid_color = c; self.view.grid_swatch.config(bg=c); self.redraw_all()

    # Открывает диалог выбора цвета отрезков
    def on_choose_segment_color(self):
        _, c = colorchooser.askcolor(initialcolor=self.state.current_color)
        if c: 
            self.state.current_color = c
            self.view.segment_swatch.config(bg=c)
            # Если что-то выделено, перекрашиваем!
            for seg in self.state.selected_segments:
                seg.color = c
            self.redraw_all()

    # Считывает данные из полей ввода и возвращает объекты точек P1 и P2, учитывая выбранную систему координат
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

    # Вспомогательный метод для обновления значений в полях ввода точки P1
    def _update_p1_entries(self, x, y):
        self.view.p1_x_entry.delete(0, tk.END); self.view.p1_x_entry.insert(0, f"{x:.2f}")
        self.view.p1_y_entry.delete(0, tk.END); self.view.p1_y_entry.insert(0, f"{y:.2f}")

    # Вспомогательный метод для обновления значений в полях ввода точки P2 (с конвертацией в полярные при необходимости)
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

    def on_style_selected(self, event=None):
        display_name = self.view.style_combobox.get()
        # 1. Находим id стиля
        new_style_name = 'solid_main'
        for key, style in self.state.line_styles.items():
            if style.display_name == display_name:
                new_style_name = key
                break
        
        # 2. Обновляем текущее состояние (для будущих линий)
        self.state.current_style_name = new_style_name
        
        # 3. Если есть ВЫДЕЛЕННЫЕ объекты, меняем стиль им
        if self.state.selected_segments:
            for seg in self.state.selected_segments:
                seg.style_name = new_style_name
                
        # 4. Обновляем превью
        self.update_preview_segment()
        self.redraw_all()

    def on_thickness_changed(self):
        try:
            # Получаем значение из Spinbox
            val = int(self.view.thickness_var.get())
            if val < 1: val = 1
            self.state.base_thickness_s = val
            self.redraw_all() # Перерисовываем всё, так как толщина S глобальна
        except ValueError:
            pass # Если ввели не число, игнорируем

    # Главный метод отрисовки: обновляет инфо-панель и делегирует рисование графики рендереру
    def redraw_all(self):
        self.update_info_panel()
        self.update_status_bar()
        if self.renderer:
            self.renderer.render_scene()
    
    # Вычисляет и обновляет текстовую информацию на нижней панели (длина, угол, координаты)
    def update_info_panel(self):
        self.state.active_p1, self.state.active_p2 = None, None

        if self.state.selected_segments:
            seg = self.state.selected_segments[0]
            self.state.active_p1, self.state.active_p2 = seg.p1, seg.p2
            self.view.p1_coord_var.set(f"P1({seg.p1.x:.2f}, {seg.p1.y:.2f})")
            self.view.p2_coord_var.set(f"P2({seg.p2.x:.2f}, {seg.p2.y:.2f})")
            self.view.length_var.set(f"Длина: {seg.length:.2f}")
            return
        
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

    def on_reset_view(self, event=None):
        self.state.pan_x = 0
        self.state.pan_y = 0
        self.state.zoom = 10.0 # Возвращаем исходный зум
        self.state.rotation = 0.0
        self.redraw_all()
        self.view.canvas.focus_set()

    def on_mouse_move_stats(self, event):
        # Переводим экранные координаты в мировые
        wx, wy = self.converter.screen_to_world(event.x, event.y)
        self.view.status_coords.config(text=f"X: {wx:.2f}  Y: {wy:.2f}")

    # Обновляет остальные поля статус-бара (вызывать внутри redraw_all)
    def update_status_bar(self):
        # 1. Масштаб (в процентах, считаем 10.0 за 100%)
        zoom_pct = int((self.state.zoom / 10.0) * 100)
        self.view.status_zoom.config(text=f"Zoom: {zoom_pct}%")
        
        # 2. Угол
        deg = math.degrees(self.state.rotation)
        self.view.status_angle.config(text=f"Angle: {deg:.1f}°")
        
        # 3. Режим
        if self.state.selected_segments:
             mode_text = f"Выбрано объектов: {len(self.state.selected_segments)}"
        else:
            modes = {'IDLE': "Ожидание", 'CREATING_SEGMENT': "Создание отрезка", 'PANNING': "Панорамирование"}
            mode_text = modes.get(self.state.app_mode, self.state.app_mode)
        
        self.view.status_mode.config(text=f"Режим: {mode_text}")

    def show_context_menu(self, event):
        # Меню показываем только если мы НЕ рисуем отрезок
        if self.state.app_mode != 'CREATING_SEGMENT':
            self.view.context_menu.post(event.x_root, event.y_root)
        else:
            # Если мы рисуем, то ПКМ должна работать как on_rmb_click (отмена точки)
            # Вызываем его вручную
            self.on_rmb_click(event)