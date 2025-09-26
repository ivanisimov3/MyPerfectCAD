# Здесь мы "спроектируем" наше окно: создадим рабочую область, панели инструментов и т.д.
# ui/main_window.py

import tkinter as tk
from tkinter import ttk
import math

class MainWindow:
    def __init__(self, root):
        """
        Инициализирует главное окно приложения с новой компоновкой.
        """
        # Настраиваем заголовок и минимальный размер окна
        root.title("MyPerfectCAD: ЛР №1")
        root.minsize(800, 600)

        # Конфигурируем сетку основного окна. У нас будет 3 строки и 2 столбца.
        # столбец 0 (рабочая область) будет растягиваться, столбец 1 (настройки) - нет
        root.columnconfigure(0, weight=1) 
        # строка 1 (рабочая область) будет растягиваться
        root.rowconfigure(1, weight=1)

        # 1. Панель инструментов (сверху)
        # columnspan=2 означает, что этот виджет займет 2 столбца
        # sticky=(tk.W, tk.E) растягиваться по горизонтали
        toolbar = ttk.LabelFrame(root, text="Инструменты", padding="5")
        toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        # Добавим кнопки горизонтально с помощью pack внутри фрейма toolbar
        ttk.Button(toolbar, text="Отрезок").pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Button(toolbar, text="Удалить").pack(side=tk.LEFT, padx=5, pady=2)

        # 2. Рабочая область -> ЗАМЕНЯЕМ Frame на Canvas
        # bg='white' устанавливает белый цвет фона
        self.canvas = tk.Canvas(root, bg='white', borderwidth=2, relief="sunken")
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, 'S'), padx=5, pady=5)
        
        # 3. Панель настроек (справа)
        # rowspan=1, но можно было бы и 2, если бы она занимала место и инфо-панели
        settings_panel = ttk.LabelFrame(root, text="Настройки", padding="5")
        settings_panel.grid(row=1, column=1, sticky=(tk.E, tk.N, tk.S), padx=5, pady=5)
        ttk.Label(settings_panel, text="Шаг сетки:").pack(pady=2)

        # 4. Информационная панель (снизу)
        info_panel = ttk.LabelFrame(root, text="Информация", padding="5")
        info_panel.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        ttk.Label(info_panel, text="Длина: N/A").pack(side=tk.LEFT, padx=5, pady=2)
        ttk.Label(info_panel, text="Угол: N/A").pack(side=tk.LEFT, padx=5, pady=2)

        # === НОВАЯ ЛОГИКА КАМЕРЫ И СОБЫТИЙ ===

        # 1. Состояние "камеры" (нашего вида)
        self.pan_x = 0
        self.pan_y = 0
        self.zoom = 1.0  # Пока не используем, но задел на будущее

        # 2. Переменные для отслеживания перемещения мыши
        self._drag_start_x = 0
        self._drag_start_y = 0

        # 3. Привязка событий
        self.canvas.bind("<Configure>", self.on_canvas_resize)  # Событие изменения размера
        self.canvas.bind("<ButtonPress-2>", self.on_mouse_press) # Нажатие средней кнопки мыши (колесика)
        self.canvas.bind("<B2-Motion>", self.on_mouse_drag)     # Движение с зажатой средней кнопкой

    def world_to_screen(self, world_x, world_y):
        """Преобразует мировые координаты в экранные."""
        # Центр экрана - это временное начало отсчета
        center_x = self.canvas.winfo_width() / 2
        center_y = self.canvas.winfo_height() / 2
        
        screen_x = center_x + world_x + self.pan_x
        # Y инвертирован, т.к. в экранных координатах Y растет вниз
        screen_y = center_y - world_y + self.pan_y
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x, screen_y):
        """Преобразует экранные координаты в мировые."""
        center_x = self.canvas.winfo_width() / 2
        center_y = self.canvas.winfo_height() / 2

        world_x = screen_x - center_x - self.pan_x
        world_y = -(screen_y - center_y - self.pan_y)
        return world_x, world_y
    
    def redraw_all(self):
        """Полностью перерисовывает холст."""
        self.canvas.delete("all")  # Очищаем холст
        self.draw_grid_and_axes()
        # В будущем здесь будет и отрисовка всех фигур

    def draw_grid_and_axes(self, grid_step=50):
        """Рисует сетку и оси координат на холсте."""
        # Получаем текущие размеры холста
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Определяем видимую область в мировых координатах
        world_top_left_x, world_top_left_y = self.screen_to_world(0, 0)
        world_bottom_right_x, world_bottom_right_y = self.screen_to_world(width, height)

        # Рисуем ВЕРТИКАЛЬНЫЕ линии сетки (и ось Y)
        start_x = math.ceil(world_top_left_x / grid_step) * grid_step
        for world_x in range(start_x, int(world_bottom_right_x), grid_step):
            screen_x, _ = self.world_to_screen(world_x, 0)
            
            line_color = 'black' if world_x == 0 else '#e0e0e0'
            line_width = 2 if world_x == 0 else 1
            
            self.canvas.create_line(screen_x, 0, screen_x, height, fill=line_color, width=line_width)

        # Рисуем ГОРИЗОНТАЛЬНЫЕ линии сетки (и ось X)
        start_y = math.ceil(world_bottom_right_y / grid_step) * grid_step
        for world_y in range(start_y, int(world_top_left_y), grid_step):
            _, screen_y = self.world_to_screen(0, world_y)
            
            line_color = 'black' if world_y == 0 else '#e0e0e0'
            line_width = 2 if world_y == 0 else 1

            self.canvas.create_line(0, screen_y, width, screen_y, fill=line_color, width=line_width)

    # --- Обработчики событий ---

    def on_canvas_resize(self, event):
        """Вызывается при изменении размера холста."""
        self.redraw_all()

    def on_mouse_press(self, event):
        """Вызывается при нажатии средней кнопки мыши."""
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def on_mouse_drag(self, event):
        """Вызывается при перемещении мыши с зажатой средней кнопкой."""
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y

        # Обновляем смещение
        self.pan_x += dx
        self.pan_y += dy

        # Сохраняем новую стартовую позицию для следующего события
        self._drag_start_x = event.x
        self._drag_start_y = event.y

        self.redraw_all()