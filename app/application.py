# app/application.py

'''
Создает экземпляры всех главных классов (AppState, MainWindow, Callbacks) и связывает их друг с другом (Dependency Injection). 
Гарантирует, что у Контроллера есть доступ к Виду, а у Вида — к Контроллеру.
'''

import tkinter as tk
from ui.main_window import MainWindow
from logic.state import AppState
from app.callbacks import Callbacks

class Application:
    def __init__(self):
        self.root = tk.Tk()
        
        # 1. Создаем Model (Состояние)
        self.state = AppState()
        
        # 2. Создаем Controller (Обработчики) и передаем ему доступ к root и state
        self.callbacks = Callbacks(self.root, self.state, None)
        
        # 3. Создаем View (Окно) и передаем ему доступ к root и callbacks
        self.view = MainWindow(self.root, self.callbacks)
        
        # 4. Завершаем связку: даем Controller'у доступ к View
        self.callbacks.view = self.view

        # 5. Даем команду контроллеру инициализировать виджеты начальными данными
        self.callbacks.initialize_view()

    def run(self):
        self.root.mainloop()