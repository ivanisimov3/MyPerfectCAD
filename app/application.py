# app/application.py

'''
Этот файл: точка сборки. Он не содержит сложной логики, его задача - 
создать три главных компонента (Модель, Вид, Контроллер) и познакомить их друг с другом.
'''

import tkinter as tk
from ui.main_window import MainWindow
from logic.state import AppState
from app.callbacks import Callbacks

class Application:
    def __init__(self):
        # Создаем корневое окно Tkinter (фундамент приложения)
        self.root = tk.Tk()
        
        # Создаем состояние. Здесь будут храниться все настройки и список линий.
        self.state = AppState()
        
        # Создаем обработчик событий. Ему нужен доступ к данным (state), 
        # чтобы их менять. Ссылку на View пока ставим None (оно еще не создано).
        self.callbacks = Callbacks(self.root, self.state, None)
        
        # Создаем главное окно. Ему нужен контроллер (callbacks), 
        # чтобы привязывать кнопки к функциям.
        self.view = MainWindow(self.root, self.callbacks)
        
        # Теперь, когда окно создано, отдаем ссылку на него контроллеру.
        # Теперь контроллер может управлять отрисовкой.
        self.callbacks.view = self.view

        # Первичная настройка экрана (применить цвета, сетку и т.д.)
        self.callbacks.initialize_view()

    #Запускает главный цикл обработки событий Windows/Linux.
    def run(self):
        self.root.mainloop()