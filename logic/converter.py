# logic/converter.py

class CoordinateConverter:
    def __init__(self, state, canvas):
        self.state = state
        self.canvas = canvas

    # Из мировых в экранные
    def world_to_screen(self, world_x, world_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        return (cx + self.state.pan_x + (world_x * self.state.zoom), 
                cy + self.state.pan_y - (world_y * self.state.zoom))

    # Из экранных в мировые
    def screen_to_world(self, screen_x, screen_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        return ((screen_x - cx - self.state.pan_x) / self.state.zoom, 
                -(screen_y - cy - self.state.pan_y) / self.state.zoom)