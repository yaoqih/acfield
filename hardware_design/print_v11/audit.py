"""Export-based V11 geometry, bearing and quasi-static estimate checks.

No slicing, strength, friction or experimental dynamics verification.
"""
from pathlib import Path
import itertools
import json
import math
import numpy as np
import trimesh as tm

P = Path(__file__).parent
C = json.loads((P/'parameters.json').read_text())
scene = tm.load(P/'assembly.glb', force='scene')
parts = {}
for name in scene.graph.nodes_geometry:
    transform, geom = scene.graph[name]
    parts[name] = scene.geometry[geom].copy()
    parts[name].apply_transform(transform)


def cyl(d, h, xyz):
    m = tm.creation.cylinder(radius=d/2, height=h, sections=48)
    m.apply_translation(xyz)
    return m


def box(size, center):
    m = tm.creation.box(extents=size)
    m.apply_translation(center)
    return m


def washer(x, y, z):
    # Latest cart M3 x OD6 x 0.3; this nominal bore is not a clearance fit test.
    inner, outer, height = C['lower_post_washer_nominal_mm']
    return tm.boolean.difference([cyl(outer, height, [x, y, z]),
                                  cyl(inner, 1, [x, y, z])], engine='manifold')


def volume(a, b):
    m = tm.boolean.intersection([a, b], engine='manifold')
    return 0. if m is None or len(m.faces) == 0 else abs(float(m.volume))


rows = []
def clear(label, a, b):
    v = volume(a, b)
    rows.append({'check': label, 'intersection_mm3': v, 'pass': v < .02})


def minimum(label, value, threshold):
    rows.append({'check': label, 'value': float(value), 'minimum': threshold,
                 'pass': bool(value >= threshold)})


def maximum(label, value, threshold):
    rows.append({'check': label, 'value': float(value), 'maximum': threshold,
                 'pass': bool(value <= threshold)})


CH = parts['chassis']
AX = C['axle_x_mm']
CY = C['caster_x_mm']
MY = C['motor_center_abs_y_mm']
MOTOR_HOLES = [(AX + dx, s*MY) for s in [-1, 1] for dx in [-9.25, 9.25]]
board = list(itertools.product([-5., 53.], [-24.5, 24.5]))
top = list(itertools.product([-60.5, 60.5], repeat=2))
for name, m in parts.items():
    if name in ['chassis', 'top_board']:
        continue
    clear(name+' / chassis', m, CH)
for a, b in [('battery', 'controller_envelope'), ('battery', 'caster_upper_envelope'),
             ('battery', 'caster_lower_cap_envelope'),
             ('battery', 'caster_flange_envelope'), ('battery', 'support_ball'),
             ('battery', 'motor_-1'), ('battery', 'motor_1'),
             ('battery', 'original_bracket_-1_ASSUMED'), ('battery', 'original_bracket_1_ASSUMED'),
             ('controller_envelope', 'top_board'), ('battery', 'top_board')]:
    clear(a+' / '+b, parts[a], parts[b])
for family, holes, length in [('board', board, 25), ('top', top, 50)]:
    for x, y in holes:
        pole = parts[f'{family}_nylon_{x}_{y}']
        for other in ['battery', 'controller_envelope', 'top_board', 'motor_-1', 'motor_1',
                      'original_bracket_-1_ASSUMED', 'original_bracket_1_ASSUMED',
                      'caster_upper_envelope', 'caster_lower_cap_envelope', 'caster_flange_envelope']:
            clear(f'{family} nylon {x},{y} / {other}', pole, parts[other])
        clear(f'{family} lower bolt passage {x},{y}', cyl(3, 8, [x, y, 12.5]), CH)
        w = washer(x, y, 9-C['lower_post_washer_nominal_mm'][2]/2)
        clear(f'{family} lower washer {x},{y}', w, CH)
        if family == 'board':
            clear(f'PCB upper bolt passage {x},{y}', cyl(3, 8, [x, y, 34.6]), pole)
            # Any printed part above the foot would recreate an unwanted column.
            clear(f'no printed PCB column {x},{y}', cyl(8, 20, [x, y, 26]), CH)
        else:
            clear(f'top M3 passage {x},{y}', cyl(3, 8, [x, y, 60.6]), parts['top_board'])
        pressed = pole.copy()
        pressed.apply_translation([0, 0, -.2])
        minimum(f'{family} nylon foot bearing volume over 0.2mm {x},{y}', volume(pressed, CH), 3.8)

