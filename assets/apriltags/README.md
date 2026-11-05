# AprilTag sources and printable labels

This is the single canonical copy of official tag36h11 images for IDs 0–3 and 10–21. The 10 × 10 pixel PNGs include the 8 × 8 black detection square and a one-cell white quiet zone. Printing, the synthetic demo and detector tests share these sources; image pixels alone do not define physical size. Source URLs and SHA-256 hashes are recorded in `sources.json`; see [third-party notices](../../THIRD_PARTY_NOTICES.md).

The older V11 PDF labels (IDs 0–3 and 10–17) use a **104 mm black square and a 130 × 130 mm complete square**, including 13 mm of white margin on every side. No screw cutouts. Small dark-gray ID/FRONT marks sit inside the black ring. Align FRONT with robot +X.

The [compact acrylic candidate](../../hardware_design/acrylic_95/tag_images/README.md) separately exports IDs 10–21 as 80 mm PNGs with a 72 mm black square and 4 mm white margin per side. Its generator crops the original quiet zone and adds this narrower margin explicitly. It has no added text; align the standard image top with robot +X. Existing runtime IDs and sizes do not change when images are added. Validate the narrow white margin with the arena camera and resolve the top fastener conflict before use.

- [A4 PDF, twelve pages](../../output/pdf/apriltag36h11_130mm_A4.pdf): one label per sheet, with dimensions, crop guides and a 100 mm ruler.
- [Tag-only PDF, twelve pages](../../output/pdf/apriltag36h11_130mm_tag_only.pdf): each page is exactly 130 × 130 mm, with no extra page whitespace or instructions. The required white quiet zone remains.

Print at 100% actual size. Use `size_m=0.104` for these V11 PDFs; compact PNGs use nominal `0.072`. Configure ground markers independently; when changing them, update their measured positions and recalibrate the arena.

```sh
python -m pip install -r requirements-print.txt
python generate_apriltags.py
# Also install requirements-apriltag.txt and Poppler for verification
python verify_apriltags.py --write-reports
```

The V11 publications are the two PDFs and the documentation's single ID 10 preview; compact PNGs and their ZIP are committed under `hardware_design/acrylic_95/tag_images/`. V11 individual PNG previews, generation manifests and verification reports go to ignored `output/apriltags/`. V11 verification checks both PDFs, all 24 page sizes, the complete quiet zone and decoding/orientation under scale, rotation and perspective. The compact generator separately verifies all 12 PNGs. Neither replaces measurement and arena-camera checks after printing. The synthetic demo keeps independently defined tag dimensions and continues to show four corners plus four robots.
