from logic.styles import GOST_STYLES

class AppState:
    def __init__(self):
        self.app_mode = 'IDLE'
        
        self.segments = []
        self.circles = []
        self.arcs = []
        self.rectangles = []
        self.ellipses = []
        self.polygons = []
        self.splines = []

        self.selected_segments = []
        self.selected_circles = []
        self.selected_arcs = []
        self.selected_rectangles = []
        self.selected_ellipses = []
        self.selected_polygons = []
        self.selected_splines = []

        self.preview_segment = None
        self.preview_circle = None
        self.preview_arc = None
        self.preview_rectangle = None
        self.preview_ellipse = None
        self.preview_polygon = None
        self.preview_spline = None
        self.spline_control_points = []
        self.points_clicked = 0
        self.active_p1 = None
        self.active_p2 = None
        self.active_p3 = None
        self.active_p4 = None
        
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
        
        self.current_style_name = 'solid_main'
        self.current_color = 'black'

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
