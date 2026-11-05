"""Review committed 95 mm DXFs and regenerate nominal layout/exploded figures.

Run from the repo root:
  uv run --with ezdxf --with shapely python hardware_design/acrylic_95/review.py

No supplier CAD, network access or absolute user paths are required. Derived
controller envelopes are historical inputs, not newly measured components.
This checks declared geometry; it does not certify strength or physical fit.
"""
from pathlib import Path
from itertools import combinations
from zipfile import ZipFile
import hashlib
import json
import math

import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import triangulate

P = Path(__file__).resolve().parent
AXLE, CASTER, TRACK = -30.5, 26.5, 73.5
POSTS = [(x, y) for x in (-43., 43.) for y in (-27.5, 27.5)]
HANGERS = [(x, y) for x in (-24.5, 24.5) for y in (-29., 29.)]
BOTTOM = "bottom_plate_95.1x80_flat_4mm.dxf"
TOP = "top_plate_95x80_flat_2mm.dxf"


def read_plate(filename):
    doc = ezdxf.readfile(P / filename)
    assert doc.units == ezdxf.units.MM, "DXF must use millimetres"
    assert not doc.audit().has_errors, "DXF structural audit failed"
    outer, cuts, circles = [], [], set()
    for e in doc.modelspace():
        assert e.dxf.layer in ("OUTER_CUT", "INNER_CUT")
        if e.dxftype() == "CIRCLE":
            assert e.dxf.layer == "INNER_CUT"
            x, y, _ = e.dxf.center
            circles.add((round(x, 4), round(y, 4), round(e.dxf.radius, 4)))
            poly = Point(x, y).buffer(e.dxf.radius, quad_segs=128)
        else:
            assert e.dxftype() == "LWPOLYLINE" and e.closed
            assert all(abs(p[4]) < 1e-12 for p in e), "Unexpected bulge"
            poly = Polygon(list(e.get_points("xy")))
        assert poly.is_valid and poly.area > 0
        (outer if e.dxf.layer == "OUTER_CUT" else cuts).append(poly)
    assert len(outer) == 1
    outline = outer[0]
    assert all(outline.contains(c) for c in cuts)
    web = min(a.distance(b) for a, b in combinations(cuts, 2))
    assert web > 0, "Intersecting cut paths"
    edge = min(outline.boundary.distance(c) for c in cuts)
    material = outline
    for c in cuts:
        material = material.difference(c)
    assert material.is_valid and material.geom_type == "Polygon"
    return dict(outline=outline, cuts=cuts, circles=circles, material=material,
                min_web_mm=web, min_edge_mm=edge)


