import tkinter as tk
from ui.main_window import MainWindow
from logic.state import AppState
from app.callbacks import Callbacks

class Application:
    def __init__(self):
        self.root = tk.Tk()
        
        self.state = AppState()
        
        self.callbacks = Callbacks(self.root, self.state, None)
        
        self.view = MainWindow(self.root, self.callbacks)
        
        self.callbacks.view = self.view

        self.callbacks.initialize_view()

    def run(self):
        self.root.mainloop()
