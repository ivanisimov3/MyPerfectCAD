# Сердце нашего приложения. Здесь мы будем собирать все части интерфейса вместе.
# app/application.py

import tkinter as tk
from ui.main_window import MainWindow

class Application:
    def __init__(self):
        """
        Конструктор класса приложения.
        Создает главное окно и инициализирует интерфейс.
        """
        # Создаем основной объект окна. Это стандартная практика в Tkinter.
        self.root = tk.Tk()
        
        # Создаем экземпляр нашего интерфейса, передавая ему главное окно
        self.main_window = MainWindow(self.root)

    def run(self):
        """
        Запускает главный цикл приложения.
        Это 'while(true)', который ждет действий пользователя (клики, ввод).
        """
        self.root.mainloop()