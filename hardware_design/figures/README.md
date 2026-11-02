# Hardware and arena figures

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

This reads the committed GLB and parameters, uses only local assets, and writes Chinese/English assembly, exploded and arena SVG/PNG files into `docs/public/images/`. `assembly.png` is the compact language-neutral homepage view. Intermediate frame captures live in ignored `.cache/`. Set `DOCS_CHROME_PATH` to a local Chrome executable if needed. Font rendering can vary slightly across systems.

After changing CAD geometry, regenerate and audit it first. The full review command also updates the 2D geometry/stability plots:

```bash
python -m pip install -r hardware_design/requirements.txt
python hardware_design/print_v11/build.py
python hardware_design/print_v11/audit.py
python hardware_design/print_v11/render.py
```

Tag textures come from the repository’s canonical tag36h11 images; see `THIRD_PARTY_NOTICES.md`. No vendor product photographs are used. Review original-size figures and desktop/mobile docs after edits.
