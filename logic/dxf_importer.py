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
            
            from logic.geometry import Point, Segment
            
            # T-FLEX часто экспортирует примитивы внутри блоков (INSERT).
            # Поэтому сначала "взрываем" все вхождения блоков (INSERT) в modelspace,
            # чтобы они превратились в базовые примитивы (LINE, ARC, и т.д.)
            for insert in msp.query('INSERT'):
                insert.explode()
            
            # Phase 2: Basic Entities (LINE, POINT)
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    p1 = Point(entity.dxf.start.x, entity.dxf.start.y)
                    p2 = Point(entity.dxf.end.x, entity.dxf.end.y)
                    
                    segment = Segment(p1, p2)
                    state.segments.append(segment)
                    
                elif entity.dxftype() == 'POINT':
                    point = Point(entity.dxf.location.x, entity.dxf.location.y)
                    state.points.append(point)
            
            print(f"DXF успешно импортирован. Версия: {doc.dxfversion}")
            print(f"Загружено отрезков: {len(state.segments)}, точек: {len(state.points)}")
            
        except IOError:
            raise Exception(f"Невозможно прочитать файл: {filepath}")
        except ezdxf.DXFStructureError as e:
            raise Exception(f"Некорректная структура DXF: {e}")
