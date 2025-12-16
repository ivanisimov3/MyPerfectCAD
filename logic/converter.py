import math

class CoordinateConverter:
    def __init__(self, state, canvas):
        self.state = state
        self.canvas = canvas

    def world_to_screen(self, world_x, world_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        
        angle = self.state.rotation
        rx = world_x * math.cos(angle) - world_y * math.sin(angle)
        ry = world_x * math.sin(angle) + world_y * math.cos(angle)
        
        screen_x = cx + self.state.pan_x + (rx * self.state.zoom)
        screen_y = cy + self.state.pan_y - (ry * self.state.zoom)
        
        return screen_x, screen_y

    def screen_to_world(self, screen_x, screen_y):
        cx = self.canvas.winfo_width() / 2
        cy = self.canvas.winfo_height() / 2
        
        unscaled_x = (screen_x - cx - self.state.pan_x) / self.state.zoom
        unscaled_y = -(screen_y - cy - self.state.pan_y) / self.state.zoom
        
        angle = -self.state.rotation
        world_x = unscaled_x * math.cos(angle) - unscaled_y * math.sin(angle)
        world_y = unscaled_x * math.sin(angle) + unscaled_y * math.cos(angle)
        
        return world_x, world_y
