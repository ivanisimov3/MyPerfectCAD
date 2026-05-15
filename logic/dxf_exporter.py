# dxf_exporter.py — Экспорт внутренних данных в формат DXF
#
# Использует библиотеку ezdxf для генерации корректных DXF-файлов,
# совместимых с T-FLEX CAD, AutoCAD, nanoCAD и другими системами.
#
# Версия: AC1018 | AutoCAD R2004

import math
import ezdxf
from logic.dimension_styles import DEFAULT_DIMENSION_STYLES
from logic.dimensions import AngularDimension, LinearDimension, RadialDimension
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

    def _rgb_to_aci(self, rgb):
        """Возвращает ближайший ACI-цвет для полей DIMSTYLE."""
        best_index = 7
        best_distance = float("inf")
        for index in range(1, 256):
            color_int = ezdxf.colors.DXF_DEFAULT_COLORS[index]
            candidate = ezdxf.colors.int2rgb(color_int)
            distance = (
                (int(rgb[0]) - candidate[0]) ** 2
                + (int(rgb[1]) - candidate[1]) ** 2
                + (int(rgb[2]) - candidate[2]) ** 2
            )
            if distance < best_distance:
                best_index = index
                best_distance = distance
        return best_index

    def _lineweight_for_style(self, style_name, state):
        valid_weights = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53, 60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211]
        gost_style = GOST_STYLES.get(style_name)
        is_main = gost_style.is_main if gost_style else False
        thickness_mm = state.base_thickness_mm if is_main else state.base_thickness_mm / 2.0
        target_weight = int(thickness_mm * 100)
        return min(valid_weights, key=lambda x: abs(x - target_weight))

    def _point_tuple(self, point):
        return (float(point.x), float(point.y))

    def _dimension_style_attribs(self, style, root, diameter=False):
        text_rgb = self._tk_color_to_rgb(style.text_color, root)
        attribs = {
            "dimtxt": max(0.1, float(style.text_height_mm)),
            "dimasz": max(0.1, float(style.arrow_size_mm)),
            "dimdec": int(style.decimal_places),
            "dimzin": 8,
            "dimgap": max(0.0, float(style.text_gap_mm)),
            "dimexo": max(0.0, float(style.extension_offset_mm)),
            "dimexe": max(0.0, float(style.extension_overrun_mm)),
            "dimclrd": self._rgb_to_aci(text_rgb),
            "dimclre": self._rgb_to_aci(text_rgb),
            "dimclrt": self._rgb_to_aci(text_rgb),
        }
        if diameter:
            attribs.update({
                "dimtix": 1,
                "dimatfit": 0,
                "dimtmove": 0,
                "dimtih": 0,
                "dimtoh": 0,
                "dimtad": 1,
            })
        return attribs

    def _setup_dimension_styles(self, doc, state, root):
        styles = getattr(state, "dimension_styles", DEFAULT_DIMENSION_STYLES)
        for style_name, style in styles.items():
            dxf_name = self._dimension_style_name(style_name)
            if dxf_name in doc.dimstyles:
                doc.dimstyles.get(dxf_name).update_dxf_attribs(self._dimension_style_attribs(style, root))
            else:
                doc.dimstyles.new(dxf_name, dxfattribs=self._dimension_style_attribs(style, root))

            diameter_name = self._dimension_style_name(style_name, diameter=True)
            diameter_attribs = self._dimension_style_attribs(style, root, diameter=True)
            if diameter_name in doc.dimstyles:
                doc.dimstyles.get(diameter_name).update_dxf_attribs(diameter_attribs)
            else:
                doc.dimstyles.new(diameter_name, dxfattribs=diameter_attribs)

    def _dimension_style_name(self, style_name, diameter=False):
        safe_name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(style_name).upper())
        suffix = "_DIAMETER" if diameter else ""
        return f"MP_{safe_name}{suffix}"

    def _dxf_text_content(self, text):
        return (
            str(text or "")
            .replace("⌀", "%%c")
            .replace("Ø", "%%c")
            .replace("ø", "%%c")
            .replace("°", "%%d")
            .replace("±", "%%p")
        )

    def _dimension_uses_text_template(self, dimension):
        return (
            not bool(getattr(dimension, "text_override", ""))
            and (
                getattr(dimension, "text_prefix_override", None) is not None
                or getattr(dimension, "text_suffix_override", None) is not None
            )
        )

    def _dimension_text(self, dimension, state):
        if self._dimension_uses_text_template(dimension):
            prefix = self._dxf_text_content(dimension._effective_text_prefix())
            suffix = self._dxf_text_content(dimension._effective_text_suffix())
            return f"{prefix}<>{suffix}"
        if getattr(dimension, "has_text_display_override", lambda: False)():
            return dimension.display_text(state)
        return "<>"

    def _dimension_dxfattribs(self, dimension, state, root):
        rgb = self._tk_color_to_rgb(getattr(dimension, "color", "black"), root)
        return {
            "layer": getattr(dimension, "layer", "0"),
            "true_color": ezdxf.colors.rgb2int(rgb),
            "lineweight": self._lineweight_for_style("solid_thin", state),
        }

    def _dimension_override(self, dimension, state, root):
        ext_rgb = self._tk_color_to_rgb(dimension._effective_extension_line_color(state), root)
        dim_rgb = self._tk_color_to_rgb(dimension._effective_dim_line_color(state), root)
        text_rgb = self._tk_color_to_rgb(dimension._effective_text_color(state), root)
        override = {
            "dimtxt": max(0.1, float(dimension._effective_text_height_mm(state))),
            "dimasz": max(0.1, float(dimension._effective_arrow_size_mm(state))),
            "dimdec": int(dimension._style(state).decimal_places),
            "dimzin": 8,
            "dimgap": max(0.0, float(dimension._effective_text_gap_mm(state))),
            "dimexe": max(0.0, float(dimension._effective_extension_overrun_mm(state))),
            "dimdle": max(0.0, float(dimension._effective_dim_line_extension_mm(state))),
            "dimclrd": self._rgb_to_aci(dim_rgb),
            "dimclre": self._rgb_to_aci(ext_rgb),
            "dimclrt": self._rgb_to_aci(text_rgb),
        }

        if getattr(dimension, "dimension_type", None) == "diameter":
            text_position = dimension._effective_text_position_mode(state)
            override.update({
                "dimtix": 1,       # держать текст внутри окружности
                "dimatfit": 0,     # требуется CAD для принудительного текста внутри
                "dimtmove": 0,     # перемещение текста не превращает размер в выноску
                "dimtih": 0,       # текст внутри выравнивается по размерной линии
                "dimtoh": 0,
                "dimtad": {"above": 1, "center": 0, "below": 4}.get(text_position, 1),
            })

        return override

    def _apply_dimension_format(self, dim_override, dimension, state):
        arrow_type = dimension._effective_arrow_type(state)
        arrow_size = dimension._effective_arrow_size_mm(state)
        if arrow_type == "tick":
            dim_override.set_tick(size=arrow_size)
        else:
            dim_override.set_arrows(size=arrow_size)

        text_position = dimension._effective_text_position_mode(state)
        if text_position == "center":
            dim_override.set_text_align(valign="center")
        elif text_position == "below":
            dim_override.set_text_align(valign="below")
        else:
            dim_override.set_text_align(valign="above")

    def _set_dimension_location(self, dim_override, dimension, state):
        geometry = dimension.resolve_geometry(state)
        if not geometry:
            return
        text_point = geometry.get("text_point")
        if text_point is None:
            return
        try:
            dim_override.set_location(self._point_tuple(text_point), leader=False, relative=False)
        except Exception:
            pass

    def _render_dimension(self, dim_override, dimension, state, use_geometry_location=True):
        self._apply_dimension_format(dim_override, dimension, state)
        if use_geometry_location:
            self._set_dimension_location(dim_override, dimension, state)
        dim_override.render()

    def _aligned_distance(self, p1, p2, line_point):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return 0.0
        nx = -dy / length
        ny = dx / length
        return (line_point.x - p1.x) * nx + (line_point.y - p1.y) * ny

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

    def _export_dimension(self, msp, doc, dimension, state, root):
        if isinstance(dimension, LinearDimension):
            return self._export_linear_dimension(msp, doc, dimension, state, root)
        if isinstance(dimension, RadialDimension):
            return self._export_radial_dimension(msp, doc, dimension, state, root)
        if isinstance(dimension, AngularDimension):
            return self._export_angular_dimension(msp, doc, dimension, state, root)

    def _export_linear_dimension(self, msp, doc, dimension, state, root):
        p1, p2, line_point = dimension._resolved_points()
        if math.hypot(p2.x - p1.x, p2.y - p1.y) < 1e-9:
            return

        dimstyle = self._dimension_style_name(
            dimension.dimension_style_name,
            diameter=dimension.dimension_type == "diameter",
        )
        override = self._dimension_override(dimension, state, root)
        dxfattribs = self._dimension_dxfattribs(dimension, state, root)
        text = self._dimension_text(dimension, state)

        if dimension.mode == "horizontal":
            dim_override = msp.add_linear_dim(
                base=self._point_tuple(line_point),
                p1=self._point_tuple(p1),
                p2=self._point_tuple(p2),
                angle=0.0,
                text=text,
                dimstyle=dimstyle,
                override=override,
                dxfattribs=dxfattribs,
            )
        elif dimension.mode == "vertical":
            dim_override = msp.add_linear_dim(
                base=self._point_tuple(line_point),
                p1=self._point_tuple(p1),
                p2=self._point_tuple(p2),
                angle=90.0,
                text=text,
                dimstyle=dimstyle,
                override=override,
                dxfattribs=dxfattribs,
            )
        else:
            dim_override = msp.add_aligned_dim(
                p1=self._point_tuple(p1),
                p2=self._point_tuple(p2),
                distance=self._aligned_distance(p1, p2, line_point),
                text=text,
                dimstyle=dimstyle,
                override=override,
                dxfattribs=dxfattribs,
            )

        self._render_dimension(dim_override, dimension, state)

    def _export_radial_dimension(self, msp, doc, dimension, state, root):
        center = dimension.center_ref.resolve()
        edge = dimension.edge_ref.resolve()
        radius = math.hypot(edge.x - center.x, edge.y - center.y)
        if radius < 1e-9:
            return

        dimstyle = self._dimension_style_name(
            dimension.dimension_style_name,
            diameter=dimension.dimension_type == "diameter",
        )
        override = self._dimension_override(dimension, state, root)
        dxfattribs = self._dimension_dxfattribs(dimension, state, root)
        text = self._dimension_text(dimension, state)
        angle = math.degrees(math.atan2(edge.y - center.y, edge.x - center.x))

        if dimension.dimension_type == "diameter":
            opposite_edge = (
                center.x - (edge.x - center.x),
                center.y - (edge.y - center.y),
            )
            if hasattr(msp, "add_diameter_dim_2p"):
                dim_override = msp.add_diameter_dim_2p(
                    p1=self._point_tuple(edge),
                    p2=opposite_edge,
                    text=text,
                    dimstyle=dimstyle,
                    override=override,
                    dxfattribs=dxfattribs,
                )
            else:
                dim_override = msp.add_diameter_dim(
                    center=self._point_tuple(center),
                    mpoint=self._point_tuple(edge),
                    text=text,
                    dimstyle=dimstyle,
                    override=override,
                    dxfattribs=dxfattribs,
                )
        else:
            dim_override = msp.add_radius_dim(
                center=self._point_tuple(center),
                radius=radius,
                angle=angle,
                text=text,
                dimstyle=dimstyle,
                override=override,
                dxfattribs=dxfattribs,
            )

        self._render_dimension(
            dim_override,
            dimension,
            state,
            use_geometry_location=dimension.dimension_type != "diameter",
        )

    def _export_angular_dimension(self, msp, doc, dimension, state, root):
        p1, vertex, p2, arc_point = dimension._resolved_points()
        if (
            math.hypot(p1.x - vertex.x, p1.y - vertex.y) < 1e-9
            or math.hypot(p2.x - vertex.x, p2.y - vertex.y) < 1e-9
            or math.hypot(arc_point.x - vertex.x, arc_point.y - vertex.y) < 1e-9
        ):
            return

        dimstyle = self._dimension_style_name(dimension.dimension_style_name)
        dim_override = msp.add_angular_dim_3p(
            base=self._point_tuple(arc_point),
            center=self._point_tuple(vertex),
            p1=self._point_tuple(p1),
            p2=self._point_tuple(p2),
            text=self._dimension_text(dimension, state),
            dimstyle=dimstyle,
            override=self._dimension_override(dimension, state, root),
            dxfattribs=self._dimension_dxfattribs(dimension, state, root),
        )
        self._render_dimension(dim_override, dimension, state)

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
        self._setup_dimension_styles(doc, state, root)

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

        for dimension in state.dimensions:
            self._export_dimension(msp, doc, dimension, state, root)

        doc.saveas(filepath)
