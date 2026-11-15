<script setup>
import { withBase } from 'vitepress'
</script>

# Hardware resources, CAD and parameter images

Updated 2026-11-15. Controller documentation and fabrication files come first, followed by controller, drive/wiring, battery and camera references. See the [detailed BOM](./bom) for selected options and quantities and [mechanical design](./overview) for the existing design.

## Controller documentation and CAD {#controller-documents-and-cad}

The reference board is **Waveshare General Driver for Robots**. Direct links below were obtained from the [official resources page](https://docs.waveshare.net/General_Driver_for_Robots/Resources-And-Documents/). They point to upstream online files; project fabrication files follow below. Confirm the actual purchased board revision.

| Priority | Resource | Purpose | Official link |
| --- | --- | --- | --- |
| 1 | Product documentation | Board overview, interfaces and development entry points | [General Driver for Robots](https://docs.waveshare.net/General_Driver_for_Robots/) |
| 2 | Schematic | Power path, motor driver, encoder signals, levels and pins | [Schematic PDF](https://www.waveshare.net/w/upload/3/37/General_Driver_for_Robots.pdf) |
| 3 | Board 2D CAD | PCB outline, mounting holes and mechanical fit | [DXF ZIP](https://www.waveshare.net/w/upload/5/50/GENERAL-DRIVER-FOR-ROBOTS-STR-DXF.zip) |
| 4 | Board 3D CAD | Component, connector and enclosure clearance | [STEP ZIP](https://www.waveshare.net/w/upload/8/8e/General_Driver_for_Robots_STEP.zip) |
| 5 | Dimensional drawings | Human-readable dimensional comparison | [Drawing PDF ZIP](https://www.waveshare.net/w/upload/0/0a/GENERAL-DRIVER-FOR-ROBOTS-STR-PDF.zip) |
| 6 | Encoder feedback example | Compare count and speed feedback methods | [EncoderRpmFeedback.rar](https://www.waveshare.net/w/upload/3/3c/EncoderRpmFeedback.rar) |
| 7 | Motor control and speed loop | Compare driver and closed-loop implementations | [MotorCtrl.rar](https://www.waveshare.net/w/upload/0/08/MotorCtrl.rar), [SpeedLoopCtrl.rar](https://www.waveshare.net/w/upload/1/18/SpeedLoopCtrl.rar) |
| 8 | Integrated firmware example | Upstream firmware structure | [UGV01_BASE.zip](https://www.waveshare.net/w/upload/0/0c/UGV01_BASE.zip) |

Check millimetre units, board revision, connector direction and actual component height when importing CAD. Upstream examples are references; project firmware and pins follow [firmware and bring-up](./bringup) and the repository implementation.

## Project fabrication and printing files {#fabrication-files}

These downloads are byte-preserving copies of existing repository files. The **95 mm first-article candidate** still has an unresolved tag/fastener conflict; decide the mounting method before fabrication.

| Priority | File | Specification and delivery notes |
| --- | --- | --- |
| 1 | [Bottom and top DXF ZIP](/downloads/hardware/95x80_flat_cutting_dxf.zip) | Millimetres, 1:1. One of each for a first article; bottom 4 mm, top 2 mm. Send thickness and quantity with the files. |
| 2 | <a :href="withBase('/downloads/hardware/bottom_plate_95.1x80_flat_4mm.dxf')" download>Bottom DXF</a> | 95.1x80x4 mm. The 0.1 mm difference is intentional in the existing design. |
| 3 | <a :href="withBase('/downloads/hardware/top_plate_95x80_flat_2mm.dxf')" download>Top DXF</a> | 95x80x2 mm. Four hanger holes intersect the tag area; holes and protruding fasteners must not damage the pattern. |
| 4 | [Twelve AprilTag PNGs ZIP](/downloads/hardware/tag36h11_80mm_white4_12ids_png.zip) | tag36h11, IDs 10-21. Finished size 80 mm; black square 72 mm; margins 4 mm each; actual-size printing, no bleed. |
| 5 | [Detailed dimensions and assembly notes](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/dimensions.md) | Existing design uses 45/15 mm posts and 1:20 motors; the new purchasing list specifies 50 mm posts and 1:30 motors. Compatibility is unresolved. |

Sources remain in [hardware_design/acrylic_95](https://github.com/yaoqih/acfield/tree/main/hardware_design/acrylic_95). The [download manifest](/downloads/hardware/manifest.json) records source paths and SHA-256 hashes. Cutting contours, holes and tag patterns were not changed.

## Controller parameter images {#controller-parameters}

The images identify ESP32-WROOM-32, TB6612FNG, XH2.54 power and two PH2.0-6P encoder-motor ports. The dimension image marks a 65 mm horizontal outline and 49/58 mm mounting-hole spacing; verify the complete outline, extensions and component envelope in CAD. Text specifies DC 7-13 V, while the visible board legend says DC 9-12.6 V. Resolve the input range for the actual revision.

<details>
<summary>Controller interface locations: original image</summary>

![Original controller interface locations and numbering](/images/主控板接口1.png)

</details>

<details>
<summary>Controller interface descriptions: original image</summary>

![Original controller components and interface descriptions](/images/主控板参数2.png)

</details>

<details>
<summary>Controller dimensions: original image</summary>

![Original controller outline and mounting dimensions](/images/主控板尺寸.png)

</details>

## Drive dimensions and wiring images {#drive-and-wiring}

For the selected **A12, 12 V, 1:30** option, the supplier table lists 730 rpm no-load speed, **380 rpm rated speed**, **19.6 mN m rated torque**, rated current at most 0.22 A and 0.4 A stall current. With a 34 mm wheel, the rated-point theoretical speed is approximately 0.68 m/s. This is not a measured loaded speed or a control limit.

The wiring image specifies an AB Hall encoder, **3 PPR** base count, 3.3/5 V supply and ZH1.5-6PIN. Do not reuse a different encoder's 7 PPR value. Confirm the post-gear count convention and actual gear ratio by measurement.

| Image wire colour | Motor-side signal | Connection check |
| --- | --- | --- |
| Red | Motor positive, M1 | Driver output; verify direction with wheels raised. |
| Green | Motor negative, M2 | Other driver output, separate from encoder ground. |
| Blue | Hall VCC | Wiring image says VCC; dimensional drawing also labels PIN5 as GND. Resolve the conflicting label before connection. |
| Black | Hall GND | Common encoder/controller ground. |
| Yellow | C1 / A | Verify channel, direction and logic level. |
| White | C2 / B | Verify channel, direction and logic level. |

These colours transcribe the supplied image. Actual harness colours may differ. Check both connector pinouts and viewing directions individually.

<details>
<summary>Motor performance: original image</summary>

![Original motor performance table for multiple voltages and ratios](/images/电机参数.png)

</details>

<details>
<summary>Motor dimensions and pin table: original image</summary>

![Original motor dimensions and conflicting pin label](/images/电机尺寸.png)

</details>

<details>
<summary>Motor wiring and encoder: original image</summary>

![Original six-wire motor connections and Hall encoder specifications](/images/电机接线.png)

</details>

<details>
<summary>Motor bracket: original image</summary>

![Original motor bracket dimensions, approximately 18.5 mm mounting pitch](/images/电机支架.png)

</details>

<details>
<summary>Drive wheel: original image</summary>

![Original 34 mm wheel, 6.5 mm thickness and 3 mm D bore](/images/轮子尺寸.png)

</details>

<details>
<summary>CY-12B caster: original image</summary>

![Original CY-12B nylon-ball dimensions and supplier load table](/images/万向轮参数.png)

</details>

## Battery and charging references {#battery-and-charging}

The selected pack is **102050x3S-1200 mAh**. The available image is a generic supplier reference, not this assembled pack's dedicated dimension, connector or charging specification. It lists 0.1C standard charge and 0.5C maximum charge, with a conditional 0.2C note. For 1200 mAh, 0.5C is 0.6 A; the selected 1 A charger is approximately 0.83C. Obtain the exact pack rating before considering the combination compatible. Verify approximately 12.6 V full-charge voltage, protection, connectors, adapter polarity and balancing arrangements.

<details>
<summary>Generic battery parameters: original image</summary>

![Original generic battery specifications, not a dedicated 3S-pack data sheet](/images/电池.png)

</details>

## Camera parameters and order notes {#camera-parameters}

Selected **H200S, 60 fps, 3 mm, seller-described 110-degree distortion-free option**. Request a **1/4 mounting hole and 5 m cable, CNY 20 surcharge**. The image specifies a default 1.5 m cable, so the custom cable length must be separately confirmed.

The image lists 1920x1080, USB2.0 High Speed, UVC, 5 V and approximately 150-200 mA. Its frame-rate table specifies 1080p at 60 fps for **MJPG**, and 5 fps for YUY2 at that resolution. Confirm actual format, field of view, distortion and sustained acquisition with the selected 5 m cable.

<details>
<summary>H200S parameters and frame-rate table: original image</summary>

![Original H200S parameters, MJPG and YUY2 frame rates and default cable length](/images/摄像头参数.png)

</details>

See [H200S device controls](./h200s-camera) for driver-read ranges and [arena setup](./arena) for installation.

## Original image archive and index {#image-archive}

All **eleven original parameter images** remain in docs/public/images with their original filenames and contents. The [image index](/images/hardware-parameters.json) records filenames, BOM IDs, supplied source URLs, pixel dimensions, sizes and SHA-256 hashes. The archive date is 2026-11-15; original capture dates were not supplied. Source URLs are provenance clues, not independent verification of every seller claim.

| Order | Original image | Related item |
| --- | --- | --- |
| 1 | [Controller interface layout](/images/主控板接口1.png) | B01; locations and numbering |
| 2 | [Controller interface descriptions](/images/主控板参数2.png) | B01; components and interfaces |
| 3 | [Controller dimensions](/images/主控板尺寸.png) | B01; outline and mounting |
| 4 | [Motor performance](/images/电机参数.png) | B02; A12 12 V and ratio options |
| 5 | [Motor dimensions](/images/电机尺寸.png) | B02; geometry and pin table |
| 6 | [Motor wiring](/images/电机接线.png) | B02; six wires and 3 PPR Hall encoder |
| 7 | [Motor bracket](/images/电机支架.png) | B02; original bracket dimensions |
| 8 | [Wheel dimensions](/images/轮子尺寸.png) | B05; 34 mm drive wheel |
| 9 | [Caster parameters](/images/万向轮参数.png) | B06; CY-12B |
| 10 | [Generic battery parameters](/images/电池.png) | B03/B04; generic reference |
| 11 | [Camera parameters](/images/摄像头参数.png) | B11; H200S and frame rates |

The user supplied these images. Supplier and brand marks are preserved, and original material remains the property of its respective rights holders. Save later revisions separately and update the index.

Run `python3 hardware_design/archive_hardware_docs.py` from the repository root to rebuild the image index and fabrication downloads. The script verifies identical copied content and leaves original images and source drawings unchanged.
