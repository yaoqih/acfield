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

Use `tag36h11`: ground IDs 0–3 and robot IDs 10–13. The [A4 print file](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_ground150_robot90_A4.pdf) contains 150 mm ground black borders and 90 mm robot black borders.

Detection size means the outer black border, excluding the white margin. A 90 mm black border has an overall 112.5 mm size including white margin. Print at 100% actual size without fit-to-page, measure the PDF's 100 mm ruler and preserve the white margin.

Regeneration requires `Pillow` and `reportlab`, then `generate_apriltags.py`. Screenshots and displayed PNG dimensions do not establish physical print size.

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
