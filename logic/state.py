# app/state.py

'''
Хранит все переменные, которые описывают текущий момент работы программы: 
    1) список нарисованных отрезков (segments), 
    2) текущий режим (рисуем, смотрим или перемещаемся), 
    3) настройки камеры (зум, смещение, поворот и тд.), 
    4) цвета и выбранные единицы измерения. 
Все остальные модули читают данные отсюда.
'''

from logic.styles import GOST_STYLES

class AppState:
    def __init__(self):
        self.app_mode = 'IDLE'
        
        # LIFO-очередь для хранения построенных отрезков
        self.segments = []
        
        self.selected_segments = []
        
        # Временный отрезок для предпросмотра в реальном времени
        self.preview_segment = None
        
        # Счетчик кликов мыши для создания точек
        self.points_clicked = 0
        
        # Флаги состояния режима приложения (полноэкранный или нет)
        self.is_fullscreen = False
        
        # Активные точки, которые нужно отрисовывать на холсте
        self.active_p1 = None
        self.active_p2 = None
        
        # Настройки камеры и вида
        self.pan_x, self.pan_y = 0, 0   # Смещение камеры
        self.zoom = 5.0 # Зум камеры
        self.grid_step = 10 # Шаг сетки
        self.rotation = 0.0
        
        # Настройки цветов
        self.bg_color = 'white'
        self.grid_color = '#e0e0e0'
        self.current_color = 'black'

        # Глобальная толщина 's' по ГОСТ (0.5 ... 1.4 мм). По умолчанию 0.8. То есть 2 пикселя: 0.8 мм; 2.5 пиеселя: 1 мм.
        self.base_thickness_s = 2  # В пикселях экрана! 

        self.current_style_name = 'solid_main'  # Текущий выбранный стиль для НОВЫХ объектов (храним ключ словаря)
        self.line_styles = GOST_STYLES.copy()   # Словарь всех загруженных стилей