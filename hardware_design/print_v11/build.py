"""V11: compact two-part chassis with integrated bearing lands.

Units mm; nominal ground Z0. Install hardware_design/requirements.txt first.
All purchased-part envelopes remain assumptions pending first-article inspection.
"""
from pathlib import Path
import itertools
import json
import math
import numpy as np
import trimesh as tm

P = Path(__file__).parent
OUT = P/'stl'
OUT.mkdir(parents=True, exist_ok=True)
CFG = {
    'version': 'V11', 'status': 'DRAWING_BASED_FIRST_ARTICLE_REQUIRED',
    'body_size_mm': [130, 130], 'deck_bottom_z_mm': 9., 'deck_top_z_mm': 12.,
    'deck_thickness_mm': 3., 'wheel_diameter_mm': 34., 'wheel_width_mm': 6.5,
    'axle_x_mm': -16., 'axle_z_mm': 17., 'wheel_track_mm': 122.,
    'motor_center_abs_y_mm': 36., 'bracket_pitch_ASSUMED_mm': 18.5,
    'bracket_axle_above_mount_ASSUMED_mm': 5.,
    'bracket_ear_thickness_ASSUMED_mm': 2.5,
    'motor_screws': 'supplier M2x10 and nuts; verify actual size and head',
    'motor_ratio': 'A12 12V 1:150',
    'motor_body_max_length_drawing_mm': 29.5,
    'motor_shaft_length_drawing_mm': [10., .3],
    'motor_body_envelope_conservative_mm': [12.5, 31., 12.],
    'encoder_counts_per_output_rev': None,
    'encoder_drawing_conflict': 'new drawing says 3 pole pairs; previous listing says 7PPR; PIN5 label GND conflicts with VCC function',
    'caster_x_mm': 44.8, 'caster_pitch_ASSUMED_mm': 28.,
    'caster_overall_height_drawing_mm': 15.,
    'caster_original_lower_flange_face_above_housing_bottom_mm': 7.,
    'caster_flange_thickness_drawing_mm': 3., 'caster_flange_top_z_mm': 8.,
    'caster_local_deck_bottom_z_mm': 8., 'caster_head_seat_z_mm': 10.,
    'caster_center_bore_mm': 22.6,
    'caster_fastening': 'M3x8 head above recessed deck; nylon nut below flange; no washer',
    'caster_flange_d_mm': 40.2, 'caster_upper_d_ASSUMED_mm': 22.,
    'battery_center_xy_mm': [-14., 0.],
    'battery_body_ASSUMED_mm': [73., 31., 24.],
    'battery_dimension_basis': 'user supplied this screenshot as selected battery dimensions; nominal 73x31x24mm and 138g +/-15g; actual XT60 and lead space still inspect',
    'battery_fit_clear_xy_mm': [81., 39.],
    'battery_floor_z_mm': 9., 'battery_floor_thickness_mm': 3.,
    'minimum_print_ground_clearance_mm': 6., 'battery_pad_mm': .5,
    'board_mount_pattern_center_xy_mm': [24., 0.],
    'board_outline_envelope_center_xy_mm': [24., 4.5],
    'board_outline_envelope_xy_mm': [65.02, 65.02],
    'board_outline_source': 'official mechanical DXF; 90deg installed rotation; outline offset from hole-pattern center, not measured mass center',
    'board_hole_pitch_mm': [58., 49.],
    'board_bottom_z_mm': 37., 'board_thickness_ASSUMED_mm': 1.6,
    'board_component_envelope_height_ASSUMED_mm': 20.,
    'board_post_length_mm': 25., 'board_posts': '4 bought M3 female-female nylon',
    'top_post_length_mm': 50., 'top_posts': '4 bought M3 female-female nylon',
    'post_AF_ASSUMED_mm': 6., 'post_threads': 'through M3 or usable depth >=7mm each end',
    'post_pitch_mm': 121., 'top_plate_thickness_mm': 2.6, 'tag_z_mm': 64.6,
    'tag_black_border_mm': 90., 'tag_outer_white_mm': 112.5,
    'main_screws': '18 M3x8 nylon Phillips pan-head per robot; user confirmed nut thickness2.5mm',
    'M3_screw_head_d_drawing_mm': 5.6, 'M3_screw_head_h_drawing_mm': 2.5,
    'lower_post_washer_nominal_mm': [3., 6., .3],
    'caster_nut_AF_ENVELOPE_mm': 5.5, 'caster_nut_thickness_user_mm': 2.5,
    'M3_nuts_per_robot': 2, 'M3_flat_washers_per_robot': 8,
    'initial_limits': {'v_m_s': .10, 'omega_rad_s': .30, 'a_m_s2': .30},
    'print_process': {
        'material': 'PETG', 'nozzle_mm': .4, 'layer_height_mm': .20,
        'walls': 4, 'top_bottom_layers': 5,
        'uniform_infill': '40% Gyroid or Cubic',
        'reason': 'geometry carries local loads; uniform slicer setting required',
    },
    'geometry_revision': 'V11 rounded pocket, integrated M2 bearing lands, parameterized top plate',
}
(P/'parameters.json').write_text(json.dumps(CFG, indent=2)+'\n')
AXLE = CFG['axle_x_mm']
MY = CFG['motor_center_abs_y_mm']
CY = CFG['caster_x_mm']
BX, BY = CFG['battery_center_xy_mm']
BOARD_HOLES = list(itertools.product([-5., 53.], [-24.5, 24.5]))
TOP_HOLES = list(itertools.product([-60.5, 60.5], repeat=2))
MOTOR_HOLES = [(AXLE+dx, s*MY) for s in [-1, 1] for dx in [-9.25, 9.25]]
CASTER_HOLES = [(CY, -14), (CY, 14)]


