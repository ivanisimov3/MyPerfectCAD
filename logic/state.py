# app/state.py

'''
Это единый источник правды (Single Source of Truth).
При изменении переменной здесь — меняется поведение во всей программе
'''

from logic.styles import GOST_STYLES

class AppState:
    def __init__(self):
        # Текущий режим работы (IDLE, CREATING_SEGMENT, CREATING_CIRCLE, CREATING_ARC, PANNING)
        self.app_mode = 'IDLE'
        
        # Список всех геометрических примитивов
        self.segments = []
        self.circles = []
        self.arcs = []
        self.rectangles = []

        # Список выделенных объектов
        self.selected_segments = []
        self.selected_circles = []
        self.selected_arcs = []
        self.selected_rectangles = []

        # Временные данные для интерактивного построения
        self.preview_segment = None
        self.preview_circle = None
        self.preview_arc = None
        self.preview_rectangle = None
        self.points_clicked = 0
        self.active_p1 = None
        self.active_p2 = None
        self.active_p3 = None  # Для создания окружности по трем точкам
        self.active_p4 = None  # Для дуг (доп. точка конца)
        
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

        # Параметры для создания окружностей
        self.circle_creation_method = 'center_radius'  # center_radius, center_diameter, two_points, three_points

        # Параметры для создания дуг
        self.arc_creation_method = 'three_points'  # three_points, center_angles

        # Параметры для создания прямоугольников
        self.rectangle_creation_method = 'two_points'  # two_points, corner_size, center_size
        self.rectangle_corner_type = 'none'  # none, chamfer, fillet
        self.rectangle_corner_value = 0.0