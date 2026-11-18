# Hardware revisions and compatibility

**Identify installed parts before copying parameters.** Record CAD revision, motor ratio and vision profile separately. Recheck measurements when any part changes.

## Current options {#matrix}

| Item | V11 reference body | Compact 95 × 80 mm candidate | Newly purchased 1:30 parts |
| --- | --- | --- | --- |
| Status | Published CAD and historical runtime profile | Plates, drawings and tags provided, first assembly awaits acceptance | Procurement specifications, whole-vehicle adaptation pending |
| Motors | Body revision is independent of motor revision. Four existing vehicles were reported converted to 1:20 | CAD arranged for 1:20 | 1:30, remeasure output counts and speed |
| Tag black frame / finished size | 104 / 130 mm | 72 / 80 mm, 4 mm white border on every side | Follow installed body and tag |
| Tag height | Nominal 64.6 mm | Nominal approximately 59 mm | Measure after assembly |
| Forward tag offset | Nominal 16 mm, server default remains 0 | Nominal 30.5 mm | Measure from axle midpoint |
| Standoffs | Follow V11 CAD | Design uses 45 / 15 mm | Purchased M3 × 50 needs layer-height and screw checks |
| Battery | Record installed pack | Verify tray, wiring and balance | 1200 mAh 3S, verify dimensions and mounting |
| Pending checks | Actual envelope, offset and counts | Mounting holes versus tag pattern, physical white-border detection, assembly interference | Motor mounting, standoff height, pack space, counts and limits |

Top-plate dimensions differ from the vehicle envelope. Include wheels, wiring and protrusions in `length/width`. The compact tag mounting-hole conflict requires first-article verification and revision. Inspect [resources and drawings](./resources) before ordering.

## What to update after changes {#changes}

| Change | Remeasure and update |
| --- | --- |
| Motor, ratio, encoder | Firmware `pulsesPerTurn`, channels, signs, feed-forward/PI, stable speeds, server limits |
| Wheel diameter, track | Firmware `wheelDiameter/trackWidth`, straight distance and pivot angle |
| Tag, top plate, standoffs | Vision black-frame size, height and heading, server tag offset, envelope and body offset |
| Camera, lens, capture mode | Intrinsics, extrinsics, full-arena error, driver readback |
| Battery and supply | Mounting, loaded voltage drop, undervoltage settings, capacity conversion |

Follow [bring-up measurements](./bringup#measurement-procedures). [Generated defaults](../reference/defaults) describe the repository configuration. See the [BOM](./bom) and [purchase options](./purchasing) for procurement details.
