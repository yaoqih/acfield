# Materials and mechanical design

The reference uses a Waveshare General Driver for Robots (SKU23730, ESP32 + TB6612), two geared encoder motors and external AprilTag localization. The **current compact first-article candidate** is a 95 × 80 mm acrylic robot, pending assembly and measurements; it is not a validated four-robot fleet.

Keep the CAD assumptions separate from hardware samples. The compact CAD and dynamics notes use a 1:20 motor as a fast candidate; the current validation sample is the same A12 family at 1:100. Do not carry speed limits, wiring or clearances from one ratio to the other without measurement.

| Item | Compact candidate |
| --- | --- |
| Bottom / top | 95.1 × 80 × 4 mm / 95 × 80 × 2 mm acrylic |
| Motors / wheels | Two A12 12 V 1:20 quadrature encoder motors and 34 mm wheels; CAD candidate, with a 1:100 validation sample |
| Support / posts | One CY-12B ball caster; four each M3 nylon posts, 45 and 15 mm |
| Battery | 3S, layout assumes 55 × 30 × 20 mm; actual model, capacity and mass unconfirmed |
| Robot tag | tag36h11, 72 mm black square, 4 mm white margin per side, 80 mm finished size, no bleed |
| Nominal mass / height | Approximately 272 g / 59 mm to top surface, subject to model assumptions |

