# Arena and camera setup

The reference layout uses a **3 × 3 m** square active arena. A fixed mast stands outside one side; a right-angle horizontal boom reaches the centre and supports a downward-facing camera. The server computer and router stay outside the arena.

[![3 by 3 metre arena: spatial layout, plan dimensions and camera–computer–router–robot connections](/images/arena-en.svg)](/images/arena-en.svg)

Click for the original size, or download the [PNG](/images/arena-en.png). Editable figure sources are in [hardware_design/figures](https://github.com/yaoqih/acfield/tree/main/hardware_design/figures).

## Dimensions and support {#dimensions-and-support}

| Item | Layout |
| --- | --- |
| Active arena | 3.0 × 3.0 m; x and y may each run from 0 to 3 m |
| Camera projection | Arena centre at (1.5, 1.5) m, optical axis downward |
| Mast | Outside the midpoint of a side; its base stays clear of the motion area |
| Boom | 1.5 m from the boundary to the centre, plus the mast setback |
| Camera height H | Choose from lens, resolution, coverage and tag pixels; no height is specified |

Robot icons are enlarged for readability. The spatial and plan views explain the arrangement; select boom sections, anchors and load capacity for the actual equipment. Allow room for cable routing and resist support movement. Calibrate after final mounting.

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

## Camera height and coverage {#camera-height-and-coverage}

Cover the ground boundary, complete fixed-tag white margins and the robot-tag plane at approximately 64.6 mm. For an ideal downward pinhole camera, coverage in one direction is approximately:

```text
coverage ≈ 2 × (H − tag-plane height) × tan(field of view / 2)
```

Check horizontal and vertical field of view at the actual capture resolution independently. A lens’s advertised diagonal angle is insufficient. Leave a margin and inspect corner distortion and the most distant tags; raising the camera expands coverage while reducing tag pixels.

Ground IDs 0–3 illustrate placement only. Measure final tag centres, headings and dimensions before updating configuration. Validate arena-wide position error, frame age and invalidation after camera movement using the [localization and calibration](../guide/localization) procedure.
