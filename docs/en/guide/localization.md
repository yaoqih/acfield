# Localization and calibration

The root `apriltag_live.py` and `web/` provide localization independently of robot control. They support a real camera, video replay and a synthetic demo. Only camera data meeting provenance and calibration requirements can enter hardware control.

## Start the vision demo {#start-the-vision-demo}

From the repository root:

```bash
uv sync --python 3.12 --extra test
uv run --python 3.12 python apriltag_live.py --source demo --runtime-config output/vision-demo-settings.json
```

Use this separate demo profile to keep physical camera settings separate. Open the printed URL, normally **http://127.0.0.1:8765**. Synthetic images check detection, calibration and export. Their 120 mm tags and 120 mm height are demo definitions, not reference-hardware dimensions, and cannot drive physical robots.

The dashboard has three workspaces. Switching preserves tag selection, filters and unsubmitted drafts:

- **Live observation** shows the camera and arena trails, with tag summaries opening the inspector. World locking and clearing tracks are under arena actions.
- **Tag data** filters by ID, name and observation status. The table shows pose, speed and quality; the inspector adds camera pose and raw corners. On phones, tag details open in a dialog closed with its button or Escape.
- **Device settings** separates source, camera capture, tag detection and preview into four groups, showing one at a time. Drafts show pending changes, with apply/reset actions and retry after read failures. Camera controls apply to the connected physical camera.

Recording, saving/export and the separate camera/world calibration page are available from the workspace header. Clearing world calibration or trajectory statistics requires confirmation. A compact status bar shows the next action; expand diagnostics for details. Source/detection changes wait for worker confirmation. Stale observations become lost during disconnection or capture expiry and resume on recovery.

Preview width and rate affect MJPEG display only, not capture resolution or detection rate. Defaults are width `0` (original size) and `30` fps; they reset on restart. Source/detector changes apply to the current run; save the profile under saving/export to retain them. See [H200S parameters](../hardware/h200s-camera) for driver support, units and readback considerations.

## Physical tags {#physical-tags}

See [arena and camera setup](../hardware/arena) for equipment layout and camera coverage.

The compact 95 mm candidate uses `tag36h11` robot labels with a **72 mm black square, 4 mm white margin per side, and 80 mm finished size**, without bleed. Print the [12 PNG images, IDs 10–21](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/tag_images/tag36h11_80mm_white4_12ids_png.zip) at actual size, with the image top facing forward. Mounting holes and fasteners must not obscure the pattern; check recognition throughout the arena. On adoption, update vision and console settings from measured dimensions (nominal `size_m=0.072`), installed height and control-point offset. Saved runtime settings are not migrated automatically; IDs 18–21 require configuration. Configure arena markers independently from their actual sizes.

The following describes the older V11 labels: `tag36h11` arena IDs 0–3 and robot IDs 10–17, each with a **104 mm black square and a 130 mm overall square including the white margin**, with no bleed. The two PDFs contain the same twelve IDs in the same order:

- [A4 print edition](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_A4.pdf): one label per page, with dimensions, crop marks and a 100 mm check ruler.
- [130 × 130 mm tag-only edition](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_tag_only.pdf): each page is exactly one complete label, with no heading, ruler, crop marks or extra page whitespace.

Detection size means the outer black border, excluding the white margin. Each label has a **104 × 104 mm** black square and a **13 mm** white margin on each side, giving a **130 × 130 mm** complete square. The tag-only edition keeps this required white quiet zone. Print either PDF at 100% actual size without fit-to-page. The A4 edition includes a check ruler and marks for trimming outside the white margin.

### Full-cover layout {#full-cover-layout}

[![Full-cover ID 10 label: clean white margin, subtle ID and forward arrow inside the black ring](/images/robot-tag.png)](/images/robot-tag.png)

The label fills the 130 mm cover without screw cutouts or screw avoidance. The ID uses approximately 5.7 pt type; the forward arrow and FRONT sit inside the opposite black border. Both use dark gray `#303030` close to the black background. Code cells, black-square edges and the white quiet zone remain intact. The arrow points to the canonical top edge. Align it with the robot's forward direction (+X); vision uses the same edge, so this installation uses `heading_offset_deg=0`.

Public vision settings still use the V11 defaults: `size_m=0.104` for arena and robot IDs, and `height_m=0.0646` for robots. IDs 10–17 default to generic robot identities; experiments can assign roles for formation, pursuit, coverage or other tasks. Configure the compact robot from its measured values above; changing arena markers also requires updated dimensions, coordinates and recalibration.

The digital artwork passes 624 checks across two detection backends, covering multiple scales, four rotations, perspective with light blur and all 24 rasterized pages across both PDFs. Checks also verify black-square dimensions, page sizes and the complete quiet zone. Test installed labels under the arena camera, including paper deformation and reflections around screws.

