# Arena and camera setup

The reference layout uses a **3 × 3 m** square active arena. A fixed mast stands outside one side; a right-angle horizontal boom reaches the centre and supports a downward-facing camera. The server computer and router stay outside the arena.

Treat the arena as three separate elements: the 3 × 3 m motion area, the camera support, and the server/network equipment outside it. Candidate tube lengths and connectors are design inputs, not a final structural drawing; choose the boom span, mast height, base and cable routing from measured camera coverage and site loads.

![3 by 3 metre arena: spatial layout, plan dimensions and camera–computer–router–robot connections](/images/arena-en.svg)

Editable figure sources are in [hardware_design/figures](https://github.com/yaoqih/acfield/tree/main/hardware_design/figures).

## Dimensions and support {#dimensions-and-support}

| Item | Layout |
| --- | --- |
| Active arena | 3.0 × 3.0 m; x and y may each run from 0 to 3 m |
| Camera projection | Arena centre at (1.5, 1.5) m, optical axis downward |
| Mast | Outside the midpoint of a side; its base stays clear of the motion area |
| Boom | 1.5 m from the boundary to the centre, plus the mast setback |
| Camera height H | Choose from lens, resolution, coverage and tag pixels; no height is specified |

Robot icons are enlarged for readability. The spatial and plan views explain the arrangement; select boom sections, anchors and load capacity for the actual equipment. Allow room for cable routing and resist support movement. Calibrate after final mounting.

## Arena reference materials {#arena-reference-materials}

Prices are one discounted purchasing snapshot, not fixed procurement costs. Tube quantities and connectors are design inputs; determine the final structure from a support drawing and the camera coverage calculation.

| Part | Reference specification | Reference quantity and price | Notes |
| --- | --- | ---: | --- |
| Camera | H200S, 1080p, 60 fps, 3 mm, advertised 110-degree wide angle | 1, CNY 167.13 | Verify actual resolution, distortion, frame rate and USB cable length before choosing the height. |
| Camera mount | U-shaped gimbal clamp for an approximately 30 mm cylinder | 1, CNY 8.78 | Candidate for the boom or tube; check anti-slip, anti-rotation and vibration resistance. |
| Tube | 15 x 15 x 0.9 mm square tube, 1.2 m x3 | 3.6 m total, CNY 4.61 each | Light support candidate; assign it to a mast, boom or brace only after the layout is fixed. |
| Tube | 20 x 20 x 1.1 mm square tube, 1.2 m x3 and 0.5 m x2 | 4.6 m total, CNY 5.29 / 1.69 each | Main support candidate; complete the span, height and base drawing before cutting. |
| Tube connectors | 20 mm straight, three-way and four-way connectors | 1 each, CNY 2.08 / 2.43 / 2.43 | Match the tube wall thickness, locking method and required stiffness. |
| AprilTag cards | 80 x 80 mm custom cards, 12 pieces | CNY 7.00 per batch | Printing carrier candidate; verify `tag36h11`, 72 mm black border, white margin and 100% scale. |

The reference tube quantity totals about 8.2 m, but it does not define a stable mast and boom by itself. Confirm the camera optical axis, boom deflection, base footprint, cable routing and vehicle clearance before assembly.

Twelve 80 mm cards cover candidate robot IDs 10–21. The four ground reference tags, IDs 0–3, need separate production, measurement and mounting. A generic square card cannot replace the required tag pattern.

## Image and network connections {#image-and-network-connections}

```text
Overhead camera ── USB / wired video ── Server computer
                                             │
                                        Ethernet / LAN
                                             │
                                        Router / AP
                                             │ Wi-Fi / UDP
                                     car-01 … car-04
```

The camera is wired to the computer, with the cable secured along the boom and mast before leaving the arena. The diagram uses a USB camera as an example; select the actual cable type and length for the camera interface. `apriltag_live.py`, `robot_server` and policy scripts can run on the same computer.

Connect the computer to the router by Ethernet. All four robots join the same experiment Wi-Fi, which carries local control and telemetry traffic. Configure the vision service URL and robot bindings on the computer; SDK clients on other machines use the server computer’s LAN IP. See [configuration](../guide/configuration).

Route the camera cable along the boom and mast to the computer, connect the computer to the access point by Ethernet, and keep the robots on Wi-Fi. Keep battery wiring away from encoder wires and wheels, label polarity at every adapter, and never run camera, network or charging cables temporarily across the active area.

## Camera height and coverage {#camera-height-and-coverage}

Cover the ground boundary, complete fixed-tag white margins and the robot-tag plane: nominally 59 mm for the compact acrylic candidate or 64.6 mm for V11; use the measured installed height. For an ideal downward pinhole camera, coverage in one direction is approximately:

```text
coverage ≈ 2 × (H − tag-plane height) × tan(field of view / 2)
```

Check horizontal and vertical field of view at the actual capture resolution independently. A lens’s advertised diagonal angle is insufficient. Leave a margin and inspect corner distortion and the most distant tags; raising the camera expands coverage while reducing tag pixels.

The H200S advertised 110° value is not automatically its horizontal or vertical field of view. Test actual resolution, distortion, frame rate, tag pixels and motion blur after mounting. Moving only the camera requires new world extrinsics. Changing camera, lens, focus or capture resolution also requires checking intrinsics. See [camera reference parameters](./h200s-camera) for device readback ranges; use the current driver's supported units and readback values in the dashboard.

Ground IDs 0–3 illustrate placement only. Measure final tag centres, headings and dimensions before updating configuration. Validate arena-wide position error, frame age and invalidation after camera movement using the [localization and calibration](../guide/localization) procedure.
