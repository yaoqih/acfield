---
pageClass: hardware-bom
---

# Purchase links and order options

Items are ordered by importance: **controller, drive and power; chassis fabrication; vision and camera support; connectors and tools**. Use this page to open product listings, select variants and prepare order notes. See the [detailed BOM](./bom) for one-robot and four-robot quantities, compatibility and missing parts, and [resources and CAD](./resources) for drawings and parameter images. IDs match the BOM.

The URLs and selections come from the supplied purchasing list. Current listings, stock and prices have not been independently checked. **Pending means no purchase quantity was supplied. Counts such as 100, 50, 10 and 12 describe pack contents; the number of packs or batches is separate.**

## Controller, drive and power {#control-drive-power}

| BOM | Item and order option | Purchase quantity / pack | Purchase link |
| --- | --- | --- | --- |
| B01 | ROS robot driver board | Pending | [Taobao product](https://item.taobao.com/item.htm?id=923727056922) |
| B02 | Encoder motor with bracket; DC 12 V A12; **1:30**; seller describes a three-wire encoder | Pending; confirm whether one item contains one motor or a pair | [Taobao product](https://item.taobao.com/item.htm?id=777868414369) |
| B03 | Battery variant: **102050x3S-1200mAh** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=39418236809) |
| B04 | Charger variant: **1 A + reverse XH2.54 female adapter** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=37065896052) |
| B05 | Black N20 rubber wheel, **34 mm diameter** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=708154853977) |
| B06 | **CY-12B**, nylon main ball caster | Pending; supplied URL matches the controller listing, so confirm the variant | [Taobao product](hhttps://item.taobao.com/item.htm?id=1004178769321) |

## Chassis fabrication and assembly {#chassis-fabrication}

| BOM | Item and order option | Purchase quantity / pack | Purchase link |
| --- | --- | --- | --- |
| B07 | Custom acrylic dimensions, cutting and drilling; **10x10 cm service option, send CAD** | Quote by CAD; plate count pending | [Tmall product](https://detail.tmall.com/item.htm?id=1004154119421) |
| B08 | White nylon **M3x50 posts, ten pieces** | 10 per pack; pack count pending | [Tmall product](https://detail.tmall.com/item.htm?id=535354726884) |
| B09 | White **M3 nuts, 100 pieces** | 100 per pack; pack count pending | [Tmall product](https://detail.tmall.com/item.htm?id=580759003585) |
| B10 | White **M3x8 screws, 100 pieces** | 100 per pack; pack count pending | [Tmall product](https://detail.tmall.com/item.htm?id=585705247440) |

Download the bottom and top DXFs from the [fabrication files](./resources#fabrication-files), specifying thickness and plate count with the drawings. The 10x10 cm service option does not define the drawing. The selected 50 mm posts differ from the existing CAD's 45 mm / 15 mm posts; see the [BOM](./bom#chassis-fabrication).

## Vision and camera support {#vision-and-camera-support}

| BOM | Item and order option | Purchase quantity / pack | Purchase link |
| --- | --- | --- | --- |
| B11 | **H200S, 60 fps, 3 mm lens, seller-described 110-degree distortion-free option** | Pending; request a **1/4 mounting hole and 5 m cable, CNY 20 surcharge** | [Taobao product](https://item.taobao.com/item.htm?id=655976902051) |
| B12 | U-shaped camera clamp for a **3 cm diameter round pole** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=825849225211) |
| B13 | Square steel tube **20x20x1.1 mm; 1.2 m per piece** | **3 pieces, 3.6 m total** | [Taobao product](https://item.taobao.com/item.htm?id=1047819735433) |
| B14 | Square steel tube **20x20x1.1 mm; 0.5 m per piece** | **2 pieces, 1.0 m total** | [Taobao product](https://item.taobao.com/item.htm?id=1047819735433) |
| B15 | Aluminium alloy 20x20 **spatial four-way connector, three-hole seller option** | **2 connectors** | [Tmall product](https://detail.tmall.com/item.htm?id=1040051817107) |
| B16 | Aluminium alloy 20x20 **straight connector, four-hole option** | **Pending**, count from the support drawing | [Tmall product](https://detail.tmall.com/item.htm?id=1040051817107) |
| B17 | Single-sided custom cards with matte laminate; **80x80 mm; twelve cards with unrestricted designs** | 12 per batch; batch count pending | [Taobao product](https://item.taobao.com/item.htm?id=1027752283513) |

Square steel tubing totals **5 pieces and 4.6 m**. The round-pole clamp is for approximately 30 mm diameter, while the frame uses 20 mm square tube; confirm fit. Before ordering cards, download the [twelve-design tag print package](./resources#fabrication-files) and check the 80 mm finished size, 72 mm black square and 4 mm white margins.

Camera order note:

> H200S, 60 fps, 3 mm lens, selected 110-degree distortion-free option. Include a 1/4 mounting hole and a 5 m USB cable, with the supplied CNY 20 surcharge.

## Connectors and tools {#connectors-and-tools}

| BOM | Item and order option | Purchase quantity / pack | Purchase link |
| --- | --- | --- | --- |
| B18 | PH2.0 female terminals for the seller's male housing; **100 pieces** | 100 per pack; pack count pending | [Tmall product](https://detail.tmall.com/item.htm?id=693403171100) |
| B19 | **PH2.0-6P male housings, 50 pieces** | 50 per pack; pack count pending | [Tmall product](https://detail.tmall.com/item.htm?id=693403171100) |
| B20 | **SN-68B crimping tool, 0.08-1.5 mm2** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=1046845441676) |
| B21 | **D3L automatic wire stripper, 0.03-10 mm2, with cutting** | Pending | [Taobao product](https://item.taobao.com/item.htm?id=1046845441676) |

The crimping tool and wire stripper use different variants on one listing. Select terminals and empty housings separately too. Each complete 6P connector needs six terminals.

## Before ordering {#before-ordering}

| Item | Relationship to the existing setup |
| --- | --- |
| Motor | This selection is **1:30**; existing robot and design records use **1:20**. Measure encoder counts and loaded speed and update control parameters after a change. |
| Battery and charger | Selected pack is **3S, 1200 mAh**. Confirm 3S / 12.6 V charger compatibility, permitted charge current and adapter polarity. |
| Caster | The supplied product ID matches the controller listing. Confirm the CY-12B variant with the seller. |
| Support | Straight connector count was not supplied. Resolve round-clamp fit and connector locking from the final support drawing. |
| Posts and CAD | The selected M3x50 posts differ from the existing 45 mm / 15 mm posts. Check assembly height before fabrication. |

When a product changes, update this page and the [detailed BOM](./bom) together. Preserve model, variant and source URL to support repeat purchases and substitutions.