def box(size, center):
    m = tm.creation.box(extents=size)
    m.apply_translation(center)
    return m


def cyl(d, h, center):
    m = tm.creation.cylinder(radius=d/2, height=h, sections=64)
    m.apply_translation(center)
    return m


def union(parts):
    return tm.boolean.union(parts, engine='manifold')


def diff(part, cuts):
    return tm.boolean.difference([part, *cuts], engine='manifold')


def rounded_rect(w, d, r, z, h, xy=(0, 0)):
    x, y = xy
    return union([box([w-2*r, d, h], [x, y, z]), box([w, d-2*r, h], [x, y, z]),
                  *[cyl(2*r, h, [x+sx*(w/2-r), y+sy*(d/2-r), z])
                    for sx, sy in itertools.product([-1, 1], repeat=2)]])


def slot(x, y, length=4., d=2.4):
    a = (length-d)/2
    return union([cyl(d, 40, [x-a, y, 15]), cyl(d, 40, [x+a, y, 15]),
                  box([length-d, d, 40], [x, y, 15])])


def nylon_post(length, xy, af=6.):
    # Flat faces face +/-Y, leaving clearance to original motor hoops.
    m = tm.creation.cylinder(radius=af/math.sqrt(3), height=length, sections=6)
    m.apply_translation([*xy, 12+length/2])
    return diff(m, [cyl(3, length+2, [*xy, 12+length/2])])


# Flat main deck; shallow drop only under the heavy battery. No tall printed
# board columns or captured board nuts are created anywhere in this model.
base = rounded_rect(130, 130, 7, 10.5, 3)
# Rounded openings keep a continuous stress path at the motor and corner
# cut-outs; the outside footprint and wheel clearance are unchanged.
cuts = [rounded_rect(44, 22, 4, 15, 40, (AXLE, s*62)) for s in [-1, 1]]
cuts += [rounded_rect(22, 18, 3, 15, 40, (x, s*49))
         for x in [-43, 43] for s in [-1, 1]]
# Battery pocket opening; a continuous lowered floor is joined by perimeter walls.
cuts += [rounded_rect(81, 39, 4, 15, 40, (BX, BY))]
base = diff(base, cuts)
pan = diff(rounded_rect(87, 45, 4, 9, 6, (BX, BY)),
           [rounded_rect(81, 39, 4, 13, 8, (BX, BY))])  # floor Z6..9; walls Z9..12
