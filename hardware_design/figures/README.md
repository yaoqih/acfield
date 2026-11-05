# Hardware and arena figures

The current compact acrylic candidate has a separate DXF-based generator:

```sh
uv run --with ezdxf --with shapely python hardware_design/acrylic_95/review.py
cp hardware_design/acrylic_95/audit_layout.png docs/public/images/acrylic-95-audit.png
cp hardware_design/acrylic_95/exploded.png docs/public/images/acrylic-95-exploded.png
```

It produces the 95 mm audit and exploded figures plus `audit_results.json`. Plate cuts come from the committed DXFs; purchased parts are simplified, and installed dimensions are documented in `acrylic_95/dimensions.md`. Red circles mark an unresolved top-fastener/tag conflict. It does not change the V11 images below. See the compact README for physical-fit limitations.

## V11 figures

`scene.mjs` loads the audited `print_v11/assembly.glb` into Three.js. Printed parts use actual mesh geometry; motors, the battery, controller and connector details are simplified visual references. These appearance details do not replace supplier drawings, wiring instructions or collision envelopes in `build.py`/`audit.py`.

Opaque surfaces, generated face normals and a depth buffer avoid transparent-triangle sorting artifacts. The assembled view preserves nominal positions. The exploded view offsets component groups for clarity and turns the caster over to expose its ball. It is an assembly illustration, not a dimensioned manufacturing drawing.

`arena.mjs` generates editable bilingual SVGs for a 3 × 3 m arena, external side mast, right-angle boom and camera above the centre. It shows wired camera-to-server and server-to-router links plus wireless robot links. Camera height is deliberately unspecified; choose it from actual lens coverage, resolution and measured tag quality.

## Regenerate

From the repository root (Node 22 recommended):

```bash
npm ci
npx playwright install chromium
npm run figures:render
```

This reads the committed GLB and parameters, uses only local assets, and writes Chinese/English assembly, exploded and arena SVG files into `docs/public/images/`. `assembly.png` is the compact language-neutral homepage view. Embedded model images and the homepage preview are limited to 600 pixels wide; docs do not publish duplicate PNG downloads. Hardware previews remain in `print_v11/`. Intermediate frame captures live in ignored `.cache/`. Set `DOCS_CHROME_PATH` to a local Chrome executable if needed. Font rendering can vary slightly across systems.

After changing CAD geometry, regenerate and audit it first. The full review command also updates the 2D geometry/stability plots:

```bash
python -m pip install -r hardware_design/requirements.txt
python hardware_design/print_v11/build.py
python hardware_design/print_v11/audit.py
python hardware_design/print_v11/render.py
```

Tag textures use the full-cover labels in `docs/public/images/robot-tag.png`, derived from official tag36h11 images with subtle ID/FRONT marks inside the black ring. The texture fills the 130 mm cover and FRONT points toward chassis +X. See `THIRD_PARTY_NOTICES.md`. No vendor product photographs are used. Review inline figures and desktop/mobile docs after edits.