DXF files, label images, the bill of materials and open checks are in the [95 mm candidate](https://github.com/yaoqih/acfield/tree/main/hardware_design/acrylic_95). **The PCB mounting holes lie inside the tag's black square and the current drawing does not resolve the fastener conflict.** Trial assembly must resolve it, along with encoder-to-plate clearance, the thin caster web and battery/connector clearance.

## Reference purchasing and design boundaries {#reference-purchases}

The following is a reusable selection example. Prices are a discounted November 2026 snapshot for rough budgeting, not fixed procurement costs or a supplier requirement. Equivalent parts may be substituted after checking voltage, current, pinout, mounting holes, dimensions and clearance.

| Part | Reference specification | Price reference | Design use and checks |
| --- | --- | ---: | --- |
| Controller | ESP32 + TB6612 class controller; software reference is Waveshare SKU23730 | CNY 135.91 | Reads encoders and drives two motors. Verify the actual IC, input voltage, PWM/direction/encoder pins and 3.3 V levels. |
| Geared encoder motors | A12, 12 V, three-wire encoder, brackets, 1:100 x2 | CNY 66.32 per pair | Current validation sample. Verify ratio, encoder type, bracket holes, shaft height and pinout; 1:20 is the faster CAD candidate. |
| Drive wheels | N20 D-shaft rubber wheels, 34 mm x2 | CNY 4.74 per pair | Differential drive contact. Measure diameter, width, bore, shaft engagement and effective track. |
| Ball caster | CY-12B nylon ball caster x1 | CNY 1.50 | Supports the body but is not the kinematic reference point. Measure holes, working height and rolling resistance. |
| 3S battery | 11.1 V, 2200 mAh, XT60 x1 | CNY 47.15 | Check fit in the 55 x 30 x 20 mm assumed space, mass, 12.6 V full charge and peak current. |
| Charger | B4 charger and adapter, 2–4S | CNY 65.49 | Match both the main and balance connectors of the selected 3S pack. |

Use assembled adapter cables where possible. ZH1.5-to-PH2.0 6P cables are signal/encoder candidates (CNY 4.20 for two); XT60-to-DC5525 (CNY 8.80) and DC5525-to-XH2.54 2P (CNY 6.80) are power candidates only when polarity, wire gauge and board ratings match. Connector names do not define pinout. Loose terminals and crimping tools are workshop equipment, not the robot BOM.

## Relationship between robot, arena and control chain {#system-hardware-relationship}

```text
Robot AprilTag ── overhead camera ── USB ── server computer ── Ethernet ── router/AP
       │                                                               │
       └─ chassis, ESP32, encoder motors, battery ── Wi-Fi / UDP ───────┘
```

1. **Robot layer:** two encoder motors and 34 mm wheels form the differential drive; the CY-12B only supports the body. Verify battery polarity, current capacity and retention before power-up.
2. **Control layer:** the ESP32 reads encoders, closes the wheel-speed loop and exchanges UDP telemetry and commands with the server. Any substitute controller needs an explicit pin, power and driver check.
3. **Vision layer:** the fixed camera observes robot and ground tags, and the vision service converts pixels to arena coordinates. Configure measured black-border size, tag height and heading.
4. **Arena layer:** the 3 x 3 m area is the active workspace. Tube supports and cables stay outside the robot envelope; the server and access point stay outside the arena.

The software uses the drive-axle midpoint as the differential-drive reference point. The tag offset, body envelope and motor ratio must be measured on the assembled first robot rather than inferred from a product title.

## Design principles for reuse {#design-principles}

1. **Define interfaces before choosing parts:** motors, batteries, cameras and connectors can change, but voltage, current, pinout, mounting geometry and data semantics must remain compatible.
2. **Turn assumptions into measurements:** wheel diameter, track, encoder counts, tag size, tag height, control-point offset and camera calibration belong in configuration or acceptance evidence.
3. **Validate robot and arena separately:** finish one robot's electrical, mechanical and wheel-loop checks before calibrating the camera, then expand from one to multiple robots.
4. **Centralize shared equipment:** the camera, server and access point are arena equipment; each robot should carry only the real-time controller and feedback hardware.
5. **Keep public documentation reusable:** prices can provide a cost estimate, while interfaces, constraints, drawings and validation steps carry the reference value. Supplier logistics and one-time discounts should not be design dependencies.

## Assembly and exploded view {#assembly-and-exploded-view}

![95 mm candidate: actual DXF cuts, installed height, assumed centre of mass and tag/hole conflicts; Chinese annotations](/images/acrylic-95-audit.png)

![95 mm acrylic candidate exploded view: top plate, 15 mm PCB hangers, controller, battery, 45 mm outer posts, motors, bottom and underslung caster; bilingual labels](/images/acrylic-95-exploded.png)

The audit image now shows **only the 95 mm version**. Both plates use the actual DXF cuts and holes. Purchased parts are simplified, screws/straps/cables are omitted, and exploded gaps are not assembly dimensions. Four red rings show unresolved hanger-hole conflicts inside the tag's black square.

The [detailed design notes, in Chinese](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/dimensions.md) cover hole coordinates, height chains, controller clearance, mass assumptions and acceptance. The [BOM](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/bom.csv) lists quantities for one and four robots. Acrylic mass is approximately 48.6 g. The estimated 272 g total and 25.9 mm centre-of-mass height assume a 90 g battery and other nominal inputs. The caster carries approximately 46.7% of static load, so measure its rolling resistance.

With 34 mm wheels, the 1:20 motor's supplied 500 rpm rated point corresponds to 0.89 m/s, while the nominal 1:100 point is about 0.23 m/s. Two rated torques imply a theoretical 1.73 N wheel-edge force for the 1:20 data sheet. Use the measured motor ratio, loaded speed, turning, low voltage and temperature to set limits; these nominal values are not a floor-speed or stopping guarantee.

The differential-drive/unicycle reference point is the axle midpoint. A centred tag lies approximately **30.5 mm forward** of it, requiring offset compensation. The front plate extends approximately 78.1 mm ahead of the axle, so the body envelope also needs an offset. Existing runtime defaults remain V11; measure tag size, height, offsets, wheel diameter, track and encoder counts after assembly.

### Recheck and regenerate

From the repository root, regenerate the report and figures using committed DXFs and historical controller envelopes; no personal supplier-STL path is required:

```sh
uv run --with ezdxf --with shapely python hardware_design/acrylic_95/review.py
uv run python hardware_design/acrylic_95/tag_images/generate.py
cp hardware_design/acrylic_95/audit_layout.png docs/public/images/acrylic-95-audit.png
cp hardware_design/acrylic_95/exploded.png docs/public/images/acrylic-95-exploded.png
```

## Older V11 printed reference {#v11-reference}

The following images and figures describe the **older V11 130 mm printed reference**, not the compact robot.

![V11 complete assembly and internal structure with the cover removed](/images/assembly-en.svg)

### V11 exploded view

![V11 exploded assembly: cover, controller, posts, battery, motors, wheels, chassis and ball caster](/images/exploded-en.svg)

The view includes the tag cover, controller, four 50 mm and four 25 mm posts, 3S battery, two encoder motors, two drive wheels, printed chassis and auxiliary ball caster. Parts are separated along installation directions; the caster is inverted to reveal its ball. Separation distances are illustrative and some fasteners are omitted.

The printed chassis and cover use repository CAD geometry. Purchased parts use nominal dimensions and simplified appearances; PCB connector details are not wiring instructions. The flat tag face points up and the cover ribs point down. Opaque surfaces and a depth buffer replace the previous transparent triangle-overlay preview.

Shared equipment is shown in [arena and camera setup](./arena).

## Mechanical reference {#mechanical-reference}

| Parameter | V11 nominal value | Usage |
| --- | --- | --- |
| Chassis/tag-board outline | 130 × 130 mm | Include wheels, screws and offsets in the full envelope |
| Wheel diameter / track | 34 / 122 mm | Measure effective values before control |
| Drive axle | 16 mm behind geometric centre | Control point is the axle midpoint |
| Robot-tag surface height | Approximately 64.6 mm | Measure after assembly |
| Black border / including white margin | 104 / 130 mm | Full cover, no screw cutouts; preserve the margin |
| Printed components | Chassis + tag board, two parts | Historical modifiers/packages excluded |

STLs, parameters and build/audit sources are in [hardware_design/print_v11](https://github.com/yaoqih/acfield/tree/main/hardware_design/print_v11). Both parts default to PETG, 0.4 mm nozzle, 0.2 mm layers, four walls, five top/bottom layers and 40% Gyroid/Cubic infill. Actual material use, supports and strength depend on slicing and first-article checks.

## Bill-of-material categories {#bill-of-material-categories}

| Category | V11 reference | Per robot |
| --- | --- | --- |
| Control | General Driver for Robots | 1 |
| Drive | A12 12 V 1:150 encoder motors and brackets (historical V11 nominal reference) | 2 |
| Ground contact | 34 mm wheels, CY12B ball caster | 2 + 1 |
| Power | 3S battery, fused harness, power switch | Per wiring plan |
| Structure | Two prints, 25/50 mm M3 standoffs and fasteners | See manufacturing list |
| Tag | tag36h11, 104 mm black border | 1 |
| Shared equipment | Camera/lens/mount, router, computer, charging equipment | Per arena |

Older CSV files retain V11 material, print-order and wiring references; use the separate BOM above for the 95 mm candidate. The lists intentionally omit supplier-specific quotations, shipping and missing parts; verify the actual motor, harness and battery revisions. The platform does not require the historical STM32/serial bridge or custom PCB.

## Why this layout {#why-this-layout}

Two drive wheels and a low-resistance support follow the differential-drive model. A low battery position and stable tag board provide a useful geometric reference. Common fasteners and a two-part printed structure reduce initial assembly complexity.

Stability, caster resistance, bracket alignment and encoder feedback directly affect low-speed control. Correct nominal geometry does not establish acceptable friction, backlash, printed strength or stopping behavior.

## Editable and inspectable {#editable-and-inspectable}

Use the shared repository Python environment for the CAD tools:

```bash
uv sync --python 3.12 --extra test
uv run --python 3.12 python hardware_design/print_v11/build.py
uv run --python 3.12 python hardware_design/print_v11/audit.py
# Install repository JS dependencies and the rendering browser
npm ci
npx playwright install chromium
uv run --python 3.12 python hardware_design/print_v11/render.py
```

Building regenerates STL, assembly and parameter files; auditing updates nominal geometry evidence. Supplier assumptions are explicit parameters and need rechecking after changes. Rendering uses preview meshes generated by the build.

Validate the first robot before replicating. See [firmware and bring-up](./bringup).