for y in [-14, 14]:
    n = parts[f'caster_nut_{y}_ENVELOPE']
    for other in ['chassis', 'battery', 'caster_upper_envelope', 'caster_lower_cap_envelope']:
        clear(f'caster nut {y} / {other}', n, parts[other])
    clear(f'caster screw {y}', parts[f'caster_screw_shank_{y}'], CH)
    head=parts[f'caster_screw_head_{y}']
    clear(f'caster head {y} / housing', head, parts['caster_upper_envelope'])
    clear(f'caster head {y} / flange', head, parts['caster_flange_envelope'])
    clear(f'caster nut {y} / ball', n, parts['support_ball'])
    clear(f'caster nut {y} / flange', n, parts['caster_flange_envelope'])
    pressed=head.copy();pressed.apply_translation([0,0,-.2])
    minimum(f'caster screw head {y} bearing volume over0.2mm',volume(pressed,CH),2.)
    minimum(f'caster nut {y} ground clearance mm',float(n.bounds[0,2]),2.5)
    minimum(f'caster screw tip {y} ground clearance mm',float(parts[f'caster_screw_shank_{y}'].bounds[0,2]),2.)
for side in [-1, 1]:
    for dx in [-9.25, 9.25]:
        clear(f'M2x10 passage {side},{dx}', cyl(2, 10, [AX+dx, side*MY, 14]), CH)

# V11 local lands are checked at their actual bearing faces. The probes keep
# the fastener void open, so this verifies material around the hole rather
# than merely counting the hole volume itself.
for x, y in MOTOR_HOLES:
    outer = cyl(8, .2, [x, y, 9.2])
    void = cyl(2.4, .4, [x, y, 9.2])
    probe = tm.boolean.difference([outer, void], engine='manifold')
    minimum(f'V11 M2 bearing land {x},{y}', volume(probe, CH), 3.)
for x, y in top:
    outer = cyl(8, .2, [x, y, 62.1])
    void = cyl(3.4, .4, [x, y, 62.1])
    probe = tm.boolean.difference([outer, void], engine='manifold')
    minimum(f'V11 top bearing land {x},{y}', volume(probe, parts['top_board']), 3.)

# The battery footprint, excluding small strap slots, must be backed by floor.
floor_probe = box([73, 31, .2], [-14, 0, 8.9])
floor_area = volume(floor_probe, CH)/.2
minimum('battery supported floor fraction excluding strap slots', floor_area/(73*31), .98)
minimum('battery to PCB underside gap mm', 37-33.5, 3)
minimum('PCB top to tag ribs gap mm', 62-57, 4)
minimum('minimum printed ground clearance mm', float(CH.bounds[0, 2]), 6-1e-5)
maximum('no printed tall board columns; chassis highest Z mm', float(CH.bounds[1, 2]), 15.001)
minimum('lower post M3x8 thread engagement mm', 8-3-C['lower_post_washer_nominal_mm'][2], 4)
maximum('PCB upper M3x8 thread engagement mm', 8-1.6, 7)
minimum('upper tag M3x8 thread engagement mm', 8-2.6, 4)
minimum('caster M3x8 protrusion mm no washers', 8-3-2-C['caster_nut_thickness_user_mm'], .5)
minimum('motor M2x10 protrusion mm assumed ear2.5', 10-3-2.5-1.6, .5)
minimum('caster screw head to housing radial gap mm', 14-5.6/2-11, .19)
minimum('caster nut flat to maximum22mm housing bound gap mm',14-C['caster_nut_AF_ENVELOPE_mm']/2-11,.24)
minimum('caster ball-down working height mm', C['caster_flange_top_z_mm'], 15-7)
maximum('caster ball-down working height mm', C['caster_flange_top_z_mm'], 15-7)
minimum('caster center bore radial housing clearance mm',C['caster_center_bore_mm']/2-11,.29)
for y in [-14,14]:
    minimum(f'caster flange supported underside bearing {y}',
            volume(cyl(5.6,.2,[CY,y,8.1]),CH),2.)
minimum('battery to caster flange forward gap mm', CY-20.1-(-14+73/2), 2)
minimum('wheel outer edge to body outer edge mm', 65-(61+6.5/2), .5)
xy = np.vstack([m.bounds for m in parts.values()])[:, :2]
maximum('modeled footprint X mm', np.ptp(xy[:, 0]), 130.01)
maximum('modeled footprint Y mm', np.ptp(xy[:, 1]), 130.01)
meshes = []
for f in sorted((P/'stl').glob('*.stl')):
    m = tm.load(f, force='mesh')
    meshes.append({'file': f.name, 'watertight': bool(m.is_watertight),
                   'positive_volume': bool(m.is_volume), 'bodies': int(m.body_count)})
    assert m.is_watertight and m.is_volume and m.body_count == 1
