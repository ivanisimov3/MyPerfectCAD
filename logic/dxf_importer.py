import ezdxf
import math
import re
from logic.geometry import Point, Segment, Circle, Arc, Ellipse, Spline
from logic.state import Layer
from logic.styles import GOST_STYLES

class DxfImporter:
    """Импортирует данные из DXF файла во внутренние примитивы приложения."""

    def _rgb_to_hex(self, rgb):
        """ Переводим из rgb формата типа (255, 255, 255) в hex формат типа #ffffff """

        """
        x переводит число из десятичной системы в шестнадцатеричную 
        02 означает, что число будет состоять из 2 символов, если число меньше 16, то перед ним ставится 0
        """
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _decode_autocad_text(self, text):
        r"""Декодирует специальные символы AutoCAD (например, \U+XXXX) в обычные символы Unicode."""

        if not isinstance(text, str):
            return text

        r""" 
        Найти строку \U+, за которой идут ровно 4 символа от 0 до 9 или буквы от A до F. 
        Обернуть в круглые скобки. 
        Преобразуем эту строку из шестнадцатеричной системы в обычное целое число.
        Берем это число и возвращаем соответствующий ему символ Unicode.
        """
        return re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), text)

    def _get_entity_style(self, entity, doc):
        """ Получаем слой, стиль и цвет линии из DXF сущности """
        
        DXF_TO_STYLE = {
            'CONTINUOUS': 'solid_main',
            'THIN': 'solid_thin',
            'WAVES': 'solid_wave',
            'ZIGZAG': 'solid_zigzag',
            'HIDDEN': 'dashed',
            'CENTER2': 'dash_dot_main',
            'CENTER': 'dash_dot_thin',
            'PHANTOM': 'dash_dot_dot'
        }
        
        # Слой
        raw_layer_name = entity.dxf.layer if entity.dxf.hasattr('layer') else '0'
        layer_name = self._decode_autocad_text(raw_layer_name)
        if layer_name.lower() == 'defpoints':
            layer_name = '0'
        
        # Тип линии
        dxf_linetype = entity.dxf.linetype if entity.dxf.hasattr('linetype') else 'ByLayer'
        
        # https://ezdxf.mozman.at/docs/howto/content.html
        # Default value is 256 which means BYLAYER
        if dxf_linetype.upper() == 'BYLAYER':
            # Пытаемся достать стиль линии из таблицы слоя
            try:
                layer_obj = doc.layers.get(raw_layer_name)
                dxf_linetype = layer_obj.dxf.linetype
            except Exception:
                dxf_linetype = 'CONTINUOUS'
                
        # T-FLEX добавляет параметры к стилю при экспорте: "HIDDEN_per6_scale0.872385"
        base_linetype = dxf_linetype.upper().split('_')[0]
                
        style_name = DXF_TO_STYLE.get(base_linetype, 'solid_main')
        if style_name not in GOST_STYLES:
            style_name = 'solid_main'
            
        # Толщина линии (это необходимо, так как при экспорте T-FLEX отличает Основную и Тонкую только толщиной)
        if style_name == 'solid_main':
            lineweight = entity.dxf.lineweight if entity.dxf.hasattr('lineweight') else -1 # ezdxf const LINEWEIGHT_BYLAYER
            
            # ByLayer
            if lineweight == -1:
                try:
                    layer_obj = doc.layers.get(raw_layer_name)
                    lineweight = layer_obj.dxf.lineweight if layer_obj.dxf.hasattr('lineweight') else -3    # DEFAULT
                except Exception:
                    lineweight = -3
                    
            # Если толщина задана и она меньше 60 (0.6мм), считаем линию тонкой
            if 0 <= lineweight < 60:
                style_name = 'solid_thin'
                
        # Цвет
        rgb = (0, 0, 0)
        color_index = entity.dxf.color if entity.dxf.hasattr('color') else 256
        
        if entity.dxf.hasattr('true_color'):
            rgb = ezdxf.colors.int2rgb(entity.dxf.true_color)
        elif color_index == 256:    # ByLayer
            try:
                layer_obj = doc.layers.get(raw_layer_name)
                if layer_obj.dxf.hasattr('true_color'):
                    rgb = ezdxf.colors.int2rgb(layer_obj.dxf.true_color)
                else:
                    layer_color_index = layer_obj.color
                    rgb = ezdxf.colors.aci2rgb(abs(layer_color_index))
            except Exception:
                pass
        elif color_index != 256 and color_index != 0:   # https://ezdxf.mozman.at/docs/enums.html#ezdxf.enums.ACI.BYLAYER
            rgb = ezdxf.colors.aci2rgb(color_index)
            
        color_hex = self._rgb_to_hex(rgb)

        return layer_name, style_name, color_hex

    def import_dxf(self, state, filepath, root):
        """
        Чтение DXF и заполнение списков примитивов в AppState.
        
        Args:
            state: объект AppState с коллекциями примитивов.
            filepath: путь к файлу (.dxf).
            root: главное окно Tkinter для конвертации цветов.
        """

        try:

            # ezdxf supports loading ASCII and binary DXF documents from a file
            # https://ezdxf.readthedocs.io/en/stable/usage_for_beginners.html#loading-dxf-files
            doc = ezdxf.readfile(filepath)

            # https://ezdxf.mozman.at/docs/concepts/modelspace.html
            # The modelspace contains the “real” world representation of the drawing subjects in real world units 
            # and is displayed in the tab called “Model” in CAD applications.
            msp = doc.modelspace()
            
            # https://ezdxf.readthedocs.io/en/stable/tutorials/layers.html#tutorial-for-layers
            # The LayerTable object supports some standard Python protocols
            for layer in doc.layers:
                name = self._decode_autocad_text(layer.dxf.name)
                if name.lower() == 'defpoints': # T-FLEX экспортирует нулевой слой как Defpoints
                    name = '0'
                    
                # Необязательная часть кода для ипорта цвета слоя в соотвествии с требованием: 
                # каждый слой должен иметь цвет
                if layer.dxf.hasattr('true_color'):
                    rgb = ezdxf.colors.int2rgb(layer.dxf.true_color)
                else:
                    rgb = ezdxf.colors.aci2rgb(abs(layer.color))
                color_hex = self._rgb_to_hex(rgb)
                
                existing = state.get_layer(name)
                if existing:
                    if name != '0' or existing.color == '#000000': 
                         existing.color = color_hex
                else:
                    state.layers.append(Layer(name, color=color_hex))

            while True:

                # https://ezdxf.readthedocs.io/en/stable/tutorials/blocks.html#tut-blocks
                # Ищем все объекты типа INSERT, чтобы разбить их на примитивы
                inserts = msp.query('INSERT')
                if not inserts:
                    break
                for insert in inserts:
                    insert.explode()
            
            # Проходимся по каждому entity
            for entity in msp:
                layer_name, style_name, color_hex = self._get_entity_style(entity, doc)
                
                # https://ezdxf.mozman.at/docs/tasks/get_entity_type.html
                # The dxftype() method returns the entity type as defined by the DXF reference as an uppercase string.

                # https://ezdxf.readthedocs.io/en/stable/dxfentities/index.html
                # Здесь можно узнать все параметры, которые можно получить у каждого примитива

                if entity.dxftype() == 'LINE':
                    p1 = Point(entity.dxf.start.x, entity.dxf.start.y)
                    p2 = Point(entity.dxf.end.x, entity.dxf.end.y)
                    segment = Segment(p1, p2, style_name=style_name, color=color_hex)
                    segment.layer = layer_name
                    state.segments.append(segment)
                    
                elif entity.dxftype() == 'POINT':
                    point = Point(entity.dxf.location.x, entity.dxf.location.y, style_name=style_name, color=color_hex)
                    point.layer = layer_name
                    state.points.append(point)
                    
                elif entity.dxftype() == 'CIRCLE':
                    center = Point(entity.dxf.center.x, entity.dxf.center.y)
                    radius = entity.dxf.radius
                    circle = Circle.from_center_radius(center, radius, style_name=style_name, color=color_hex)
                    circle.layer = layer_name
                    state.circles.append(circle)
                    
                elif entity.dxftype() == 'ARC':
                    center = Point(entity.dxf.center.x, entity.dxf.center.y)
                    radius = entity.dxf.radius
                    start_angle = math.radians(entity.dxf.start_angle)
                    end_angle = math.radians(entity.dxf.end_angle)
                    
                    arc = Arc.from_center_angles(center, radius, start_angle, end_angle, style_name=style_name, color=color_hex)
                    arc.layer = layer_name
                    state.arcs.append(arc)
                    
                elif entity.dxftype() == 'ELLIPSE':
                    center = Point(entity.dxf.center.x, entity.dxf.center.y)
                    
                    """ 
                    В DXF большая полуось задается как вектор (x, y), отсчитываемый от центра.
                    Прибавляем этот вектор к центру, чтобы получить конкретную физическую точку на плоскости (axis_point_a).
                    """
                    major_axis = entity.dxf.major_axis
                    
                    a_x = center.x + major_axis[0]
                    a_y = center.y + major_axis[1]
                    axis_point_a = Point(a_x, a_y)
                    
                    """
                    Малая полуось не задается напрямую, в DXF есть только ratio (коэффициент сжатия от 0 до 1).
                    Длина большой полуоси вычисляется как гипотенуза из координат её вектора.
                    Длина малой полуоси = Длина большой * ratio.
                    """
                    ratio = entity.dxf.ratio
                    major_len = math.hypot(major_axis[0], major_axis[1])
                    minor_len = major_len * ratio
                    
                    """
                    Для вычисления координат точки малой полуоси необходимо повернуть вектор большой полуоси ровно на 90 градусов.
                    Сначала находим нормализованный вектор большой полуоси (делим координаты на длину вектора).
                    """
                    if major_len > 1e-9:
                        nx, ny = major_axis[0] / major_len, major_axis[1] / major_len
                    else:
                        nx, ny = 1.0, 0.0
                        
                    """
                    Свойство extrusion определяет "нормаль" 2D-фигуры в 3D-пространстве.
                    Если Z-компонента нормали отрицательная, значит плоскость фигуры "перевернута" обратной стороной.
                    Из-за этого направление отсчета углов (и направление поворота вектора на 90 градусов) меняется.
                    Формула поворота вектора (nx, ny) на 90 градусов:
                    - Против часовой: (-ny, nx)
                    - По часовой (если extrusion перевернут): (ny, -nx)
                    """
                    extrusion = getattr(entity.dxf, 'extrusion', (0,0,1))
                    if extrusion[2] < 0:
                        ox, oy = ny, -nx
                    else:
                        ox, oy = -ny, nx
                        
                    # Умножаем повернутый нормализованный вектор на длину малой полуоси и прибавляем к центру
                    b_x = center.x + ox * minor_len
                    b_y = center.y + oy * minor_len
                    axis_point_b = Point(b_x, b_y)
                    
                    ellipse = Ellipse.from_center_axes(center, axis_point_a, axis_point_b, style_name=style_name, color=color_hex)
                    ellipse.layer = layer_name
                    state.ellipses.append(ellipse)

                elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    # T-FLEX экспортирует и сплайны, и обычные полилинии как POLYLINE с флагом 128 (сглаживание).
                    # Мы можем отличить их по количеству точек: сплайны бьются на множество мелких отрезков.
                    
                    points_to_use = []
                    if entity.dxftype() == 'POLYLINE':
                        for v in entity.vertices:
                            points_to_use.append(Point(v.dxf.location.x, v.dxf.location.y))
                    else:   # LWPOLYLINE
                        with entity.points() as points:
                            for p in points:
                                points_to_use.append(Point(p[0], p[1]))
                                
                    if not points_to_use:
                        continue
                        
                    if len(points_to_use) > 20:
                        
                        spline = Spline(points_to_use, style_name=style_name, color=color_hex)
                        spline.layer = layer_name
                        if entity.is_closed:
                            spline.is_closed = True
                        state.splines.append(spline)
                        
                    # Если точек мало и начальная совпадает с конечной - это замкнутый многоугольник
                    elif len(points_to_use) > 2 and math.hypot(points_to_use[0].x - points_to_use[-1].x, points_to_use[0].y - points_to_use[-1].y) < 1e-5:
                        from logic.geometry import RegularPolygon
                        
                        pts = points_to_use[:-1]
                        
                        for i in range(len(pts)):
                            p1 = pts[i]
                            p2 = pts[(i + 1) % len(pts)]
                            segment = Segment(p1, p2, style_name=style_name, color=color_hex)
                            segment.layer = layer_name
                            state.segments.append(segment)
                            
                    else:
                        # Обычная незамкнутая полилиния (разбиваем на отрезки)
                        # Используем virtual_entities, если в полилинии есть выпуклости (дуги)
                        for v_entity in entity.virtual_entities():
                            if v_entity.dxftype() == 'LINE':
                                p1 = Point(v_entity.dxf.start.x, v_entity.dxf.start.y)
                                p2 = Point(v_entity.dxf.end.x, v_entity.dxf.end.y)
                                segment = Segment(p1, p2, style_name=style_name, color=color_hex)
                                segment.layer = layer_name
                                state.segments.append(segment)
                            elif v_entity.dxftype() == 'ARC':
                                center = Point(v_entity.dxf.center.x, v_entity.dxf.center.y)
                                radius = v_entity.dxf.radius
                                start_angle = math.radians(v_entity.dxf.start_angle)
                                end_angle = math.radians(v_entity.dxf.end_angle)
                                arc = Arc.from_center_angles(center, radius, start_angle, end_angle, style_name=style_name, color=color_hex)
                                arc.layer = layer_name
                                state.arcs.append(arc)

                elif entity.dxftype() == 'SPLINE':
                    
                    points_to_use = []
                    if hasattr(entity, 'control_points') and len(entity.control_points) > 0:
                        points_to_use = entity.control_points
                    elif hasattr(entity, 'fit_points') and len(entity.fit_points) > 0:
                        points_to_use = entity.fit_points
                    
                    if points_to_use:
                        internal_points = [Point(p[0], p[1]) for p in points_to_use]
                        spline = Spline(internal_points, style_name=style_name, color=color_hex)
                        spline.layer = layer_name
                        
                        if getattr(entity, 'closed', False):
                            spline.is_closed = True
                            
                        state.splines.append(spline)
            
            print(f"DXF успешно импортирован. Версия: {doc.dxfversion}")
            print(f"Загружено: отрезков {len(state.segments)}, точек {len(state.points)}, "
                  f"окружностей {len(state.circles)}, дуг {len(state.arcs)}, "
                  f"эллипсов {len(state.ellipses)}, сплайнов {len(state.splines)}")
            
        except IOError:
            raise Exception(f"Невозможно прочитать файл: {filepath}")
        except ezdxf.DXFStructureError as e:
            raise Exception(f"Некорректная структура DXF: {e}")