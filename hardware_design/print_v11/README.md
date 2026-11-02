# V11 reference chassis

Two printable parts: `stl/chassis_130mm_rear_axle.stl` and `stl/tag_plate_130mm.stl`. The nominal footprint is 130 × 130 mm, with 34 mm wheels, 122 mm wheel track, drive axle at X=-16 mm and a tag surface at approximately Z=64.6 mm. All purchased-part dimensions must be checked on the first article.

## Printing

Use PETG, 0.4 mm nozzle, 0.20 mm layer height, 4 walls, 5 top/bottom layers and uniform 40% Gyroid or Cubic infill. Check support needs in the slicer. Print the chassis flat-bottom down and tag plate with its tag face down. Preserve scale and orientation. There are only two parts; historical modifiers are not part of V11.

These are initial manufacturing settings, not a strength certification. Inspect bracket/caster pitches, electrical clearances, bolt engagement, three-point ground contact, cable routes and battery retention before replicating vehicles.

## Regenerate and audit

From the repository root, install `hardware_design/requirements.txt` in a separate environment, then run:

```bash
python hardware_design/print_v11/build.py
python hardware_design/print_v11/audit.py
python hardware_design/print_v11/render.py
```

Build writes the STL, assembly and preview intermediates; audit writes nominal geometry and quasi-static reports. The bundled report records 212 nominal checks. Estimated mass, load fractions and center of gravity are design estimates, not physical measurements.

The historical shopping CSV is a dated reference, not a complete current quote. Wiring entries explicitly flag unresolved supplier pin-label conflicts; verify actual pin functions before power. See the [public hardware guide](https://yaoqih.github.io/acfield/hardware/overview).