assert len(meshes) == 2
report = {'status': 'PASS' if all(r['pass'] for r in rows) else 'FAIL',
          'release_status': C['status'],
          'scope': 'nominal user drawings plus user-confirmed nut thickness2.5mm; hardware tolerances and real assembly not tested',
          'checks': rows, 'meshes': meshes,
          'physical_inspection_required': ['selected G-tech battery size/mass and lead exits',
                                           'actual motor bracket height, ear thickness and M2 hardware',
                                           'wheel hub insertion and retention',
                                           'caster dimensions against supplied drawing, ball-down operation/drag and nominal28mm pitch',
                                           'board backside components, real connector/antenna envelopes',
                                           'nylon nut AF5.5mm assumed and thickness2.5mm user-confirmed; screw/nut actual tolerances, post AF/thread depths; entire tool access',
                                           'slicer support, print strength, joint stiffness and road tests']}
(P/'assembly_audit.json').write_text(json.dumps(report, indent=2)+'\n')


def box_izz(mass, l, w):
    return mass*(l*l+w*w)/12


# Entries: name, mass_g, x_mm, y_mm, z_mm, intrinsic Izz_gmm2.
entries = []
for name in ['chassis', 'top_board']:
    m = parts[name]
    entries.append([name, float(m.volume*.00127), *m.center_mass,
                    float(m.moment_inertia[2, 2]*.00127)])
for name, m in parts.items():
    if '_nylon_' in name:
        entries.append([name+'_ESTIMATE', float(m.volume*.00115), *m.center_mass,
                        float(m.moment_inertia[2, 2]*.00115)])
entries += [
    ['battery_ASSUMED', 138, -14, 0, 21.5, box_izz(138, 73, 31)],
    # Mass center is unknown: retain the declared hole-center estimate. The
    # verified outline offset does not establish the PCB/component mass center.
    ['controller_ESTIMATE', 40, 24, 0, 46, box_izz(40, 65, 65)],
    ['motorL_ESTIMATE', 13, AX, MY, 17, box_izz(13, 12.2, 31)],
    ['motorR_ESTIMATE', 13, AX, -MY, 17, box_izz(13, 12.2, 31)],
    ['wheelL_ESTIMATE', 8, AX, 61, 17, box_izz(8, 34, 6.5)],
    ['wheelR_ESTIMATE', 8, AX, -61, 17, box_izz(8, 34, 6.5)],
    ['caster', 20, CY, 0, 8, 20*20.1**2/2],
    ['paper_label_ESTIMATE', 2, 0, 0, 64.7, box_izz(2, 112.5, 112.5)],
    ['clips_ESTIMATE', 12, AX, 0, 18, box_izz(12, 25, 72)],
    ['wire_fuse_ESTIMATE', 30, 20, 0, 20, box_izz(30, 35, 20)],
    ['fasteners_strap_pad_ESTIMATE', 22, 0, 0, 25, box_izz(22, 70, 70)]
]
mass = sum(r[1] for r in entries)
cg = np.array([sum(r[1]*r[j] for r in entries)/mass for j in [2, 3, 4]])
izz = sum(r[5]+r[1]*((r[2]-cg[0])**2+(r[3]-cg[1])**2) for r in entries)*1e-9
length = CY-AX
halftrack = 61.


def support(x, y, z, ax, ay, axle=AX, caster=CY, half=halftrack):
    xe = x-z*ax/9.81
    ye = y-z*ay/9.81
    span = caster-axle
    n_caster = (xe-axle)/span
    n_left = (1-n_caster+ye/half)/2
    n_right = (1-n_caster-ye/half)/2
    margin = min(xe-axle, (half*(1-n_caster)-abs(ye))/math.sqrt(1+(half/span)**2))
    return {'effective_xy_mm': [float(xe), float(ye)], 'support_margin_mm': float(margin),
            'normal_load_fractions': {'caster': float(n_caster), 'left': float(n_left), 'right': float(n_right)},
            'inside_support_triangle': bool(min(n_caster, n_left, n_right) > 0)}


scenarios = []
for ax, ay in itertools.product([-.6, -.3, 0, .3, .6], repeat=2):
    scenarios.append({'ax_m_s2': ax, 'ay_m_s2': ay, **support(*cg, ax, ay)})
static = support(*cg, 0, 0)['normal_load_fractions']
old = json.loads((P/'previous_design_reference.json').read_text())
old_cg = old['center_of_mass_mm']
old_tip_accel = 9.81*(old_cg[0]+16)/old_cg[2]
tip_accel = 9.81*(cg[0]-AX)/cg[2]

