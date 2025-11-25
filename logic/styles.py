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
        display_name='Сплошная толстая основная',
        is_main=True,   # True = основная толщина (s), False = тонкая (s/2)
        dash_pattern=None   # Сплошная
    ),
    'solid_thin': LineStyle(
        name='solid_thin',
        display_name='Сплошная тонкая',
        is_main=False,
        dash_pattern=None
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
        is_main=False,
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
        display_name='Штрихпунктирная с двумя точками тонкая',
        is_main=False,
        dash_pattern=(13, 3, 3, 3, 3, 3) # Штрих, пробел, точка, пробел, точка, пробел
    )
    # Примечание: "Волнистая" и "С изломами" требуют сложной векторной генерации, 
    # их стандартными средствами create_line (dash) не сделать идеально. 
    # Пока оставим их за рамками базовой реализации или добавим позже как спец-рендеринг.
}