---
pageClass: hardware-bom
---

# Detailed BOM and purchasing specifications

Check [hardware compatibility](./compatibility) for the existing 1:20 motors and the adaptation required for purchased 1:30 parts.

Updated 2026-11-15. Items are ordered by importance: **controller, drive and power; chassis fabrication; vision and camera support; connectors and workshop tools**. Product options and URLs come from the supplied purchasing list; current prices, stock and purchase status have not been independently checked.

**Quantity basis:** one-robot and four-robot requirements are estimates for a differential-drive configuration. Explicit quantities, pack contents and suggested purchases are distinguished below. Shared equipment is not multiplied by robot count. No current total cost is calculated: only the CNY 20 camera cable surcharge was supplied.

[Purchase links and order options](./purchasing) · [Parameter images, controller documentation and CAD](./resources) · [Mechanical design](./overview) · [Arena setup](./arena)

## Check these specifications first {#priority-checks}

| Item | Current selection and unresolved detail |
| --- | --- |
| Motor revision | This list specifies **A12, 12 V, 1:30**. Existing 95 mm CAD and historical robot records use 1:20. This purchasing record does not establish a physical replacement or update runtime settings. Recheck encoder counts, loaded speed and limits after replacement. |
| Battery and charger | Selected **102050x3S, 1200 mAh**, replacing the previous 2200 mAh/XT60 purchasing reference. The selected charger is 1 A with a reverse XH2.54 female adapter. Confirm 3S/12.6 V charging, allowed charge current and actual polarity. |
| Motor wiring | The seller option says three-wire encoder motor, while the supplied image shows **six wires, AB encoder and ZH1.5-6P**. The dimensional drawing labels PIN5 as both GND and Hall VCC. Resolve this conflict before connecting to the controller's PH2.0-6P socket. |
| Standoffs | Selected **M3x50, ten white pieces per pack**. Existing CAD needs four 45 mm outer posts and four 15 mm hangers per robot. The 50 mm option is not an established direct replacement. |
| Camera clamp | Selected for an approximately 30 mm round pole, while the frame uses 20 mm square steel tube. Clamping range, adapters and rotation restraint require confirmation. Request a 1/4 camera mounting hole. |
| Missing quantity and shared URL | Straight tube connector quantity was not supplied. The caster and controller share the same supplied product URL; confirm the CY-12B option. |

## Controller, drive and power {#control-drive-power}

Per-robot quantities assume two drive motors and exclude spares. Suggested quantities do not mean items were ordered.

