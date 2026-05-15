from logic.styles import GOST_STYLES
from logic.dimension_styles import DEFAULT_DIMENSION_STYLES


class Layer:
    """Слой чертежа."""

    def __init__(self, name, visible=True, color=7):
        self.name = name
        self.visible = visible
        self.color = color          # ACI-цвет (для DXF-экспорта)


class AppState:
    def __init__(self):
        self.app_mode = 'IDLE'

        # ── Слои ──
        self.layers = [Layer("0")]
        self.active_layer = "0"
        
        self.segments = []
        self.circles = []
        self.arcs = []
        self.rectangles = []
        self.ellipses = []
        self.polygons = []
        self.splines = []
        self.points = []
        self.dimensions = []

        self.selected_segments = []
        self.selected_circles = []
        self.selected_arcs = []
        self.selected_rectangles = []
        self.selected_ellipses = []
        self.selected_polygons = []
        self.selected_splines = []
        self.selected_points = []
        self.selected_dimensions = []

        self.preview_segment = None
        self.preview_circle = None
        self.preview_arc = None
        self.preview_rectangle = None
        self.preview_ellipse = None
        self.preview_polygon = None
        self.preview_spline = None
        self.preview_dimension = None
        self.spline_control_points = []
        self.selected_spline_point_index = None
        self.dragging_spline_point_index = None
        self.points_clicked = 0
        self.active_p1 = None
        self.active_p2 = None
        self.active_p3 = None
        self.active_p4 = None
        self.dimension_creation_refs = []
        self.dimension_creation_object = None
        self.dimension_grip_drag = None
        
        self.pan_x, self.pan_y = 0, 0
        self.zoom = 5.0 
        self.rotation = 0.0
        self.is_fullscreen = False
        
        self.grid_step = 10 
        self.bg_color = 'white'
        self.grid_color = '#e0e0e0'
        
        self.base_thickness_mm = 0.8
        
        self.mm_to_px_ratio = 3.78 
        
        self.line_styles = GOST_STYLES.copy()
        self.dimension_styles = DEFAULT_DIMENSION_STYLES.copy()
        
        self.current_style_name = 'solid_main'
        self.current_dimension_style_name = 'gost_default'
        self.current_color = 'black'
        self.current_dxf_path = None
        self.current_dxf_saved_at = None

        self.circle_creation_method = 'center_radius'

        self.arc_creation_method = 'three_points'

        self.rectangle_creation_method = 'two_points'
        self.rectangle_corner_type = 'none'
        self.rectangle_corner_value = 0.0

        self.ellipse_creation_method = 'center_axes'
        
        self.polygon_creation_method = 'center_radius'
        self.polygon_variant = 'inscribed'
        self.polygon_sides = 5
        self.polygon_start_angle = 0.0

        self.editing_object = None
        self.editing_object_type = None
        
        self.snap_enabled = True
        self.snap_radius_px = 15
        
        self.snap_endpoint = True
        self.snap_midpoint = True
        self.snap_center = True
        
        self.snap_intersection = True
        self.snap_perpendicular = False
        self.snap_tangent = False
        self.snap_grid = False
        
        self.current_snap_point = None

    # ── Вспомогательные методы для слоёв ──

    def get_layer(self, name):
        """Найти слой по имени (или None)."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def is_layer_visible(self, name):
        """Виден ли слой с данным именем?"""
        layer = self.get_layer(name)
        return layer.visible if layer else True

    def add_layer(self, name):
        """Добавить новый слой. Возвращает True если добавлен."""
        if self.get_layer(name):
            return False
        self.layers.append(Layer(name))
        return True

    def delete_layer(self, name):
        """Удалить слой (кроме '0'). Возвращает True если удалён."""
        if name == "0":
            return False
        layer = self.get_layer(name)
        if not layer:
            return False
        # Перенести объекты со слоя на "0"
        for collection in (self.segments, self.circles, self.arcs,
                          self.rectangles, self.ellipses, self.polygons,
                          self.splines, self.points, self.dimensions):
            for obj in collection:
                if obj.layer == name:
                    obj.layer = "0"
        self.layers.remove(layer)
        if self.active_layer == name:
            self.active_layer = "0"
        return True
