# app/state.py

'''
Это единый источник правды (Single Source of Truth).
При изменении переменной здесь — меняется поведение во всей программе
'''

from logic.styles import GOST_STYLES

class AppState:
    def __init__(self):
        # Текущий режим работы (IDLE, CREATING, PANNING)
        self.app_mode = 'IDLE'
        
        # Список всех геометрических примитивов
        self.segments = []
        
        # Список выделенных объектов
        self.selected_segments = [] 
        
        # Временные данные для интерактивного построения
        self.preview_segment = None
        self.points_clicked = 0
        self.active_p1 = None
        self.active_p2 = None
        
        # Параметры Вида
        self.pan_x, self.pan_y = 0, 0
        self.zoom = 5.0 
        self.rotation = 0.0
        self.is_fullscreen = False
        
        # Настройки сетки и фона
        self.grid_step = 10 
        self.bg_color = 'white'
        self.grid_color = '#e0e0e0'
        
        # Глобальная толщина основной линии S в миллиметрах
        self.base_thickness_mm = 0.8
        
        # Коэффициент перевода: 1 мм экрана ≈ 3.78 пикселя
        self.mm_to_px_ratio = 3.78 
        
        # Централизованная база стилей. 
        self.line_styles = GOST_STYLES.copy()
        
        # Текущий инструмент рисования
        self.current_style_name = 'solid_main'
        self.current_color = 'black'