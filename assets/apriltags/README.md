# AprilTag sources and printable labels

This is the single canonical copy of official tag36h11 images for IDs 0–3 and 10–13. The 10 × 10 pixel PNGs include the 8 × 8 black detection square and a one-cell white quiet zone. Printing, the synthetic demo and detector tests share these sources; image pixels alone do not define physical size. Source URLs and SHA-256 hashes are recorded in `sources.json`; see [third-party notices](../../THIRD_PARTY_NOTICES.md).

All physical labels use a **104 mm black square and a 130 × 130 mm complete square**, including 13 mm of white margin on every side. No screw cutouts. Small dark-gray ID/FRONT marks sit inside the black ring. Align FRONT with robot +X.

- [A4 PDF, eight pages](../../output/pdf/apriltag36h11_130mm_A4.pdf): one label per sheet, with dimensions, crop guides and a 100 mm ruler.
- [Tag-only PDF, eight pages](../../output/pdf/apriltag36h11_130mm_tag_only.pdf): each page is exactly 130 × 130 mm, with no extra page whitespace or instructions. The required white quiet zone remains.

Print at 100% actual size. Use `size_m=0.104` for both ground and robot markers; when changing historical ground labels, update their measured positions and recalibrate the arena.

```sh
python -m pip install -r requirements-print.txt
python generate_apriltags.py
# Also install requirements-apriltag.txt and Poppler for verification
python verify_apriltags.py --write-reports
```

Only the two current PDFs and the documentation's single ID 10 preview are published artifacts. Individual PNG previews, generation manifests and verification reports go to ignored `output/apriltags/`. Verification checks both PDFs, all 16 page sizes, the complete quiet zone and decoding/orientation under scale, rotation and perspective. It does not replace measurement and arena-camera checks after printing. The synthetic demo keeps independently defined tag dimensions.
