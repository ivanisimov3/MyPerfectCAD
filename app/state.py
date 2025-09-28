# app/state.py

class AppState:
    def __init__(self):
        # Режим работы приложения: 'IDLE' - ничего важного не делаем или 'CREATING_SEGMENT' - создаем отрезок
        self.app_mode = 'IDLE'
        
        # LIFO-очередь для хранения построенных отрезков
        self.segments = []
        
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
        
        # Настройки цветов
        self.bg_color = 'white'
        self.grid_color = '#e0e0e0'
        self.segment_color = 'red'