ribs = [box([2.4, 116, 3], [x, 0, 13.5]) for x in [-61.5, 61.5]]
ribs += [box([116, 2.4, 3], [0, y, 13.5]) for y in [-61.5, 61.5]]
stops = [box([65, 2, 3], [BX, y, 13.5]) for y in [-20.5, 20.5]]
stops += [box([2, 12, 3], [BX-41.5, 0, 13.5])]
stops += [box([2, 8, 3], [BX+41.5, y, 13.5]) for y in [-14, 14]]
# This annular support lowers the caster contact face to Z8. Head pockets below
# leave 2mm of print under each screw, retaining the common M3x8 length.
caster_pad = cyl(40.2, 4, [CY, 0, 10])
main = union([base, pan, *ribs, *stops, caster_pad])
# Cut the motor-body relief before adding local bearing lands. The lands stop
# at the assumed motor-envelope underside, so the drawing-based clearance
# check remains valid while the 3 mm deck carries the screw head load.
motor_reliefs = [box([13.2, 33, 8], [AXLE, s*MY, 14.8]) for s in [-1, 1]]
main = diff(main, motor_reliefs)
motor_bosses = [cyl(8, 1.8, [x, y, 10.0]) for x, y in MOTOR_HOLES]
# Flush lands document the bearing zones for a uniform-infill print; they do
# not raise the deck or change the bought post heights.
post_bosses = [cyl(8, 3, [x, y, 10.5]) for x, y in TOP_HOLES+BOARD_HOLES]
main = union([main, *motor_bosses, *post_bosses])
holes = [rounded_rect(44, 22, 4, 15, 40, (AXLE, s*62)) for s in [-1, 1]]
holes += [slot(x, y) for x, y in MOTOR_HOLES]
# Original drawing is ball-up: total15, lower flange face7, thickness3.
# Turn ball-down: ground=0, flange Z5..8, body top15. Clear below Z8,
# not the old Z10. Local head seats are Z10, so the print stack remains2.
holes += [cyl(CFG['caster_center_bore_mm'], 40, [CY, 0, 15]),
          cyl(42, 20, [CY, 0, -2])]
holes += [cyl(6.2, 20, [x, y, 20]) for x, y in CASTER_HOLES]
holes += [cyl(3.6, 40, [x, y, 15]) for x, y in CASTER_HOLES]
holes += [cyl(3.4, 40, [x, y, 15]) for x, y in TOP_HOLES+BOARD_HOLES]
# All bought posts bear directly on Z12; remove only the rib above the deck,
# preserving the integrated Ø8 bearing land in the 3 mm deck.
holes += [cyl(9, 3, [x, y, 13.5]) for x, y in TOP_HOLES+BOARD_HOLES]
# Washer bearing face Z9 stays clear of the lowered battery pocket walls.
holes += [cyl(8, 4, [x, y, 7]) for x, y in BOARD_HOLES]
# A strap wraps over battery width; slots lie outside the body edges.
holes += [box([12, 2.4, 40], [BX, y, 15]) for y in [-18.3, 18.3]]
holes += [box([6, 2, 40], [x, y, 15]) for x, y in [(15, -31), (51, 29), (-46, 28)]]
main = diff(main, holes)

# Parameterized top plate: a 1 mm flat tag face, 1.6 mm underside grid ribs,
# and Ø8 x 2.6 mm solid bearing lands around the four M3 holes. This keeps the
# tag face at the same height while avoiding a hidden dependency on an old STL.
plate = union([
    box([130, 130, 1], [0, 0, 2.1]),
    *[box([130, 1.6, 1.6], [0, y, .8]) for y in [-60.5, -30, 0, 30, 60.5]],
    *[box([1.6, 130, 1.6], [x, 0, .8]) for x in [-60.5, -30, 0, 30, 60.5]],
    *[cyl(8, 2.6, [x, y, 1.3]) for x, y in TOP_HOLES],
])
plate = diff(plate, [cyl(3.4, 15, [x, y, 2]) for x, y in TOP_HOLES])
models = {'chassis_130mm_rear_axle': main, 'tag_plate_130mm': plate}
report = {}
for name, m in models.items():
    m.process(validate=True)
    assert m.is_watertight and m.is_volume and m.body_count == 1, (name, m.body_count)
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    m.export(OUT/f'{name}.stl')
    report[name] = {'size_mm': m.extents.tolist(), 'volume_cm3': float(m.volume/1000),
                    'solid_petg_mass_g': float(m.volume*.00127),
                    'watertight': bool(m.is_watertight), 'positive_volume': bool(m.is_volume),
                    'connected_bodies': int(m.body_count), 'triangles': len(m.faces)}
(P/'mesh_validation.json').write_text(json.dumps(report, indent=2)+'\n')

