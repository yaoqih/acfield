# Localization and calibration

The root `apriltag_live.py` and `web/` provide localization independently of robot control. They support a real camera, video replay and a synthetic demo. Only camera data meeting provenance and calibration requirements can enter hardware control.

## Start the vision demo {#start-the-vision-demo}

From the repository root:

```bash
uv sync --python 3.12 --extra test
uv run --python 3.12 python apriltag_live.py --source demo
```

Open the printed URL, normally **http://127.0.0.1:8765**. Synthetic images check detection, calibration and export. Their 120 mm tags and 120 mm height are demo definitions, not reference-hardware dimensions, and cannot drive physical robots.

## Physical tags {#physical-tags}

See [arena and camera setup](../hardware/arena) for equipment layout and camera coverage.

Use `tag36h11`: arena IDs 0–3 and robot IDs 10–17. All physical labels use a **104 mm black square and a 130 mm overall square including the white margin**, with no bleed. The repository provides two current PDFs, each containing the same twelve IDs in the same order:

- [A4 print edition](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_A4.pdf): one label per page, with dimensions, crop marks and a 100 mm check ruler.
- [130 × 130 mm tag-only edition](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_tag_only.pdf): each page is exactly one complete label, with no heading, ruler, crop marks or extra page whitespace.

Detection size means the outer black border, excluding the white margin. Each label has a **104 × 104 mm** black square and a **13 mm** white margin on each side, giving a **130 × 130 mm** complete square. The tag-only edition keeps this required white quiet zone. Print either PDF at 100% actual size without fit-to-page. The A4 edition includes a check ruler and marks for trimming outside the white margin.

### Full-cover layout {#full-cover-layout}

[![Full-cover ID 10 label: clean white margin, subtle ID and forward arrow inside the black ring](/images/robot-tag.png)](/images/robot-tag.png)

The label fills the 130 mm cover without screw cutouts or screw avoidance. The ID uses approximately 5.7 pt type; the forward arrow and FRONT sit inside the opposite black border. Both use dark gray `#303030` close to the black background. Code cells, black-square edges and the white quiet zone remain intact. The arrow points to the canonical top edge. Align it with the robot's forward direction (+X); vision uses the same edge, so this installation uses `heading_offset_deg=0`.

Public vision settings use `size_m=0.104` for both arena and robot IDs. IDs 10–13 retain the pursuit-demo roles; IDs 14–17 use a generic robot role that experiments can configure as needed. Nominal `height_m` is `0.0646` for robots and `0` for arena markers; measure installed heights. Record the server's `tag_size` as `0.104` too. Existing local settings are not migrated automatically. When replacing historical 150 mm ground tags, update sizes, measure positions and recalibrate the arena.

The digital artwork passes 624 checks across two detection backends, covering multiple scales, four rotations, perspective with light blur and all 24 rasterized pages across both PDFs. Checks also verify black-square dimensions, page sizes and the complete quiet zone. Test installed labels under the arena camera, including paper deformation and reflections around screws.

Regenerate from the repository root:

```bash
uv run --python 3.12 python generate_apriltags.py
# Detection also needs Poppler's pdftoppm
uv run --python 3.12 python verify_apriltags.py --write-reports
```

To install printing tools alone with pip, use `python -m pip install -r requirements-print.txt`.

The two PDFs are committed release artifacts. Individual PNGs, manifests and check reports are generated in ignored `output/apriltags/`. Official source images live once in `assets/apriltags/` and serve printing, demos and detector tests. Historical size variants have been removed from the working tree and remain in Git history. The synthetic demo keeps its independent dimensions.

## Calibration order {#calibration-order}

1. Fix focal length, focus and resolution. Use an external calibration tool to obtain intrinsics/distortion and enter them in `apriltag_live.json` under `camera`.
2. Measure ground-tag positions, black-border sizes and headings in a shared frame. Fill the configuration and set `world.configured=true`.
3. Fix the camera and start arena extrinsic calibration in the interface. Check reprojection error, then measure arena-wide coordinate error at known positions.
4. Enter actual robot-tag size, height and heading correction. The V11 nominal tag-surface height of approximately 64.6 mm is a design reference only.
5. Set the server's tag offset relative to the axle midpoint. Verify forward heading and avoid adding the same mounting angle twice.
6. Occlude tags, freeze frames and move the camera to check expiry and calibration invalidation.

Public settings default to `camera=null` and an unconfigured world, not a laboratory calibration. `--source 0` normally opens the first camera; see `--help` for options.

## Hardware integration requirements {#hardware-integration-requirements}

Hardware data must declare `source_kind=camera`, `world_calibrated=true`, `tag36h11` and `demo=false`. The adapter never treats pixels as metres or repeated frames as fresh poses.

When quality metrics are supplied, an edge below 35 px, decision margin below 30, nonzero Hamming distance or implausible consecutive position jumps invalidate localization. OpenCV's missing quality fields alone do not cause rejection. Thresholds are initial values to revise against pixels, lighting and measured error.

Localization expires after 200 ms. Inspect source-frame age, detection age and processing latency; an online service can still serve frozen images.
