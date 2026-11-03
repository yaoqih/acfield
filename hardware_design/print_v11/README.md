# V11 reference chassis

Two printable parts: `stl/chassis_130mm_rear_axle.stl` and `stl/tag_plate_130mm.stl`. The nominal footprint is 130 × 130 mm, with 34 mm wheels, 122 mm wheel track, drive axle at X=-16 mm and a tag surface at approximately Z=64.6 mm. All purchased-part dimensions must be checked on the first article.

The current paper label fills the entire 130 × 130 mm cover: a 104 mm black detection square plus a 13 mm white quiet zone on each side, without screw cutouts. Small dark-gray ID and FRONT marks sit inside the black ring. Align FRONT with chassis +X. Ground tags use the same size. Use the [A4 PDF](../../output/pdf/apriltag36h11_130mm_A4.pdf) or [tag-only PDF](../../output/pdf/apriltag36h11_130mm_tag_only.pdf) at 100% scale; see [generation and verification notes](../../assets/apriltags/README.md).

## Printing

Use PETG, 0.4 mm nozzle, 0.20 mm layer height, 4 walls, 5 top/bottom layers and uniform 40% Gyroid or Cubic infill. Check support needs in the slicer. Print the chassis flat-bottom down and tag plate with its tag face down. Preserve scale and orientation. There are only two parts; historical modifiers are not part of V11.

These are initial manufacturing settings, not a strength certification. Inspect bracket/caster pitches, electrical clearances, bolt engagement, three-point ground contact, cable routes and battery retention before replicating vehicles.

## Regenerate and audit

From the repository root, install `hardware_design/requirements.txt` in a separate environment, then run:

```bash
python hardware_design/print_v11/build.py
python hardware_design/print_v11/audit.py
# Install the depth-buffered rendering toolchain once
npm ci
npx playwright install chromium
python hardware_design/print_v11/render.py
```

Build writes the STL, assembly and preview intermediates; audit generates nominal geometry and quasi-static reports locally. The audit performs 213 nominal checks, including a continuous upper tag face with ribs underneath. Reports and local review images are ignored by Git; the current STL, assembly model/parameters and published documentation figures are retained. Estimated mass, load fractions and center of gravity are design estimates, not physical measurements.

The [figure toolchain](../figures/README.md) generates bilingual full assembly, exploded and arena diagrams. `npm run figures:render` uses the committed GLB without rebuilding CAD. Purchased-part appearance details are illustrative.

The generic BOM, print order and wiring table remain as practical references; historical shopping quotes are available in Git history. Wiring entries explicitly flag unresolved supplier pin-label conflicts; verify actual pin functions before power. See the [public hardware guide](https://yaoqih.github.io/acfield/hardware/overview).
