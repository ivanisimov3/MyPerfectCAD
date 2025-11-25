# logic/styles.py
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class LineStyle:
    name: str
    display_name: str
    is_main: bool
    dash_pattern: Optional[Tuple[float, ...]] 
    limits: Optional[Tuple[float, float, float, float]] = None 

# Стандартные шаблоны с ограничениями по ГОСТ
GOST_STYLES = {
    'solid_main': LineStyle(
        name='solid_main',
        display_name='Сплошная толстая основная',
        is_main=True,
        dash_pattern=None,
        limits=None
    ),
    'solid_thin': LineStyle(
        name='solid_thin',
        display_name='Сплошная тонкая',
        is_main=False,
        dash_pattern=None,
        limits=None
    ),
    'solid_wave': LineStyle(
        name='solid_wave',
        display_name='Сплошная волнистая',
        is_main=False,
        dash_pattern=None,
        limits=None
    ),
    'solid_zigzag': LineStyle(
        name='solid_zigzag',
        display_name='Сплошная тонкая с изломами',
        is_main=False,
        dash_pattern=None,
        limits=None
    ),
    'dashed': LineStyle(
        name='dashed',
        display_name='Штриховая',
        is_main=False,
        dash_pattern=(5, 2),
        limits=(2, 8, 1, 2) 
    ),
    'dash_dot_main': LineStyle(
        name='dash_dot_main',
        display_name='Штрихпунктирная утолщенная',
        is_main=True,
        dash_pattern=(5, 3), 
        limits=(3, 8, 3, 4)
    ),
    'dash_dot_thin': LineStyle(
        name='dash_dot_thin',
        display_name='Штрихпунктирная тонкая',
        is_main=False,
        dash_pattern=(15, 4),
        limits=(5, 30, 3, 5)
    ),
    'dash_dot_dot': LineStyle(
        name='dash_dot_dot',
        display_name='Штрихпунктирная с двумя точками',
        is_main=False,
        dash_pattern=(15, 5),
        limits=(5, 30, 4, 6)
    )
}