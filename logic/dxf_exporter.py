# dxf_exporter.py — Экспорт внутренних данных в формат DXF
#
# Использует библиотеку ezdxf для генерации корректных DXF-файлов,
# совместимых с T-FLEX CAD, AutoCAD, nanoCAD и другими системами.
#
# Версия: AC1018 | AutoCAD R2004

import math
import ezdxf
from logic.styles import GOST_STYLES

# Названия из tcad.lin, specline.def, папки LinePattern и https://tflexcad.ru/help/cad/15/index.html?graghics_parameters.htm
STYLE_TO_DXF = {
    'solid_main': 'CONTINUOUS',     # Основная
    'solid_thin': 'THIN',           # Тонкая
    'solid_wave': 'WAVES',          # Волнистая
    'solid_zigzag': 'ZIGZAG',       # Зигзаг
    'dashed': 'HIDDEN',             # Штриховая
    'dash_dot_main': 'CENTER2',     # Штрихпунктирная короткая
    'dash_dot_thin': 'CENTER',      # Штрихпунктирная
    'dash_dot_dot': 'PHANTOM'       # Штрихпунктирная с двумя точками
}

class DxfExporter:
    """Экспортирует внутренние примитивы приложения в файл DXF (AC1018)."""

    def _tk_color_to_rgb(self, tk_color, root):
        try:
            # Tkinter возвращает 16-битные значения цвета (от 0 до 65535)
            r, g, b = root.winfo_rgb(tk_color)
            # Делим на 256, чтобы получить привычные 8-битные значения (от 0 до 255)
            return (r // 256, g // 256, b // 256)
        except Exception:
            return (0, 0, 0)    # Черный по умолчанию

    def _setup_linetypes(self, doc):
        """Создает стандартные типы линий в DXF документе на основе текущих GOST_STYLES."""
        
        # https://ezdxf.mozman.at/docs/tutorials/linetypes.html#tut-linetypes
        # elements = [total_pattern_length, elem1, elem2, ...]
        patterns = {
            'THIN': [0.0],
            'WAVES': [0.0],
            'ZIGZAG': [0.0]
        }
        
        # Штриховая (HIDDEN)
        gost_dashed = GOST_STYLES.get('dashed')
        if gost_dashed and gost_dashed.dash_pattern:
            dash, gap = gost_dashed.dash_pattern
            patterns['HIDDEN'] = [dash + gap, float(dash), -float(gap)]
            
        # Штрихпунктирная утолщенная (CENTER2)
        gost_center2 = GOST_STYLES.get('dash_dot_main')
        if gost_center2 and gost_center2.dash_pattern:
            dash, gap = gost_center2.dash_pattern
            dot = 1.0
            space = (gap - dot) / 2.0
            patterns['CENTER2'] = [dash + gap, float(dash), -space, dot, -space]
            
        # Штрихпунктирная тонкая (CENTER)
        gost_center = GOST_STYLES.get('dash_dot_thin')
        if gost_center and gost_center.dash_pattern:
            dash, gap = gost_center.dash_pattern
            dot = 1.0
            space = (gap - dot) / 2.0
            patterns['CENTER'] = [dash + gap, float(dash), -space, dot, -space]
            
        # Штрихпунктирная с 2 точками (PHANTOM)
        gost_phantom = GOST_STYLES.get('dash_dot_dot')
        if gost_phantom and gost_phantom.dash_pattern:
            dash, gap = gost_phantom.dash_pattern
            dot = 1.0
            space = (gap - 2.0 * dot) / 3.0
            patterns['PHANTOM'] = [dash + gap, float(dash), -space, dot, -space, dot, -space]

        for name, pattern in patterns.items():
            if name not in doc.linetypes:
                doc.linetypes.new(name=name, dxfattribs={
                    'description': name,
                    'pattern': pattern
                })

    def _get_attribs(self, doc_layer, primitive, root, state):

        # Вытаскиваем свойства объекта, иначе ставим дефолтные
        layer = getattr(primitive, 'layer', '0')
        style = getattr(primitive, 'style_name', 'solid_main')
        color = getattr(primitive, 'color', 'black')
        
        # Получаем цвет линии в формате true_color
        rgb = self._tk_color_to_rgb(color, root)
        true_color = ezdxf.colors.rgb2int(rgb)
        
        # Соотносим тип линии
        dxf_linetype = STYLE_TO_DXF.get(style, 'CONTINUOUS')
        

        # Определяем толщину линии в зависимости от типа линии
        gost_style = GOST_STYLES.get(style)
        is_main = gost_style.is_main if gost_style else False
        
        # https://ezdxf.mozman.at/docs/concepts/lineweights.html#lineweights
        # Список стандартных толщин
        valid_weights = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211]
        
        # Основная = base_thickness, тонкая = base_thickness / 2
        thickness_mm = state.base_thickness_mm if is_main else state.base_thickness_mm / 2.0
        target_weight = int(thickness_mm * 100)
        
        # Находим ближайший стандартный lineweight DXF
        closest_weight = min(valid_weights, key=lambda x: abs(x - target_weight))
        

        # Расчет масштаба штрихов (ltscale)
        base_type = gost_style.base_type if gost_style else 'solid'
        ltscale = 1.0

        # if base_type != 'solid':
        #     ltscale = state.base_thickness_mm * 10.0
        
        return {
            'layer': layer,
            'linetype': dxf_linetype,
            'true_color': true_color,
            'lineweight': closest_weight,
            'ltscale': ltscale
        }

    def export(self, state, filepath, root):
        """Собрать DXF и записать в файл.

        Args:
            state: объект AppState с коллекциями примитивов.
            filepath: путь для сохранения (.dxf).
            root: главное окно Tkinter для конвертации цветов.
        """

        # The support for true color was added to the DXF file format in revision R2004. 
        # https://ezdxf.mozman.at/docs/concepts/true_color.html
        doc = ezdxf.new('R2004')
        
        # https://ezdxf.mozman.at/docs/concepts/units.html#module-ezdxf.units
        # https://ezdxf.mozman.at/docs/concepts/lineweights.html
        doc.header['$INSUNITS'] = 4     # Millimeters
        doc.header['$MEASUREMENT'] = 1  # Metric
        doc.header['$LUNITS'] = 2       # Decimal (default)
        doc.header['$LWDISPLAY'] = 1    # Setting the HEADER variable $LWDISPLAY to 1, activates support for displaying lineweights on screen

        # https://ezdxf.mozman.at/docs/concepts/modelspace.html
        # The modelspace contains the “real” world representation of the drawing subjects in real world units 
        # and is displayed in the tab called “Model” in CAD applications.
        msp = doc.modelspace()
        
        self._setup_linetypes(doc)

        # Проходим через все слои
        for layer in state.layers:
            # Каждый слой должен иметь цвет в соответствии со спецификацией Autodesk 
            rgb = self._tk_color_to_rgb(layer.color, root)
            # 2. ezdxf хранит пользовательские (True Color) цвета как одно целое число.
            # rgb2int склеивает (255, 0, 0) в число 16711680.
            true_color = ezdxf.colors.rgb2int(rgb)
            if layer.name != "0":
                doc.layers.new(name=layer.name, dxfattribs={'true_color': true_color})
            else:
                doc.layers.get("0").true_color = true_color


        # Дальше идем по спискам примитивов и добавляем их в modelspace

        # Line, Circle, Arc, Ellipse, Point
        # https://ezdxf.mozman.at/docs/tutorials/dxf_primitives.html#tut-dxf-primitives

        for seg in state.segments:
            msp.add_line(
                (seg.p1.x, seg.p1.y),
                (seg.p2.x, seg.p2.y),
                dxfattribs=self._get_attribs(seg.layer, seg, root, state),
            )

        for circle in state.circles:
            msp.add_circle(
                (circle.center.x, circle.center.y),
                circle.radius,
                dxfattribs=self._get_attribs(circle.layer, circle, root, state),
            )

        for arc in state.arcs:
            # Углы строго в градусах, переводим их радиан
            start_deg = math.degrees(arc.start_angle)
            end_deg = math.degrees(arc.end_angle)
            msp.add_arc(
                (arc.center.x, arc.center.y),
                arc.radius,
                start_deg,
                end_deg,
                dxfattribs=self._get_attribs(arc.layer, arc, root, state),
            )

        for ell in state.ellipses:
            e1x, e1y, a, e2x, e2y, b = ell._basis()
            # Большая полуось (major) должна быть реально больше или равна малой (minor).
            # Если мы нарисовали наоборот - меняем оси местами
            if b > a:
                major_axis = (e2x * b, e2y * b, 0.0)    # Вектор направления большой оси
                ratio = a / b if b > 1e-9 else 1.0  # Коэффициент сжатия (малой оси) с защитой от деления на 0
            else:
                major_axis = (e1x * a, e1y * a, 0.0)
                ratio = b / a if a > 1e-9 else 1.0

            msp.add_ellipse(
                center=(ell.center.x, ell.center.y),
                major_axis=major_axis,
                ratio=ratio,
                dxfattribs=self._get_attribs(ell.layer, ell, root, state),
            )

        for pt in state.points:
            msp.add_point((pt.x, pt.y), dxfattribs=self._get_attribs(pt.layer, pt, root, state))

        # Прямоугольник это совокупность отрезков и возможно дуг
        for rect in state.rectangles:
            segments, arcs = rect.build_edges()
            for seg in segments:
                msp.add_line(
                    (seg.p1.x, seg.p1.y),
                    (seg.p2.x, seg.p2.y),
                    dxfattribs=self._get_attribs(rect.layer, rect, root, state),
                )
            for arc in arcs:
                s_deg = math.degrees(arc.start_angle)
                e_deg = math.degrees(arc.end_angle)
                msp.add_arc(
                    (arc.center.x, arc.center.y),
                    arc.radius,
                    s_deg,
                    e_deg,
                    dxfattribs=self._get_attribs(rect.layer, rect, root, state),
                )

        # Полилиния тоже совокупность отрезков
        for poly in state.polygons:
            verts = poly.vertices()
            n = len(verts)
            for i in range(n):
                p1 = verts[i]
                p2 = verts[(i + 1) % n]
                msp.add_line(
                    (p1.x, p1.y), (p2.x, p2.y),
                    dxfattribs=self._get_attribs(poly.layer, poly, root, state),
                )

        # Spline
        # https://ezdxf.mozman.at/docs/tutorials/spline.html#tut-spline

        for spline in state.splines:
            if len(spline.control_points) < 2:  # Минимум две контрольные точки
                continue
            fit_pts = [(p.x, p.y) for p in spline.control_points]
            msp.add_spline(fit_pts, dxfattribs=self._get_attribs(spline.layer, spline, root, state))

        doc.saveas(filepath)