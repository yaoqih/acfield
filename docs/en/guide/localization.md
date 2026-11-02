# Localization and calibration

The root `apriltag_live.py` and `web/` provide localization independently of robot control. They support a real camera, video replay and a synthetic demo. Only camera data meeting provenance and calibration requirements can enter hardware control.

## Start the vision demo {#start-the-vision-demo}

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-apriltag.txt
.venv/bin/python apriltag_live.py --source demo
```

Open the printed URL, normally **http://127.0.0.1:5050**. Synthetic images check detection, calibration and export. Their 120 mm tags and 120 mm height are demo definitions, not reference-hardware dimensions, and cannot drive physical robots.

## Physical tags {#physical-tags}

See [arena and camera setup](../hardware/arena) for equipment layout and camera coverage.

Use `tag36h11`: ground IDs 0–3 and robot IDs 10–13. Download the [complete eight-page A4 print file](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_ground150_robot104_A4.pdf), or the [four-page robot-only file for IDs 10–13](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_robot104_4tags_A4.pdf). Ground black squares remain 150 mm; robot black squares are now 104 mm.

Detection size means the outer black border, excluding the white margin. Each robot label has a **104 × 104 mm** black square and a **13 mm** white margin on each side, giving a **130 × 130 mm** cut size. Print at 100% actual size without fit-to-page, check the 100 mm ruler and trim at the crop marks outside the white margin.

### Full-cover layout {#full-cover-layout}

[![Full-cover ID 10 label: clean white margin, subtle ID and forward arrow inside the black ring](/images/robot-tag.png)](/images/robot-tag.png)

The label fills the 130 mm cover without screw cutouts or screw avoidance. The ID uses approximately 5.7 pt type; the forward arrow and FRONT sit inside the opposite black border. Both use dark gray `#303030` close to the black background. Code cells, black-square edges and the white quiet zone remain intact. The arrow points to the canonical top edge. Align it with the robot's forward direction (+X); vision uses the same edge, so this installation uses `heading_offset_deg=0`.

Public vision settings now use `size_m=0.104` and nominal `height_m=0.0646` for IDs 10–13. Measure the installed label height; existing local settings are not migrated automatically. Record the server's `tag_size` as `0.104` too.

The digital artwork passes 408 checks across two detection backends, covering multiple scales, four rotations, perspective with light blur and rasterized print PDFs. Checks also verify black-square dimensions and the complete quiet zone. Test the installed label under the arena camera, including paper deformation and reflections around screws.

Regenerate from the repository root:

```bash
python -m pip install -r requirements-print.txt
python generate_apriltags.py --robot-pdf output/pdf/apriltag36h11_robot104_4tags_A4.pdf
# Detection also needs requirements-apriltag.txt and Poppler's pdftoppm
python verify_apriltags.py --write-reports
```

PNGs are previews; print from the vector PDFs. Historical 90 mm files remain available, while the synthetic demo keeps its own 120 mm artwork and dimensions.

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