| ID | Selected specification | One / four robots | Purchasing unit and suggested quantity | Source and notes |
| --- | --- | --- | --- | --- |
| B01 | ROS robot driver board; software reference: Waveshare General Driver for Robots | 1 / 4 boards | One board per item; first article 1, four robots 4 | [Product](https://item.taobao.com/item.htm?id=923727056922). Verify revision, ESP32, TB6612FNG, power and pins. [Official documentation and CAD](./resources#controller-documents-and-cad). |
| B02 | Encoder motor with bracket; DC 12 V A12; **1:30**; seller describes a three-wire encoder | 2 / 8 motor/bracket sets | First article 2, four robots 8; confirm whether one selling unit contains one motor or a pair | [Product](https://item.taobao.com/item.htm?id=777868414369). Confirm bracket fasteners and the six-wire interface shown in the reference image. |
| B03 | **102050x3S-1200mAh** battery | 1 / 4 packs | First article 1, four robots 4 | [Product](https://item.taobao.com/item.htm?id=39418236809). Nominal 3S voltage approximately 11.1 V, full charge 12.6 V. Verify assembled dimensions, protection, connectors, wire exit, mass and discharge rating. |
| B04 | **1 A charger + reverse XH2.54 female adapter** | Shared | Start with one set; simultaneous charging needs separate channels | [Product](https://item.taobao.com/item.htm?id=37065896052). At 1200 mAh, 1 A is approximately 0.83C. The generic battery image does not establish permission for this current. Confirm the specific pack's charge rating, 3S compatibility and polarity. |
| B05 | Black N20 rubber wheel, **34 mm diameter** | 2 / 8 wheels | First article 2, four robots 8 | [Product](https://item.taobao.com/item.htm?id=708154853977). Image shows 6.5 mm thickness and a 3 mm D bore. Measure shaft engagement and effective diameter. |
| B06 | **CY-12B, nylon main ball** caster | 1 / 4 casters | First article 1, four robots 4 | [Supplied URL](https://item.taobao.com/item.htm?id=923727056922), identical to B01; verify the option. Image shows a 12 mm ball, 15 mm height and 20 g mass. |

## Chassis fabrication and assembly {#chassis-fabrication}

Keep selected purchasing options distinct from the current CAD requirements. Trial-assemble one robot before replication.

| ID | Selected specification | One / four robots | Purchasing unit and suggested quantity | Source and notes |
| --- | --- | --- | --- | --- |
| B07 | Custom acrylic cutting/drilling; **10x10 cm service option, send CAD** | Current CAD: one bottom and one top / four of each | Quote by drawing; first article one two-plate set | [Product](https://detail.tmall.com/item.htm?id=1004154119421). Bottom 95.1x80x4 mm; top 95x80x2 mm. The service option does not define thickness, holes or set count. [Files](./resources#fabrication-files). |
| B08 | White nylon **M3x50, ten pieces** | Trial quantity unresolved; four per robot would mean sixteen for four robots | Suggested trial purchase one ten-piece pack; sixteen posts would need two packs | [Product](https://detail.tmall.com/item.htm?id=535354726884). Confirm thread configuration and effective length. Current CAD separately needs 45 mm outer posts and 15 mm hangers. |
| B09 | White nylon **M3 nuts, 100 pieces** | Current CAD caster reference: 2 / 8, plus any other joints | Suggested one 100-piece pack | [Product](https://detail.tmall.com/item.htm?id=580759003585). Check thickness and screw engagement. |
| B10 | White nylon **M3x8 screws, 100 pieces** | Current CAD plate/controller reference: 16 / 64 | Suggested one 100-piece pack | [Product](https://detail.tmall.com/item.htm?id=585705247440). Does not cover separately sized caster screws or M2 motor fasteners. Top fastener/tag conflict remains unresolved. |

## Vision and camera support {#vision-and-camera-support}

These are shared arena parts or batch printing. The explicitly specified steel tubing totals **five pieces and 4.6 m**, excluding the historical 15 mm tube option.

| ID | Selected specification | Purchasing unit and quantity | Source and notes |
| --- | --- | --- | --- |
| B11 | **H200S, 60 fps, 3 mm lens, seller-described 110-degree distortion-free option** | Suggested one camera; total not explicitly supplied | [Product](https://item.taobao.com/item.htm?id=655976902051). Request **1/4 mounting hole, 5 m cable, CNY 20 surcharge**. Confirm thread and housing fit. Measure actual field of view and distortion. |
| B12 | U-shaped camera clamp for approximately **30 mm round pole** | Suggested one; total not explicitly supplied | [Product](https://item.taobao.com/item.htm?id=825849225211). Compatibility with 20 mm square tube is unresolved. |
| B13 | Square steel tube **20x20x1.1 mm, 1.2 m per piece** | **Three pieces, 3.6 m total: explicit** | [Product](https://item.taobao.com/item.htm?id=1047819735433). Assign uprights and arms after the support drawing is complete. Tube is steel; connectors are aluminium alloy. |
| B14 | Square steel tube **20x20x1.1 mm, 0.5 m per piece** | **Two pieces, 1.0 m total: explicit** | [Product](https://item.taobao.com/item.htm?id=1047819735433). B13+B14 total 4.6 m. Verify fit and tolerances. |
| B15 | Aluminium alloy 20x20 **spatial four-way connector, three-hole seller option** | **Two connectors: explicit** | [Product](https://detail.tmall.com/item.htm?id=1040051817107). Preserve the seller's four-way/three-hole description; confirm geometry, locking holes and 1.1 mm tube-wall fit. |
| B16 | Aluminium alloy 20x20 **straight connector, four-hole option** | **Quantity unresolved** | [Product](https://detail.tmall.com/item.htm?id=1040051817107). Count from the final support drawing; do not reuse the historical quantity as confirmed. |
| B17 | Single-sided custom cards, matte laminate, **80x80 mm; twelve cards, unrestricted designs** | Suggested one twelve-card batch; number of batches unspecified | [Product](https://item.taobao.com/item.htm?id=1027752283513). Twelve tag36h11 designs, IDs 10-21, 72 mm black square, 4 mm white margins, actual-size printing and no bleed. [Print package](./resources#fabrication-files). |

## Connectors, consumables and tools {#connectors-and-tools}

Pack contents are inventory quantities. Tools are shared workshop equipment. Validated assembled adapter leads may replace loose crimp parts in the initial build.

| ID | Selected specification | Purchasing unit and quantity | Source and notes |
| --- | --- | --- | --- |
| B18 | PH2.0 female terminals for the seller's male housing; **100 pieces** | Suggested one pack; pack count unspecified | [Product](https://detail.tmall.com/item.htm?id=693403171100). Check the seller's terminal/housing terminology. One fully populated 6P board end uses six terminals; eight board-end motor leads for four robots use 48 before spares. |
| B19 | **PH2.0-6P male housing, 50 pieces** | Suggested one pack; pack count unspecified | [Product](https://detail.tmall.com/item.htm?id=693403171100). Four robots need eight housings if only the board ends are made. One hundred terminals populate sixteen 6P housings with four terminals left over, not all fifty housings. |
| B20 | **SN-68B crimping tool, 0.08-1.5 mm2** | Suggested one shared tool; total unspecified | [Product](https://item.taobao.com/item.htm?id=1046845441676). Confirm die compatibility with the exact terminal and wire; check pull strength and continuity. |
| B21 | **D3L automatic wire stripper, 0.03-10 mm2, with cutting** | Suggested one shared tool; total unspecified | [Product](https://item.taobao.com/item.htm?id=1046845441676). Same URL as B20, different option. Adjust with spare wire before stripping fine conductors. |

## Ordering and assembly notes {#order-and-assembly-notes}

| Order | Information to confirm with the supplier |
| --- | --- |
| Camera | H200S, 60 fps, 3 mm lens, selected 110-degree option; confirm a 1/4 mounting hole and 5 m USB cable with the supplied CNY 20 surcharge. Confirm supported formats at the selected resolution. |
| Acrylic | Two DXFs, millimetres and 1:1 scale, all contours/holes cut through; bottom 4 mm, top 2 mm, one of each for the first article. Resolve tag/fastener conflicts before fabrication. |
| Cards | Twelve unique designs, one each, single-sided matte finish; 80 mm finished size, 72 mm black square, 4 mm margins, no resizing, bleed, added lettering or cropped margins. Check printed scale and camera detection. |
| Frame | Steel tube 20x20x1.1 mm: 1.2 m x3 and 0.5 m x2. Two spatial four-way/three-hole connectors; straight connector count pending. Confirm included locking screws. |
| Battery/charger | Confirm assembled dimensions, connector photographs, pinout, protection and permitted charge current for the 102050x3S-1200 mAh pack. Verify the charger is for 3S/12.6 V and the adapter matches both endpoints. |

## Assembly items still to specify {#remaining-assembly-items}

All 21 supplied options are recorded above. A complete assembly still requires these decisions or parts:

| Item | One / four robots and next decision |
| --- | --- |
| Controller standoffs | If retaining 95 mm CAD: M3x45 outer posts 4 / 16 and M3x15 hangers 4 / 16; otherwise revise geometry and recount. |
| Motor and power harnesses | Motor adapter leads 2 / 8, matched battery-to-board power harnesses 1 / 4; specify wire, connectors, disconnect and protection for the actual hardware. |
| Motor/caster fasteners | One original M2 motor-bracket hardware set per robot; caster M3x10 screws are a trial candidate, two per robot, subject to actual thickness and engagement. |
| Battery retention | One flexible strap and insulating pad set per robot, matching slots and actual pack dimensions. |
| Tag mounting | Four controller hanger holes currently intersect the black square. Define a flat mounting method before ordering the final plates. |
| Camera support completion | Straight connector count, square-tube/clamp adaptation, base or ballast, locking hardware and cable retention follow the support drawing. |
| Arena equipment | Inventory the computer, router/AP, Ethernet cable and ground tags. The twelve roof cards do not automatically include corner IDs 0-3. |

The [95 mm design BOM](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/bom.csv) retains the previous 1:20 and standoff assumptions. This page records the new 1:30 and 1200 mAh purchasing options; reconcile both after the first article is confirmed.