# Sensitivity sweep of poorly known component weights/locations. These are
# declared engineering ranges, NOT statistically validated confidence bounds.
sensitivity = []
base_without_battery_board = [r for r in entries if r[0] not in ['battery_ASSUMED', 'controller_ESTIMATE']]
for bm, cm, dx, dz in itertools.product([123, 138, 153], [30, 40, 50], [-3, 0, 3], [0, 3]):
    trial = [*base_without_battery_board,
             ['battery', bm, -14+dx, 0, 21.5+dz], ['controller', cm, 24, 0, 46+dz]]
    trial_mass = sum(r[1] for r in trial)
    xyz = [sum(r[1]*r[j] for r in trial)/trial_mass for j in [2, 3, 4]]
    for ax, ay in itertools.product([-.6, .6], repeat=2):
        sensitivity.append(support(*xyz, ax, ay))

axle_study = []
for proposed in [-4, -8, -12, -16, -20, -24]:
    tx = cg[0]+54/mass*(proposed-AX)
    a = support(tx, cg[1], cg[2], .6, .6, axle=proposed)
    axle_study.append({'axle_x_mm': proposed, 'estimated_cg_x_mm': float(tx),
                       'caster_static_load_fraction': (tx-proposed)/(CY-proposed),
                       'support_margin_mm_at_ax_ay_0_6': a['support_margin_mm'],
                       'geometry_validated': proposed == AX})
print_mass = sum(r[1] for r in entries if r[0] in ['chassis', 'top_board'])
validation = {
    'status': 'ESTIMATED_NOT_PHYSICALLY_VALIDATED', 'mass_g': mass,
    'center_of_mass_mm': cg.tolist(), 'yaw_inertia_estimate_kg_m2': izz,
    'solid_print_mass_g': print_mass, 'mass_inputs': entries,
    'drive_axle_to_caster_mm': length, 'static_normal_load_fractions': static,
    'minimum_quasistatic_support_margin_mm': min(r['support_margin_mm'] for r in scenarios),
    'scenarios': scenarios,
    'ideal_forward_acceleration_to_lift_caster_m_s2': float(tip_accel),
    'ideal_pure_lateral_acceleration_limit_m_s2': float(9.81*halftrack*(1-static['caster'])/cg[2]),
    'axle_position_study_fixed_other_parts': axle_study,
    'sensitivity': {'battery_mass_g': [123, 138, 153], 'controller_mass_g': [30, 40, 50],
                     'battery_x_variation_mm': [-3, 0, 3], 'component_height_extra_mm': [0, 3],
                     'ax_ay_m_s2': [-.6, .6], 'cases': len(sensitivity),
                     'all_inside_support': all(r['inside_support_triangle'] for r in sensitivity),
                     'minimum_support_margin_mm': min(r['support_margin_mm'] for r in sensitivity),
                     'meaning': 'chosen ranges only, not universal tolerance or probability'},
    'comparison_V9': {'mass_g': old['mass_g'], 'center_of_mass_mm': old_cg,
                       'solid_print_mass_g': old['solid_print_mass_g'],
                       'drive_axle_to_caster_mm': old['drive_axle_to_caster_mm'],
                       'minimum_quasistatic_support_margin_mm': old['minimum_quasistatic_support_margin_mm'],
                       'caster_static_load_fraction': old['static_normal_load_fractions']['caster'],
                       'ideal_forward_acceleration_to_lift_caster_m_s2': old_tip_accel,
                       'CG_height_reduction_mm': old_cg[2]-float(cg[2])},
    'limitations': ['solid CAD PETG and assumed purchased masses; not weighed or sliced',
                    'quasi-static rigid-body calculation; no impact, tilt, compliance or friction model',
                    'tip acceleration is not a recommended driving limit; grip/sliding may limit first',
                    'regeneration, wheel PID and braking behavior not tested',
                    'caster friction and rocking must be checked at actual load',
                    'height sensitivity does not establish those components physically fit']}
(P/'stability_validation.json').write_text(json.dumps(validation, indent=2)+'\n')
print(json.dumps({'geometry_status': report['status'], 'checks': len(rows),
                  'failures': [r for r in rows if not r['pass']], 'mass_g': mass,
                  'CG_mm': cg.tolist(), 'static_loads': static,
                  'min_support_margin_mm': validation['minimum_quasistatic_support_margin_mm'],
                  'height_reduction_mm': validation['comparison_V9']['CG_height_reduction_mm'],
                  'sensitivity_worst_mm': validation['sensitivity']['minimum_support_margin_mm']}, indent=2))
assert all(r['pass'] for r in rows)
assert all(r['inside_support_triangle'] for r in scenarios)
assert validation['sensitivity']['all_inside_support']
