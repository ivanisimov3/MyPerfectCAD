import ezdxf

class DxfImporter:
    """Импортирует данные из DXF файла во внутренние примитивы приложения."""

    def _rgb_to_hex(self, rgb):
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _decode_autocad_text(self, text):
        if not isinstance(text, str):
            return text
        import re
        return re.sub(r'\\U\+([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), text)

    def _get_entity_style(self, entity, doc):
        from logic.styles import GOST_STYLES
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
        
        # 1. Слой
        raw_layer_name = entity.dxf.layer if entity.dxf.hasattr('layer') else '0'
        layer_name = self._decode_autocad_text(raw_layer_name)
        # T-FLEX экспортирует нулевой слой как Defpoints
        if layer_name.lower() == 'defpoints':
            layer_name = '0'
        
        # 2. Тип линии
        dxf_linetype = entity.dxf.linetype if entity.dxf.hasattr('linetype') else 'ByLayer'
        
        if dxf_linetype.upper() == 'BYLAYER':
            try:
                # Если у слоя стояло ByLayer, пытаемся достать его реальный тип из таблицы
                layer_obj = doc.layers.get(raw_layer_name)
                dxf_linetype = layer_obj.dxf.linetype
            except Exception:
                dxf_linetype = 'CONTINUOUS'
                
        # T-FLEx добавляет параметры к стилю при экспорте: "HIDDEN_per6_scale0.872385"
        base_linetype = dxf_linetype.upper().split('_')[0]
                
        style_name = DXF_TO_STYLE.get(base_linetype, 'solid_main')
        if style_name not in GOST_STYLES:
            style_name = 'solid_main'
            
        # 2.5 Толщина линии (Lineweight)
        # Если тип линии сплошной, то отличие Основной от Тонкой задается только толщиной!
        if style_name == 'solid_main':
            lineweight = entity.dxf.lineweight if entity.dxf.hasattr('lineweight') else -1 # ezdxf const LINEWEIGHT_BYLAYER
            
            if lineweight == -1: # ByLayer
                try:
                    layer_obj = doc.layers.get(raw_layer_name)
                    lineweight = layer_obj.dxf.lineweight if layer_obj.dxf.hasattr('lineweight') else -3 # DEFAULT
                except Exception:
                    lineweight = -3
                    
            # Если толщина задана (>=0) и она меньше 50 (0.5мм), считаем линию тонкой
            # Обычно основная 0.8мм (80), тонкая 0.4мм (40).
            if 0 <= lineweight < 60:
                style_name = 'solid_thin'
                
        # 3. Цвет
        rgb = (0, 0, 0)
        color_index = entity.dxf.color if entity.dxf.hasattr('color') else 256
        
        if entity.dxf.hasattr('true_color'):
            rgb = ezdxf.colors.int2rgb(entity.dxf.true_color)
        elif color_index == 256: # ByLayer
            try:
                layer_obj = doc.layers.get(raw_layer_name)
                if layer_obj.dxf.hasattr('true_color'):
                    rgb = ezdxf.colors.int2rgb(layer_obj.dxf.true_color)
                else:
                    layer_color_index = layer_obj.color
                    rgb = ezdxf.colors.aci2rgb(abs(layer_color_index))
            except Exception:
                pass
        elif color_index != 256 and color_index != 0:
            rgb = ezdxf.colors.aci2rgb(color_index)
            
        color_hex = self._rgb_to_hex(rgb)

        return layer_name, style_name, color_hex

    def import_dxf(self, state, filepath, root):
        """
        Чтение DXF файла и заполнение списков примитивов в AppState.
        
        Args:
            state: объект AppState.
            filepath: путь к файлу .dxf.
            root: главное окно Tkinter для конвертации цветов (если потребуется).
        """
        try:
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            from logic.geometry import Point, Segment, Circle, Arc, Ellipse
            import math
            
            # Считываем слои (Phase 5)
            from logic.state import Layer
            for layer in doc.layers:
                name = self._decode_autocad_text(layer.dxf.name)
                if name.lower() == 'defpoints':
                    name = '0'
                    
                if layer.dxf.hasattr('true_color'):
                    rgb = ezdxf.colors.int2rgb(layer.dxf.true_color)
                else:
                    rgb = ezdxf.colors.aci2rgb(abs(layer.color))
                color_hex = self._rgb_to_hex(rgb)
                
                # Добавляем или обновляем слой
                existing = state.get_layer(name)
                if existing:
                    # Если слой 0 существует, мы не меняем его цвет на белый(черный), 
                    # если только не хотим, но пока просто обновим его
                    if name != '0' or existing.color == '#000000': 
                         existing.color = color_hex
                else:
                    state.layers.append(Layer(name, color=color_hex))

            # Многоуровневые блоки (INSERT):
            # T-FLEX часто экспортирует примитивы внутри вложенных блоков.
            # Поэтому "взрываем" вхождения блоков (INSERT) в modelspace рекурсивно,
            # пока не останутся только базовые примитивы.
            while True:
                inserts = msp.query('INSERT')
                if not inserts:
                    break
                for insert in inserts:
                    insert.explode()
            
            # Phase 2 & 3: Parse entities
            for entity in msp:
                layer_name, style_name, color_hex = self._get_entity_style(entity, doc)
                
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
                    
                    # Вектор большой полуоси (Относительно центра, в WCS)
                    major_axis = entity.dxf.major_axis
                    
                    a_x = center.x + major_axis[0]
                    a_y = center.y + major_axis[1]
                    axis_point_a = Point(a_x, a_y)
                    
                    # Малая полуось = Большая полуось * ratio
                    # Направление малой полуоси ортогонально большой против часовой стрелки (если выдавливание +Z)
                    # Но ezdxf предоставляет удобный метод для получения точек на эллипсе
                    # Мы можем вычислить минорную ось вручную:
                    
                    ratio = entity.dxf.ratio
                    major_len = math.hypot(major_axis[0], major_axis[1])
                    minor_len = major_len * ratio
                    
                    # Вектор нормализованной большой оси
                    if major_len > 1e-9:
                        nx, ny = major_axis[0] / major_len, major_axis[1] / major_len
                    else:
                        nx, ny = 1.0, 0.0
                        
                    # Ортогональный вектор (поворот на 90 градусов)
                    extrusion = getattr(entity.dxf, 'extrusion', (0,0,1))
                    if extrusion[2] < 0:
                        ox, oy = ny, -nx # Поворот по часовой
                    else:
                        ox, oy = -ny, nx # Поворот против часовой
                        
                    b_x = center.x + ox * minor_len
                    b_y = center.y + oy * minor_len
                    axis_point_b = Point(b_x, b_y)
                    
                    ellipse = Ellipse.from_center_axes(center, axis_point_a, axis_point_b, style_name=style_name, color=color_hex)
                    ellipse.layer = layer_name
                    state.ellipses.append(ellipse)

                elif entity.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    # T-FLEX может экспортировать сплайны как POLYLINE с флагом 4 (3D) или 128 (2D Spline/Fit)
                    flags = getattr(entity.dxf, 'flags', 0)
                    is_poly_spline = (flags & 4) or (flags & 128)
                    
                    if is_poly_spline and entity.dxftype() == 'POLYLINE':
                        # Это сплайн, представленный полилинией.
                        # В T-FLEX вершины такого сплайна могут не иметь флагов контрольных точек,
                        # а быть просто набором точек для сглаживания.
                        from logic.geometry import Spline
                        
                        points_to_use = []
                        for v in entity.vertices:
                            points_to_use.append(Point(v.dxf.location.x, v.dxf.location.y))
                            
                        if points_to_use:
                            spline = Spline(points_to_use, style_name=style_name, color=color_hex)
                            spline.layer = layer_name
                            if entity.is_closed:
                                spline.is_closed = True
                            state.splines.append(spline)
                    else:
                        # Обычная полилиния, может содержать как прямые сегменты, так и дуги (bulges)
                        # ezdxf предоставляет удобный метод virtual_entities() для получения "чистых" примитивов
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
                    from logic.geometry import Spline
                    
                    # Проверяем, есть ли контрольные точки
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