Regenerate from the repository root:

```bash
uv run --python 3.12 python generate_apriltags.py
# Detection also needs Poppler's pdftoppm
uv run --python 3.12 python verify_apriltags.py --write-reports
```

To install printing tools alone with pip, use `python -m pip install -r requirements-print.txt`.

The two V11 PDFs are committed release artifacts. V11 individual PNGs, manifests and reports go to ignored `output/apriltags/`; compact PNGs and their ZIP live in `hardware_design/acrylic_95/tag_images/`. Official sources in `assets/apriltags/` serve printing, demos and tests. The synthetic demo keeps independent dimensions. Run `uv run python hardware_design/acrylic_95/tag_images/generate.py` to rebuild and digitally check all twelve compact labels; this does not replace camera measurements.

## Calibration order {#calibration-order}

Disarm all robots, connect a physical camera in the dashboard and fix focus and capture resolution. Open camera/world calibration at the same vision service's `/calibration` (normally `http://127.0.0.1:8765/calibration`). Keep the camera fixed and move the board during sampling.

### ChArUco camera intrinsics {#charuco-intrinsics}

1. Download the page's A4 board PDF (`/calibration/board.pdf`). Defaults are **8 columns × 11 rows of squares, 20 mm squares, 15 mm markers and `DICT_5X5_100`**. Counts refer to squares. Print at 100%, measure and mount it flat. For another board, match the settings to the physical board; changing settings does not regenerate the default PDF.
2. Keep the same camera, resolution and focus. Move and tilt the board across the centre, corners, distances and angles. Capture at least 8 images, preferably 15–25, up to 40. Each image needs at least 8 valid corners.
3. Calculate intrinsics and inspect the matrix, distortion, image size and reprojection RMS. RMS measures pixel fitting error; validate world coordinates at known locations separately.
4. Save intrinsics to the runtime profile. Saving clears old world extrinsics, which must be recalibrated. Externally measured OpenCV intrinsics can also be imported when they match the camera and image mode.

Sampling accepts fresh physical-camera frames only. Video, demo, frames older than 500 ms and repeated raw frames are rejected. Clear samples after changing board settings, camera connection or resolution. Samples live in server memory: refreshing the page retains them, restarting the service loses them. Calibration sample images are not persisted.

### World coordinates and extrinsics {#world-coordinates-and-extrinsics}

1. Measure ground reference tags **IDs 0–3**: centre X/Y in metres, Z=0, black-border sizes and headings. The separate page forms the boundary in order 0→1→2→3; enter a valid polygon rather than copying schematic coordinates. Other fixed IDs or non-ground arrangements require the full profile editor.
2. Save measured coordinates to mark the world configured and clear old extrinsics. Lock extrinsics with all four complete reference tags visible. Measure position and heading error across the arena at known locations.
3. Enter measured robot-tag size, height and heading correction. Nominal height is approximately 59 mm for the compact candidate or 64.6 mm for V11, as design references only. Set tag offset from the axle midpoint in the control server. Check forward heading and avoid duplicate mounting-angle compensation.
4. Reload the vision profile in the control console before saving. After restarting, use **Verify and load**: the service observes fixed tags and solves again, rejecting camera-position differences above 3 cm. This initial software threshold does not replace arena-wide error measurement.
5. Occlude tags, freeze frames and move the camera to validate invalidation and stops. Moving only the camera requires new world extrinsics. Changing camera, lens, focus or capture mode also requires checking intrinsics before solving extrinsics.

Public initial settings have `camera=null` and an unconfigured world. The runtime profile defaults to `output/vision-settings.json` and overrides initial defaults. Saved extrinsics are not trusted automatically after restart. `--source 0` normally opens the first camera; see `--help` for more options.

## Hardware integration requirements {#hardware-integration-requirements}

Hardware data must declare `source_kind=camera`, `world_calibrated=true`, `tag36h11` and `demo=false`. The adapter never treats pixels as metres or repeated frames as fresh poses.

When quality metrics are supplied, an edge below 35 px, decision margin below 30, nonzero Hamming distance or implausible consecutive position jumps invalidate localization. OpenCV's missing quality fields alone do not cause rejection. Thresholds are initial values to revise against pixels, lighting and measured error.

Localization expires after 200 ms. Inspect source-frame age, detection age and processing latency; an online service can still serve frozen images.

These rules govern pose acceptance. With `ROBOT_ALLOW_UNLOCALIZED_CONTROL=1`, the control server permits manual motion with invalid localization and skips position protection. Set it to `0` for localization-constrained experiments; see [configuration](./configuration).
