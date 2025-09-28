# app/application.py

import tkinter as tk
from ui.main_window import MainWindow
import sv_ttk

class Application:
    def __init__(self):
        """
        Конструктор класса приложения.
        Создает главное окно и инициализирует интерфейс.
        """
        self.root = tk.Tk()
        
        # Устанавливаем тему ПЕРЕД созданием главного окна
        sv_ttk.set_theme("dark")
        
        self.main_window = MainWindow(self.root)

    def run(self):
        """
        Запускает главный цикл приложения.
        """
        self.root.mainloop()