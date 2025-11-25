# logic/styles.py
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class LineStyle:
    name: str
    display_name: str
    is_main: bool
    dash_pattern: Optional[Tuple[int, ...]] # Шаблон штриховки для Tkinter, None для сплошной

# Стандартные шаблоны штриховки (примерные значения для визуализации)
# Значения относительно базовой ширины. В рендерере будем их масштабировать

GOST_STYLES = {
    'solid_main': LineStyle(
        name='solid_main',
        display_name='Сплошная основная',
        is_main=True,   # True = основная толщина (s), False = тонкая (s/2)
        dash_pattern=None   # Сплошная
    ),
    'solid_thin': LineStyle(
        name='solid_thin',
        display_name='Сплошная тонкая',
        is_main=False,
        dash_pattern=None
    ),
    'solid_wave': LineStyle(
        name='solid_wave',
        display_name='Сплошная волнистая',
        is_main=True,
        dash_pattern=None   # Рисуем спец. алгоритмом
    ),
    'dashed': LineStyle(
        name='dashed',
        display_name='Штриховая',
        is_main=True,
        dash_pattern=(5, 3)
    ),
    'dash_dot_main': LineStyle(
        name='dash_dot_main',
        display_name='Штрихпунктирная утолщенная',
        is_main=True,
        dash_pattern=(8, 3, 3, 3) # Штрих, пробел, точка (короткий штрих), пробел
    ),
    'dash_dot_thin': LineStyle(
        name='dash_dot_thin',
        display_name='Штрихпунктирная тонкая',
        is_main=False,
        dash_pattern=(13, 3, 3, 3)
    ),
    'dash_dot_dot': LineStyle(
        name='dash_dot_dot',
        display_name='Штрихпунктирная с двумя точками',
        is_main=False,
        dash_pattern=(13, 3, 3, 3, 3, 3) # Штрих, пробел, точка, пробел, точка, пробел
    ),
    'solid_zigzag': LineStyle(
        name='solid_zigzag',
        display_name='Сплошная тонкая с изломами',
        is_main=False,
        dash_pattern=None
    )
}