def inspect():
    bottom, top = read_plate(BOTTOM), read_plate(TOP)
    outer_holes = {(x, y, 1.8) for x, y in POSTS}
    motor_holes = {(x, y, 1.3) for x in (-39.75, -21.25) for y in (-18., 18.)}
    assert bottom["circles"] == outer_holes | motor_holes | {(26.5, 0., 11.4)}
    assert top["circles"] == outer_holes | {(x, y, 1.8) for x, y in HANGERS}
    assert len(bottom["cuts"]) == 13 and len(top["cuts"]) == 8
    assert np.allclose(bottom["outline"].bounds, [-47.5, -40, 47.6, 40], atol=.001)
    assert np.allclose(top["outline"].bounds, [-47.5, -40, 47.5, 40], atol=.001)
    assert bottom["min_web_mm"] >= .799 and bottom["min_edge_mm"] >= 2.699
    slots = [c for c in bottom["cuts"] if abs(c.centroid.x - CASTER) < .001 and 13 < abs(c.centroid.y) < 17]
    assert len(slots) == 2
    for c in slots:
        x0, y0, x1, y1 = c.bounds
        assert np.allclose([x1-x0, y1-y0], [3.6, 5.6], atol=.001)
    straps = [c for c in bottom["cuts"] if abs(abs(c.centroid.y)-30.5) < .001]
    assert len(straps) == 2
    for c in straps:
        x0, y0, x1, y1 = c.bounds
        assert np.allclose([c.centroid.x, x1-x0, y1-y0], [1, 6, 3], atol=.001)
    assert bottom["outline"].contains(Point(CASTER, 0).buffer(20.1, quad_segs=256))
    for y in (-36., 36.):
        assert not bottom["outline"].covers(Point(AXLE, y)), "Wheel notch closed"
        assert not bottom["outline"].covers(Point(-47., y)), "Rear notch closed"
    for name in (BOTTOM, TOP):
        with ZipFile(P / "95x80_flat_cutting_dxf.zip") as z:
            assert set(z.namelist()) == {BOTTOM, TOP}
            assert z.read(name) == (P / name).read_bytes()

    ref = json.loads((P / "references/controller_component_reference.json").read_text())
    coordinates = json.loads((P / "references/controller_outline_reference.json").read_text())["coordinates_mm"]
    board = affinity.rotate(Polygon(coordinates), 90, origin=(0, 0))
    components = []
    for i, s in enumerate(ref["body_solid_bounds_mm"]):
        if i:
            r = affinity.rotate(box(s[0], s[1], s[3], s[4]), 90, origin=(0, 0))
            components.append((i, s, r))
    battery = box(-17, -27.5, 13, 27.5)  # 55 transverse x 30 fore/aft x 20 high
    overlap = [(s[2], i) for i, s, r in components if s[2] < 0 and r.intersects(battery.buffer(1, join_style="mitre"))]
    local_z, local_id = min(overlap)
    post_r = 5.5 / math.sqrt(3)
    hanger_gap = min(Point(x,y).distance(r)-post_r for x,y in HANGERS
                     for _,s,r in components if s[5] > 0 and s[2] < 15)
    tires = [box(AXLE-17, y-3.25, AXLE+17, y+3.25) for y in (-TRACK/2, TRACK/2)]
    tire_gap = min(t.distance(bottom["outline"]) for t in tires)
    assert tire_gap >= .999 and hanger_gap > 0
    conflicts = [(x,y) for x,y in HANGERS if box(-36,-36,36,36).intersects(Point(x,y).buffer(1.8))]
    assert len(conflicts) == 4  # Expected unresolved finding, not a passing fit test.

    # Mass assumptions inherited from the V15 study; each entry is m[g], x,z[mm].
    area = math.sqrt(3)/2*5.5**2-math.pi*1.5**2
    parts = [(bottom["material"].area*4*.00118, bottom["material"].centroid.x, 10),
             (top["material"].area*2*.00118, top["material"].centroid.x, 58),
             (90,-2,22.5), (40,0,50), (20,CASTER,8), (4,AXLE,17),
             (15,-2,22), (6,0,25), (1,0,59.1), (21,AXLE,17), (21,AXLE,17)]
    parts += [(area*45*.00115,x,34.5) for x,y in POSTS]
    parts += [(area*15*.00115,x,49.5) for x,y in HANGERS]
    mass = sum(m for m,x,z in parts)
    cgx = sum(m*x for m,x,z in parts)/mass
    cgz = sum(m*z for m,x,z in parts)/mass
    force = 2*.0147/.017
    result = dict(
        status="NOMINAL_GEOMETRY_CHECKED_PHYSICAL_FIT_UNRESOLVED",
        units="mm, g, s unless explicitly stated",
        cut_sha256={n: hashlib.sha256((P/n).read_bytes()).hexdigest() for n in (BOTTOM,TOP)},
        controller_step_sha256=ref["source_sha256"],
        bottom_bounds_mm=list(bottom["outline"].bounds), top_bounds_mm=list(top["outline"].bounds),
        bottom_minimum_web_mm=bottom["min_web_mm"], bottom_minimum_edge_mm=bottom["min_edge_mm"],
        bottom_acrylic_mass_g=parts[0][0], top_acrylic_mass_g=parts[1][0],
        axle_x_mm=AXLE, caster_x_mm=CASTER, track_mm=TRACK,
        bottom_z_mm=[8,12], pcb_top_z_mm=42, top_z_mm=[57,59],
        battery_xyz_mm=[30,55,20], battery_mass_assumed_g=90,
        battery_to_local_component_gap_after_1mm_strap_mm=42+local_z-32.5-1,
        local_component_index=local_id,
        highest_component_to_top_mm=57-42-ref["component_above_pcb_top_mm"],
        hanger_to_component_lateral_gap_mm=hanger_gap, tire_to_plate_gap_mm=tire_gap,
        tag_black_square_conflicting_holes_mm=conflicts,
        assumed_mass_g=mass, assumed_cg_x_mm=cgx, assumed_cg_z_mm=cgz,
        assumed_caster_static_load_fraction=(cgx-AXLE)/(CASTER-AXLE),
        theoretical_rear_pitch_threshold_m_s2=9.81*(cgx-AXLE)/cgz,
        theoretical_front_pitch_threshold_m_s2=9.81*(CASTER-cgx)/cgz,
        motor_1_20_nominal_rated_speed_m_s=math.pi*.034*500/60,
        motor_1_20_nominal_no_load_speed_m_s=math.pi*.034*1100/60,
        motor_1_20_two_rated_torques_wheel_force_N=force,
        force_div_assumed_mass_m_s2=force/(mass/1000),
        unresolved=["Four hanger holes inside tag black square",
                    "Caster cut web is only 0.8 mm; strength untested",
                    "Encoder diameter/shaft height may cause plate interference",
                    "Battery model, leads, plugs, strap and component clearances need physical checks",
                    "1:20 motors, loaded speed, grip, braking and thermal behavior untested"],
    )
    return bottom, top, board, battery, components, result


