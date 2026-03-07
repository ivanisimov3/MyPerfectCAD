import ezdxf

class DxfImporter:
    """Импортирует данные из DXF файла во внутренние примитивы приложения."""

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
            
            # T-FLEX часто экспортирует примитивы внутри блоков (INSERT).
            # Поэтому сначала "взрываем" все вхождения блоков (INSERT) в modelspace,
            # чтобы они превратились в базовые примитивы (LINE, ARC, и т.д.)
            for insert in msp.query('INSERT'):
                insert.explode()
            
            # Phase 2 & 3: Parse entities
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    p1 = Point(entity.dxf.start.x, entity.dxf.start.y)
                    p2 = Point(entity.dxf.end.x, entity.dxf.end.y)
                    segment = Segment(p1, p2)
                    state.segments.append(segment)
                    
                elif entity.dxftype() == 'POINT':
                    point = Point(entity.dxf.location.x, entity.dxf.location.y)
                    state.points.append(point)
                    
                elif entity.dxftype() == 'CIRCLE':
                    center = Point(entity.dxf.center.x, entity.dxf.center.y)
                    radius = entity.dxf.radius
                    state.circles.append(Circle.from_center_radius(center, radius))
                    
                elif entity.dxftype() == 'ARC':
                    center = Point(entity.dxf.center.x, entity.dxf.center.y)
                    radius = entity.dxf.radius
                    # ezdxf возвращает углы в градусах, нам нужны радианы
                    start_angle = math.radians(entity.dxf.start_angle)
                    end_angle = math.radians(entity.dxf.end_angle)
                    
                    state.arcs.append(Arc.from_center_angles(center, radius, start_angle, end_angle))
                    
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
                    
                    state.ellipses.append(Ellipse.from_center_axes(center, axis_point_a, axis_point_b))

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
                            spline = Spline(points_to_use)
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
                                state.segments.append(Segment(p1, p2))
                            elif v_entity.dxftype() == 'ARC':
                                center = Point(v_entity.dxf.center.x, v_entity.dxf.center.y)
                                radius = v_entity.dxf.radius
                                start_angle = math.radians(v_entity.dxf.start_angle)
                                end_angle = math.radians(v_entity.dxf.end_angle)
                                state.arcs.append(Arc.from_center_angles(center, radius, start_angle, end_angle))

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
                        spline = Spline(internal_points)
                        
                        # Если сплайн замкнут, нужно явно замкнуть его в нашей программе
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
