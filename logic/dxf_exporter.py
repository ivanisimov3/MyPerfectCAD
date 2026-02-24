# dxf_exporter.py — Экспорт внутренних данных в формат DXF
#
# Формат DXF (Drawing Exchange Format) — текстовый формат Autodesk
# для обмена чертежами между CAD-системами.
#
# Структура файла:
#   HEADER  — версия, единицы измерения
#   TABLES  — слои, типы линий
#   ENTITIES — геометрические объекты (LINE, CIRCLE, ARC, …)
#   EOF     — конец файла

import math

class DxfExporter:
    """Экспортирует внутренние примитивы приложения в файл DXF (AC1009 / R12)."""

    def __init__(self):
        self._lines = []  # собираем текст DXF построчно

    # ─── вспомогательные методы записи ────────────────────────────

    def _pair(self, code, value):
        """Добавить пару «код группы — значение»."""
        self._lines.append(f"{code:>3}")
        self._lines.append(str(value))

    def _section_start(self, name):
        self._pair(0, "SECTION")
        self._pair(2, name)

    def _section_end(self):
        self._pair(0, "ENDSEC")

    # ─── секция HEADER ────────────────────────────────────────────

    def _write_header(self):
        self._section_start("HEADER")

        # Версия DXF — AC1009 (AutoCAD R12), максимальная совместимость
        self._pair(9, "$ACADVER")
        self._pair(1, "AC1009")

        # Единицы измерения — миллиметры (4)
        self._pair(9, "$INSUNITS")
        self._pair(70, 4)

        self._section_end()

    # ─── секция TABLES ────────────────────────────────────────────

    def _write_tables(self):
        self._section_start("TABLES")

        # --- таблица типов линий LTYPE ---
        self._pair(0, "TABLE")
        self._pair(2, "LTYPE")
        self._pair(70, 1)  # число записей (пока одна — CONTINUOUS)

        # CONTINUOUS — сплошная линия (обязательна)
        self._pair(0, "LTYPE")
        self._pair(2, "CONTINUOUS")
        self._pair(70, 0)
        self._pair(3, "Solid line")
        self._pair(72, 65)       # ASCII 'A' — выравнивание
        self._pair(73, 0)        # 0 элементов паттерна
        self._pair(40, 0.0)      # длина паттерна = 0

        self._pair(0, "ENDTAB")

        # --- таблица слоёв LAYER ---
        self._pair(0, "TABLE")
        self._pair(2, "LAYER")
        self._pair(70, 1)  # число слоёв

        # Слой по умолчанию — «0»
        self._pair(0, "LAYER")
        self._pair(2, "0")
        self._pair(70, 0)        # статус
        self._pair(62, 7)        # цвет 7 = белый/чёрный
        self._pair(6, "CONTINUOUS")

        self._pair(0, "ENDTAB")

        self._section_end()

    # ─── запись примитивов ────────────────────────────────────────

    def _write_line(self, segment):
        """Segment → DXF LINE."""
        self._pair(0, "LINE")
        self._pair(8, "0")       # слой
        # начальная точка
        self._pair(10, f"{segment.p1.x:.6f}")
        self._pair(20, f"{segment.p1.y:.6f}")
        self._pair(30, 0.0)
        # конечная точка
        self._pair(11, f"{segment.p2.x:.6f}")
        self._pair(21, f"{segment.p2.y:.6f}")
        self._pair(31, 0.0)

    def _write_circle(self, circle):
        """Circle → DXF CIRCLE."""
        self._pair(0, "CIRCLE")
        self._pair(8, "0")       # слой
        # центр
        self._pair(10, f"{circle.center.x:.6f}")
        self._pair(20, f"{circle.center.y:.6f}")
        self._pair(30, 0.0)
        # радиус
        self._pair(40, f"{circle.radius:.6f}")

    def _write_arc(self, arc):
        """Arc → DXF ARC.  Углы переводятся из радиан в градусы."""
        self._pair(0, "ARC")
        self._pair(8, "0")       # слой
        # центр
        self._pair(10, f"{arc.center.x:.6f}")
        self._pair(20, f"{arc.center.y:.6f}")
        self._pair(30, 0.0)
        # радиус
        self._pair(40, f"{arc.radius:.6f}")
        # начальный и конечный углы (в градусах)
        start_deg = math.degrees(arc.start_angle)
        end_deg = math.degrees(arc.end_angle)
        self._pair(50, f"{start_deg:.6f}")
        self._pair(51, f"{end_deg:.6f}")

    def _write_rectangle(self, rect):
        """Rectangle → набор DXF LINE (+ARC для скруглений).

        Используем build_edges(), который уже учитывает фаски и скругления.
        """
        segments, arcs = rect.build_edges()
        for seg in segments:
            self._write_line(seg)
        for arc in arcs:
            self._write_arc(arc)

    def _write_polygon(self, polygon):
        """RegularPolygon → набор DXF LINE (рёбра между вершинами)."""
        verts = polygon.vertices()
        n = len(verts)
        for i in range(n):
            p1 = verts[i]
            p2 = verts[(i + 1) % n]
            self._pair(0, "LINE")
            self._pair(8, "0")
            self._pair(10, f"{p1.x:.6f}")
            self._pair(20, f"{p1.y:.6f}")
            self._pair(30, 0.0)
            self._pair(11, f"{p2.x:.6f}")
            self._pair(21, f"{p2.y:.6f}")
            self._pair(31, 0.0)

    # ─── секция ENTITIES ──────────────────────────────────────────

    def _write_entities(self, state):
        self._section_start("ENTITIES")

        for seg in state.segments:
            self._write_line(seg)

        for circle in state.circles:
            self._write_circle(circle)

        for arc in state.arcs:
            self._write_arc(arc)

        for rect in state.rectangles:
            self._write_rectangle(rect)

        for poly in state.polygons:
            self._write_polygon(poly)

        self._section_end()

    # ─── публичный API ────────────────────────────────────────────

    def export(self, state, filepath):
        """Собрать DXF и записать в файл.

        Args:
            state: объект AppState с коллекциями примитивов.
            filepath: путь для сохранения (.dxf).
        """
        self._lines = []

        self._write_header()
        self._write_tables()
        self._write_entities(state)

        self._pair(0, "EOF")

        with open(filepath, "w", encoding="ascii") as f:
            f.write("\n".join(self._lines) + "\n")
