# logic/styles.py

'''
Здесь описана структура стиля линии.
'''

from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class LineStyle:
    name: str             # Название стиля для программы
    display_name: str     # Имя для отображения в UI
    is_main: bool         # Если True -> толщина S, иначе S/2
    
    # Параметры штриховки
    dash_pattern: Optional[Tuple[float, ...]]
    
    # Ограничения на ввод размеров по ГОСТ (min_dash, max_dash, min_gap, max_gap)
    limits: Optional[Tuple[float, float, float, float]] = None
    
    # Флаг пользовательского стиля
    is_custom: bool = False
    
    # Тип алгоритма отрисовки (solid, dashed, wave, zigzag)
    base_type: str = 'solid'
    
    # Количество изломов для стиля zigzag (None = автоматически)
    kinks_count: Optional[int] = None
    
    # Амплитуда волны для стиля wave в единицах чертежа (None = по умолчанию ~3)
    wave_amplitude: Optional[float] = None 

# База предустановленных стилей ГОСТ
GOST_STYLES = {
    'solid_main': LineStyle(
        name='solid_main',
        display_name='Сплошная основная',
        is_main=True,
        dash_pattern=None,
        base_type='solid'
    ),
    'solid_thin': LineStyle(
        name='solid_thin',
        display_name='Сплошная тонкая',
        is_main=False,
        dash_pattern=None,
        base_type='solid'
    ),
    'solid_wave': LineStyle(
        name='solid_wave',
        display_name='Сплошная волнистая',
        is_main=False,
        dash_pattern=None,
        base_type='wave',
        wave_amplitude=3.0  # Амплитуда волны по умолчанию
    ),
    'solid_zigzag': LineStyle(
        name='solid_zigzag',
        display_name='Сплошная тонкая с изломами',
        is_main=False,
        dash_pattern=None,
        base_type='zigzag',
        kinks_count=2  # Количество изломов по умолчанию
    ),
    'dashed': LineStyle(
        name='dashed',
        display_name='Штриховая',
        is_main=False,
        dash_pattern=(5, 2),
        limits=(2, 8, 1, 2),
        base_type='dashed'
    ),
    'dash_dot_main': LineStyle(
        name='dash_dot_main',
        display_name='Штрихпунктирная утолщенная',
        is_main=True,
        dash_pattern=(5, 3),
        limits=(3, 8, 3, 4),
        base_type='dash_dot'
    ),
    'dash_dot_thin': LineStyle(
        name='dash_dot_thin',
        display_name='Штрихпунктирная тонкая',
        is_main=False,
        dash_pattern=(15, 4),
        limits=(5, 30, 3, 5),
        base_type='dash_dot'
    ),
    'dash_dot_dot': LineStyle(
        name='dash_dot_dot',
        display_name='Штрихпунктирная с двумя точками',
        is_main=False,
        dash_pattern=(15, 5),
        limits=(5, 30, 4, 6),
        base_type='dash_dot_dot'
    )
}