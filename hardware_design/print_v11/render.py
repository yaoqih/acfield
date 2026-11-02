"""Static review images from exported triangles; not simulated motion."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

P = Path(__file__).parent
C = json.loads((P/'parameters.json').read_text())
d = np.load(P/'preview_meshes.npz')


def draw(ax, hidden=(), elev=38, azim=-57):
    for name in d.files:
        if name in hidden:
            continue
        tri = d[name]
        color = np.array([.20, .47, .54])
        alpha = 1.
        if name == 'battery':
            color = np.array([.88, .58, .23])
        elif 'controller' in name:
            color = np.array([.22, .56, .37])
        elif 'wheel' in name:
            color = np.array([.15, .16, .18])
        elif 'nylon' in name or 'bracket' in name:
            color = np.array([.89, .89, .85])
        elif any(s in name for s in ['motor', 'shaft', 'caster', 'support_ball']):
            color = np.array([.63, .67, .69])
        elif name == 'top_board':
            color = np.array([.86, .87, .81])
            alpha = .16
        n = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-9)
        shade = .5+.5*np.maximum(n@np.array([.3, -.4, .866]), 0)
        colors = np.column_stack([shade[:, None]*color, np.full(len(tri), alpha)])
        ax.add_collection3d(Poly3DCollection(tri, facecolors=colors, edgecolors='none'))
    ax.set(xlim=(-70, 70), ylim=(-70, 70), zlim=(0, 72), xlabel='X forward (mm)', ylabel='Y (mm)', zlabel='Z (mm)')
    ax.set_box_aspect((140, 140, 72))
    ax.view_init(elev, azim)


fig = plt.figure(figsize=(14, 6), facecolor='white')
ax = fig.add_subplot(121, projection='3d')
draw(ax)
ax.set_title('V11 | caster seating corrected to Z8 mm', pad=15)
ax = fig.add_subplot(122, projection='3d')
draw(ax, hidden=('top_board', 'controller_envelope'), elev=52)
ax.set_title('PCB hidden | low battery and rear drive axle', pad=15)
fig.tight_layout()
fig.savefig(P/'assembly_preview.png', dpi=170)
plt.close(fig)
fig = plt.figure(figsize=(9, 7))
ax = fig.add_subplot(111, projection='3d')
draw(ax, hidden=tuple(n for n in d.files if n != 'chassis'), elev=52)
ax.set_title('Printed chassis only | zero tall printed columns')
fig.tight_layout()
fig.savefig(P/'chassis_preview.png', dpi=150)
plt.close(fig)

v = json.loads((P/'stability_validation.json').read_text())
fig, axes = plt.subplots(1, 2, figsize=(13, 6), facecolor='white')
ax = axes[0]
ax.add_patch(Rectangle((-65, -65), 130, 130, fc='#f5f7f4', ec='#53727b', lw=2))
ax.add_patch(Rectangle((-50.5, -15.5), 73, 31, fc='#dcad66', ec='#b58034', lw=2, label='Battery, underside Z9.5'))
bc = C['board_outline_envelope_center_xy_mm']
bs = C['board_outline_envelope_xy_mm']
ax.add_patch(Rectangle((bc[0]-bs[0]/2, bc[1]-bs[1]/2), *bs,
                       fc='#58a179', ec='#296848', lw=2, alpha=.25,
                       label='PCB outline offset from mounting pattern, underside Z37'))
for s in [-1, 1]:
    ax.add_patch(Rectangle((-22.1, s*36-15.5), 12.2, 31, fc='#acb6ba', ec='#58676d'))
    ax.add_patch(Rectangle((-33, s*61-3.25), 34, 6.5, fc='#30383b'))
for x in [-5, 53]:
    for y in [-24.5, 24.5]:
        ax.add_patch(Circle((x, y), 3.4, fc='#e9e9e1', ec='#748479'))
ax.add_patch(Circle((44.8, 0), 20.1, fill=False, ec='#879499', lw=2, label='Caster flange under deck'))
ax.plot([-16, -16], [-61, 61], '--', color='#bd6248', label='Drive axle X=-16')
ax.scatter(*v['center_of_mass_mm'][:2], marker='x', color='#99433c', s=70, label='Estimated CG projection')
ax.set(xlim=(-71, 71), ylim=(-70, 70), xlabel='X forward (mm)', ylabel='Y (mm)', title='130 x 130 mm nominal component layout')
ax.set_aspect('equal')
ax.grid(alpha=.15)
ax.legend(fontsize=7, loc='upper left')
ax = axes[1]
ax.add_patch(Polygon([[-16, -61], [-16, 61], [44.8, 0]], fc='#edf5f5', ec='#277c8d', lw=2))
ax.scatter(*v['center_of_mass_mm'][:2], s=65, color='#3c778a', label='Estimated CG projection')
for r in v['scenarios']:
    ax.scatter(*r['effective_xy_mm'], s=14, color='#d69740')
ax.set(xlim=(-22, 53), ylim=(-69, 69), xlabel='X forward (mm)', ylabel='Y (mm)', title='Quasi-static ax/ay up to 0.6 m/s2')
ax.set_aspect('equal')
ax.grid(alpha=.15)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(P/'layout_and_stability.png', dpi=180)
plt.close(fig)

old = v['comparison_V9']
fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
for ax, title, vals in zip(axes,
                        ['Estimated CG height (mm)', 'Drive axle to caster (mm)', 'Minimum support margin (mm)'],
                        [[old['center_of_mass_mm'][2], v['center_of_mass_mm'][2]],
                         [old['drive_axle_to_caster_mm'], v['drive_axle_to_caster_mm']],
                         [old['minimum_quasistatic_support_margin_mm'], v['minimum_quasistatic_support_margin_mm']]]):
    ax.bar(['V9', 'V11'], vals, color=['#aab8bc', '#317e8f'], width=.55)
    for i, value in enumerate(vals):
        ax.text(i, value+.02*max(vals), f'{value:.2f}', ha='center')
    ax.set_title(title, fontsize=11)
    ax.set_ylim(0, max(vals)*1.2)
    ax.grid(axis='y', alpha=.15)
fig.suptitle('Nominal estimates only: no physical dynamics validation', fontsize=11)
fig.tight_layout()
fig.savefig(P/'comparison.png', dpi=150)
plt.close(fig)

# Actual triangles cut near caster X, including both bolt locations. A 0.0001mm
# offset avoids slicing exactly along tessellation vertices and shared edges.
fig, ax = plt.subplots(figsize=(11, 5))
families = [
    ('chassis', '#28788b', 'Printed chassis'),
    ('caster_flange_envelope', '#696e75', 'Caster flange'),
    ('caster_upper_envelope', '#a6a9ab', 'Upper housing envelope'),
    ('caster_lower_cap_envelope', '#a6a9ab', 'Lower cap envelope'),
    ('support_ball', '#d29a3d', '12 mm ball'),
]
families += [(name, '#418b61', 'M3x8 screw' if 'head' in name else None)
             for name in d.files if name.startswith('caster_screw')]
families += [(name, '#9565a6', '2.5 mm nylon nut')
             for name in d.files if name.startswith('caster_nut')]
used = set()
for name, color, label in families:
    tri = d[name]
    e0, e1 = tri, np.roll(tri, -1, axis=1)
    dx = e1[:, :, 0]-e0[:, :, 0]
    with np.errstate(divide='ignore', invalid='ignore'):
        t = (44.8001-e0[:, :, 0])/dx
    hit = (np.abs(dx)>1e-9)&(t>=0)&(t<=1)
    for i in np.flatnonzero(hit.sum(axis=1)==2):
        pts=e0[i,hit[i]]+t[i,hit[i],None]*(e1[i,hit[i]]-e0[i,hit[i]])
        text_label=label if label not in used else None
        ax.plot(pts[:,1],pts[:,2],color=color,lw=1.3,label=text_label)
        used.add(label)
ax.axhline(0,color='#444444',lw=1.5)
for z in [5,8,10]:
    ax.axhline(z,color='#a7afb3',ls='--',lw=.7)
ax.text(22,8.2,'Seating Z8',fontsize=9)
ax.text(22,10.2,'Head seat Z10',fontsize=9)
ax.text(-24,-1.7,'Screw tip Z2 | nut bottom Z2.5 | flange Z5..8 | nut protrusion 0.5 mm',fontsize=9)
ax.set(xlim=(-25,38),ylim=(-2.5,18),xlabel='Y (mm)',ylabel='Z above ground (mm)',
       title='V11 nominal caster section near X44.8 | dimensions from exported assembly')
ax.set_aspect('equal')
ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(1.01,1))
fig.tight_layout()
fig.savefig(P/'caster_section.png',dpi=180)
plt.close(fig)