def draw_poly(ax, poly, face, edge="#667785", **kw):
    ax.fill(*poly.exterior.xy, facecolor=face, edgecolor=edge, lw=.7, **kw)
    for ring in poly.interiors:
        ax.fill(*ring.xy, facecolor="white", edgecolor=edge, lw=.6)


def layout(bottom, top, board, battery, components, result):
    fig, axs = plt.subplots(2,2,figsize=(13,10))
    ax = axs[0,0]
    draw_poly(ax, bottom["material"], "#e5ebf0")
    for y in (-36.75,36.75):
        ax.add_patch(Rectangle((AXLE-17,y-3.25),34,6.5,color="#344553"))
        ax.add_patch(Rectangle((AXLE-6.25,2.5 if y>0 else -33.5),12.5,31,color="#a3b0b9",alpha=.7))
        ax.add_patch(Rectangle((AXLE-12.5,(18 if y>0 else -18)-4),25,8,color="#dba265",alpha=.7))
    draw_poly(ax,battery,"#aed5b9")
    ax.plot(*board.exterior.xy,":",color="#784298",lw=1.5)
    for _,s,r in components:
        if s[2] < -6:
            ax.fill(*r.exterior.xy,color="#c04c50",alpha=.6,lw=0)
    ax.add_patch(Circle((CASTER,0),20.1,fill=False,ls="--",color="#bf6464"))
    ax.plot([AXLE,AXLE],[-40,40],"--",color="#476778",lw=.7)
    ax.text(-2,0,"电池\n55 × 30 × 20",ha="center",va="center",fontsize=9)
    ax.text(CASTER,0,"球轮",ha="center",fontsize=9)
    ax.set_title("底板俯视：实际切割轮廓 + 不同高度零件投影")
    ax = axs[0,1]
    draw_poly(ax,top["material"],"#e5ebf0")
    ax.add_patch(Rectangle((-40,-40),80,80,fill=False,ec="#697c88",ls=":"))
    ax.add_patch(Rectangle((-36,-36),72,72,fill=False,ec="#aa681e",lw=1.5))
    for x,y in HANGERS:
        ax.add_patch(Circle((x,y),3.5,fill=False,ec="#c43c40",lw=1.5))
    ax.text(0,7,"标签成品 80 × 80 mm\n黑框 72 × 72 mm\n白边各 4 mm",ha="center",fontsize=10)
    ax.text(0,-16,"红圈：4 个悬挂孔与黑框冲突\n当前 DXF 尚未解决",ha="center",color="#ae3338",fontsize=10)
    ax.set_title("顶板俯视：主板悬挂孔与标签覆盖检查")
    for ax in axs[0,:]:
        ax.set(xlim=(-52,52),ylim=(-44,44),aspect="equal",xlabel="X / mm（向右为车头）",ylabel="Y / mm")
        ax.grid(alpha=.12)
    ax = axs[1,0]
    ax.add_patch(Rectangle((-47.5,8),95.1,4,color="#a8b8c5"))
    ax.add_patch(Rectangle((-47.5,57),95,2,color="#788e9f"))
    ax.add_patch(Circle((AXLE,17),17,fill=False,ls="--",ec="#344553"))
    ax.add_patch(Rectangle((-17,12.5),30,20,fc="#aed5b9",ec="#387e4a"))
    ax.add_patch(Rectangle((CASTER-20.1,5),40.2,3,color="#bf6464",alpha=.4))
    ax.add_patch(Circle((CASTER,6),6,fill=False,ec="#bf6464"))
    ax.add_patch(Rectangle((board.bounds[0],40.4),board.bounds[2]-board.bounds[0],1.6,color="#784298"))
    for x in (-43,43): ax.plot([x,x],[12,57],color="#81919b",lw=3)
    for x in (-24.5,24.5): ax.plot([x,x],[42,57],color="#b29d73",lw=3)
    for i,s,r in components:
        if s[2] < -6 or i in (result["local_component_index"],630):
            x0,_,x1,_ = r.bounds
            ax.add_patch(Rectangle((x0,42+s[2]),x1-x0,s[5]-s[2],fill=False,ec="#c27b55",lw=.6))
    ax.plot(result["assumed_cg_x_mm"],result["assumed_cg_z_mm"],"+",color="#202d3a",ms=12,mew=2)
    ax.text(-2,22,"CG",ha="center",fontsize=9)
    ax.axhline(0,color="#344553",lw=.8)
    ax.set(xlim=(-52,52),ylim=(-3,66),aspect="equal",xlabel="X / mm",ylabel="距地 Z / mm",title="侧面投影（非剖面）：45 mm 外柱 / 15 mm 悬挂柱")
    ax.grid(alpha=.12)
    ax = axs[1,1]; ax.axis("off")
    ax.text(.02,.95,"名义审核结果 · 尚未实装",fontsize=14,weight="bold",va="top")
    ax.text(.02,.84,
        f"底板 95.1 × 80 × 4；顶板 95 × 80 × 2 mm\n"
        f"轴距球轮 57 mm；轮心距约 73.5 mm\n"
        f"顶面高 59 mm；估算质量 {result['assumed_mass_g']:.1f} g\n"
        f"估算 CG：X {result['assumed_cg_x_mm']:.1f} / Z {result['assumed_cg_z_mm']:.1f} mm\n"
        f"球轮静载约 {100*result['assumed_caster_static_load_fraction']:.1f}%\n\n"
        "电池到局部元件约 5 mm（含 1 mm 绑带）\n"
        "最高元件到顶板约 2.1 mm；轮胎间隙约 1 mm\n"
        "悬挂柱到元件侧隙约 0.32 mm\n\n"
        "待解决：标签紧固孔冲突、球轮 0.8 mm 薄桥、\n"
        "编码器轴高干涉、真实电池与完整插头/线束。",
        fontsize=11,linespacing=1.7,va="top")
    fig.suptitle("95 × 80 mm 亚克力首件候选｜CAD 布局审核",fontsize=17)
    fig.text(.5,.025,"基于已提交 DXF 和历史主板包络。名义投影不证明强度或实物可装配；加工以 DXF 为准。",ha="center",fontsize=10)
    fig.tight_layout(rect=(0,.05,1,.95))
    fig.subplots_adjust(hspace=.3)
    fig.savefig(P/"audit_layout.png",dpi=140); plt.close(fig)


