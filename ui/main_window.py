# Здесь мы "спроектируем" наше окно: создадим рабочую область, панели инструментов и т.д.
# ui/main_window.py

import tkinter as tk
from tkinter import ttk

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
        root.columnconfigure(1, weight=0) # Фиксированная ширина для панелей
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

        # 2. Рабочая область (слева, основная часть)
        # Это будет наш холст для рисования
        canvas_frame = ttk.Frame(root, borderwidth=2, relief="sunken")
        canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
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