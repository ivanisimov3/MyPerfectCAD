# Сердце нашего приложения. Здесь мы будем собирать все части интерфейса вместе.

# app/application.py
import tkinter as tk
from ui.main_window import MainWindow

class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.main_window = MainWindow(self.root)
    def run(self):
        self.root.mainloop()