import ezdxf

doc = ezdxf.readfile('dxf_files/импорт5.dxf')
msp = doc.modelspace()

for insert in msp.query('INSERT'):
    insert.explode()

polylines = msp.query('POLYLINE')
lwpolylines = msp.query('LWPOLYLINE')

print(f"Polylines found: {len(polylines)}")
print(f"LWPolylines found: {len(lwpolylines)}")

for p in polylines:
    print(f"\nPOLYLINE:")
    print(f"Type: {p.dxftype()}")
    print(f"Flags: {p.dxf.flags}")
    print(f"Is 2d polyline: {p.is_2d_polyline}")
    print(f"Is 3d polyline: {p.is_3d_polyline}")
    print(f"Is closed: {p.is_closed}")
    print(f"Is polygon mesh: {p.is_polygon_mesh}")
    print(f"Is polyface mesh: {p.is_poly_face_mesh}")
    
    if hasattr(p, 'is_spline_fit_polyline'):
        print(f"Is spline fit: {p.is_spline_fit_polyline}")
    if hasattr(p, 'is_spline_control_frame'):
        print(f"Is control frame: {p.is_spline_control_frame}")
    
    verts = list(p.vertices())
    print(f"Vertices total: {len(verts)}")
    
    cnt_control = 0
    cnt_fit = 0
    for v in verts:
        if hasattr(v.dxf, 'flags'):
             # 8 = spline fit vertex, 16 = spline control point
             if v.dxf.flags & 8: cnt_fit += 1
             if v.dxf.flags & 16: cnt_control += 1
    
    print(f"Fit points: {cnt_fit}, Control points: {cnt_control}")