assembly = []
def place(name, m, xyz=(0, 0, 0), kind='bought_envelope'):
    m = m.copy()
    m.apply_translation(xyz)
    assembly.append((name, m, kind))


place('chassis', models['chassis_130mm_rear_axle'], [0, 0, 6], 'print')
for side in [-1, 1]:
    place(f'motor_{side}', box(CFG['motor_body_envelope_conservative_mm'], [AXLE, side*MY, 17]))
    shaft = cyl(3, 10, [0, 0, 0])
    shaft.apply_transform(tm.transformations.rotation_matrix(math.pi/2, [1, 0, 0]))
    place(f'shaft_{side}', shaft, [AXLE, side*(MY+20.5), 17])
    wheel = cyl(34, 6.5, [0, 0, 0])
    wheel.apply_transform(tm.transformations.rotation_matrix(math.pi/2, [1, 0, 0]))
    place(f'wheel_{side}', wheel, [AXLE, side*61, 17])
    outer = box([14.5, 14.5, 11.3], [AXLE, side*MY, 17.65])
    inner = box([12, 16, 10.1], [AXLE, side*MY, 16.95])
    ears = [box([5, 14.5, 2.5], [AXLE+dx, side*MY, 13.25]) for dx in [-9.25, 9.25]]
    bracket = diff(union([diff(outer, [inner]), *ears]),
                   [cyl(2.2, 20, [AXLE+dx, side*MY, 13]) for dx in [-9.25, 9.25]])
    place(f'original_bracket_{side}_ASSUMED', bracket)
place('battery', box([73, 31, 24], [BX, 0, 21.5]))
place('controller_envelope', box([*CFG['board_outline_envelope_xy_mm'], 20],
                                 [*CFG['board_outline_envelope_center_xy_mm'], 47]))
for x, y in BOARD_HOLES:
    place(f'board_nylon_{x}_{y}', nylon_post(25, (x, y)))
for x, y in TOP_HOLES:
    place(f'top_nylon_{x}_{y}', nylon_post(50, (x, y)))
place('support_ball', tm.creation.icosphere(subdivisions=3, radius=6), [CY, 0, 6])
place('caster_upper_envelope', cyl(22, 7, [CY, 0, 11.5]))
# Conservative envelope of the raised cone on the ball side of the flange.
# The drawing gives maximum diameter22; retain this bound over nut height.
place('caster_lower_cap_envelope', cyl(22, 2.5, [CY, 0, 3.75]))
flange = diff(cyl(40.2, 3, [CY, 0, 6.5]),
              [cyl(20, 5, [CY, 0, 6.5]), *[cyl(3.5, 5, [x, y, 6.5]) for x, y in CASTER_HOLES]])
place('caster_flange_envelope', flange)
for x,y in CASTER_HOLES:
    place(f'caster_screw_head_{y}', cyl(5.6, 2.5, [x,y,11.25]))
    place(f'caster_screw_shank_{y}', cyl(3, 8, [x,y,6]))
    nh=CFG['caster_nut_thickness_user_mm'];nz=5-nh/2
    n = tm.creation.cylinder(radius=CFG['caster_nut_AF_ENVELOPE_mm']/math.sqrt(3),height=nh,sections=6)
    n.apply_translation([x,y,nz])
    n = diff(n,[cyl(3,5,[x,y,nz])])
    place(f'caster_nut_{y}_ENVELOPE',n)
top = plate.copy()
# The continuous tag face is the high-Z side of the printable plate. Keep
# ribs below it; flipping the plate puts the ribs above the tag surface.
place('top_board', top, [0, 0, CFG['tag_z_mm']-CFG['top_plate_thickness_mm']], 'print')
scene = tm.Scene()
for name, m, kind in assembly:
    m.visual.face_colors = [60, 130, 150, 255] if kind == 'print' else [170, 172, 165, 255]
    scene.add_geometry(m, node_name=name, geom_name=name)
scene.export(P/'assembly.glb')
np.savez(P/'preview_meshes.npz', **{n: m.triangles for n, m, _ in assembly})
print(json.dumps({'version': 'V11', 'STL_count': len(models),
                  'solid_print_mass_g': sum(r['solid_petg_mass_g'] for r in report.values()),
                  'printed_board_columns': 0}, indent=2))
