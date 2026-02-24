# dxf_exporter.py — Экспорт внутренних данных в формат DXF
#
# Использует библиотеку ezdxf для генерации корректных DXF-файлов,
# совместимых с T-FLEX CAD, AutoCAD, nanoCAD и другими системами.
#
# Версия: AC1015 (AutoCAD 2000 / R2000).

import math
import ezdxf


class DxfExporter:
    """Экспортирует внутренние примитивы приложения в файл DXF (AC1015)."""

    def export(self, state, filepath):
        """Собрать DXF и записать в файл.

        Args:
            state: объект AppState с коллекциями примитивов.
            filepath: путь для сохранения (.dxf).
        """
        doc = ezdxf.new('R2000')
        msp = doc.modelspace()

        # ── Отрезки ──
        for seg in state.segments:
            msp.add_line(
                (seg.p1.x, seg.p1.y),
                (seg.p2.x, seg.p2.y),
            )

        # ── Окружности ──
        for circle in state.circles:
            msp.add_circle(
                (circle.center.x, circle.center.y),
                circle.radius,
            )

        # ── Дуги ──
        for arc in state.arcs:
            start_deg = math.degrees(arc.start_angle)
            end_deg = math.degrees(arc.end_angle)
            msp.add_arc(
                (arc.center.x, arc.center.y),
                arc.radius,
                start_deg,
                end_deg,
            )

        # ── Прямоугольники ──
        for rect in state.rectangles:
            segments, arcs = rect.build_edges()
            for seg in segments:
                msp.add_line(
                    (seg.p1.x, seg.p1.y),
                    (seg.p2.x, seg.p2.y),
                )
            for arc in arcs:
                s_deg = math.degrees(arc.start_angle)
                e_deg = math.degrees(arc.end_angle)
                msp.add_arc(
                    (arc.center.x, arc.center.y),
                    arc.radius,
                    s_deg,
                    e_deg,
                )

        # ── Многоугольники ──
        for poly in state.polygons:
            verts = poly.vertices()
            n = len(verts)
            for i in range(n):
                p1 = verts[i]
                p2 = verts[(i + 1) % n]
                msp.add_line((p1.x, p1.y), (p2.x, p2.y))

        # ── Эллипсы ──
        for ell in state.ellipses:
            e1x, e1y, a, e2x, e2y, b = ell._basis()

            # DXF требует: major >= minor
            if b > a:
                major_axis = (e2x * b, e2y * b, 0.0)
                ratio = a / b if b > 1e-9 else 1.0
            else:
                major_axis = (e1x * a, e1y * a, 0.0)
                ratio = b / a if a > 1e-9 else 1.0

            msp.add_ellipse(
                center=(ell.center.x, ell.center.y),
                major_axis=major_axis,
                ratio=ratio,
            )

        doc.saveas(filepath)