def extrude(ax, poly, z, height, color):
    faces = []
    colors = []
    darker = tuple(c*.78 for c in matplotlib.colors.to_rgb(color))
    for t in triangulate(poly):
        if poly.covers(t):
            pts = list(t.exterior.coords)[:-1]
            faces += [[(x,y,z) for x,y in pts],[(x,y,z+height) for x,y in pts]]
            colors += [darker,color]
    for ring in [poly.exterior,*poly.interiors]:
        pts = list(ring.coords)
        for (x,y),(u,v) in zip(pts,pts[1:]):
            faces.append([(x,y,z),(u,v,z),(u,v,z+height),(x,y,z+height)])
            colors.append(darker)
    ax.add_collection3d(Poly3DCollection(faces,facecolors=colors,edgecolors="none",linewidths=0))


def exploded(bottom,top,board,battery):
    fig = plt.figure(figsize=(13,9),facecolor="white")
    ax = fig.add_axes((0,.06,.66,.86),projection="3d",computed_zorder=True)
    # Deliberately exploded heights, not installed Z coordinates.
    extrude(ax,bottom["material"],12,4,"#b7c9d5")
    extrude(ax,top["material"],162,2,"#b7c9d5")
    extrude(ax,board,103,1.6,"#497f85")
    extrude(ax,battery,58,20,"#77b48b")
    for x,y in POSTS:
        hexagon = Polygon([(x+5.5/math.sqrt(3)*math.cos(a),y+5.5/math.sqrt(3)*math.sin(a))
                           for a in np.linspace(0,2*math.pi,6,endpoint=False)])
        extrude(ax,hexagon,24,45,"#b7a177")
    for x,y in HANGERS:
        extrude(ax,Point(x,y).buffer(5.5/math.sqrt(3),quad_segs=3),122,15,"#d5bb87")
        ring=Point(x,y).buffer(3.7,quad_segs=24)
        ax.plot(*ring.exterior.xy,[164.1]*len(ring.exterior.coords),color="#bc3b41",lw=1.5,zorder=100)
    for y in (-18,18):
        extrude(ax,box(AXLE-12.5,y-4,AXLE+12.5,y+4),29,2,"#dba265")
    for lo,hi in ((2.5,33.5),(-33.5,-2.5)):
        extrude(ax,box(AXLE-6.25,lo,AXLE+6.25,hi),31,12.5,"#98a8b4")
    # Wheel cylinders along Y, displaced sideways for the exploded view.
    a=np.linspace(0,2*np.pi,50)
    for side in (-1,1):
        y=side*49
        faces=[]
        for i in range(len(a)-1):
            faces.append([(AXLE+17*np.cos(t),yy,33+17*np.sin(t))
                          for yy,t in [(y-3.25,a[i]),(y+3.25,a[i]),(y+3.25,a[i+1]),(y-3.25,a[i+1])]])
        faces.extend([[(AXLE+17*np.cos(t),yy,33+17*np.sin(t)) for t in a] for yy in (y-3.25,y+3.25)])
        ax.add_collection3d(Poly3DCollection(faces,facecolors="#344553",edgecolors="none"))
    flange=Point(CASTER,0).buffer(20.1,quad_segs=48).difference(Point(CASTER,0).buffer(6,quad_segs=32))
    extrude(ax,flange,-9,3,"#95a4ae")
    extrude(ax,Point(CASTER,0).buffer(6,quad_segs=32),-15,6,"#c8cfd3")
    black=box(-36,-36,36,36)
    ax.plot(*black.exterior.xy,[164.15]*5,color="#aa681e",ls="--",lw=1,zorder=100)
    ax.quiver(30,-46,10,24,0,0,color="#344553",arrow_length_ratio=.2)
    ax.text(35,-46,0,"+X",fontsize=10)
    ax.set(xlim=(-63,63),ylim=(-62,62),zlim=(-18,170))
    ax.set_box_aspect((1,1,1.4)); ax.view_init(elev=22,azim=-48); ax.set_axis_off()
    fig.text(.65,.88,"95 × 80 mm acrylic",fontsize=20,weight="bold")
    fig.text(.65,.82,"Exploded assembly / 首件装配示意",fontsize=12)
    fig.text(.65,.75,
        "01  Top plate / 顶板  95 × 80 × 2 mm\n"
        "      Red rings: tag / hanger-hole conflict\n"
        "      红圈：标签与悬挂孔冲突，尚未解决\n\n"
        "02  PCB hangers / 主板悬挂柱\n"
        "      4 × M3 × 15 mm\n\n"
        "03  Controller / 主控板（轮廓简化）\n"
        "      Board components & cables omitted\n\n"
        "04  3S battery / 电池  55 × 30 × 20 mm\n"
        "      Assumed size, 90 g / 假定尺寸与质量\n\n"
        "05  Outer posts / 外柱  4 × M3 × 45 mm\n"
        "      2 motors + M2 brackets + Ø34 wheels\n\n"
        "06  Bottom / 底板  95.1 × 80 × 4 mm\n"
        "      CY-12B below plate / 球轮装在板下",
        fontsize=11,linespacing=1.4,va="top")
    fig.text(.5,.045,"Actual DXF plate cuts; nominal purchased-part shapes. Exploded gaps are not assembly dimensions.",ha="center",fontsize=10)
    fig.text(.5,.02,"板材使用实际 DXF 轮廓；采购件为简化示意，螺丝/绑带/线束省略。尚未通过实物装配验收。",ha="center",fontsize=10)
    fig.savefig(P/"exploded.png",dpi=140); plt.close(fig)


def main():
    # Prefer system CJK fonts, but allow another platform's font fallback.
    candidates = ["Arial Unicode MS", "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams["font.family"] = next((f for f in candidates if f in available),"DejaVu Sans")
    plt.rcParams["axes.unicode_minus"] = False
    data = inspect()
    (P/"audit_results.json").write_text(json.dumps(data[-1],ensure_ascii=False,indent=2)+"\n")
    layout(*data)
    exploded(*data[:4])
    print("DXF coordinates, units, open wheel notches and archive contents: PASS")
    print("Updated audit_layout.png, exploded.png, audit_results.json")
    print("Physical fit remains unresolved; see audit_results.json and dimensions.md")


if __name__ == "__main__":
    main()
