import tkinter as tk
from ui.main_window import MainWindow
from logic.state import AppState
from app.callbacks import Callbacks

class Application:
    def __init__(self):
        self.root = tk.Tk() # Инициализация Tkinter
        
        self.state = AppState() # Инициализация состояния приложения
        
        self.callbacks = Callbacks(self.root, self.state, None) # Создание обработчиков событий
        
        self.view = MainWindow(self.root, self.callbacks)   # Создание главного окна интерфейса
        
        self.callbacks.view = self.view # Связывание обработчиков событий и UI
        self.callbacks.initialize_view()

    def run(self):  # Запуска главного цикла
        self.root.mainloop()
