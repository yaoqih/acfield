#!/usr/bin/env python3
"""Create vector A4 PDFs and PNG previews from official tag36h11 images."""

import argparse
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


SOURCE_BASE = "https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11"
FAMILY = "tag36h11"


def get_source(tag_id, source_dir):
    name = f"tag36_11_{tag_id:05d}.png"
    url = f"{SOURCE_BASE}/{name}"
    path = source_dir / name
    cached = Path("output/apriltags/source") / name
    if path.exists():
        data = path.read_bytes()
    elif cached.exists():
        data = cached.read_bytes()
    else:
        request = Request(url, headers={"User-Agent": "AprilTag-print-generator/1.0"})
        with urlopen(request, timeout=30) as response:
            data = response.read()
    with Image.open(io.BytesIO(data)) as source:
        im = source.convert("L")
    if im.size != (10, 10) or not set(im.tobytes()) <= {0, 255}:
        raise ValueError(f"Unexpected official image for ID {tag_id}: {im.size}")
    if any(im.getpixel((x, y)) != 255 for x in range(10) for y in range(10)
           if x in (0, 9) or y in (0, 9)):
        raise ValueError(f"Missing outer white cells for ID {tag_id}")
    if any(im.getpixel((x, y)) != 0 for x in range(1, 9) for y in range(1, 9)
           if x in (1, 8) or y in (1, 8)):
        raise ValueError(f"Unexpected black detection border for ID {tag_id}")
    path.write_bytes(data)
    return im, url, hashlib.sha256(data).hexdigest()


def draw_page(canvas, image, tag_id, role, size_mm, page_no, page_count):
    width, height = A4
    # The official 10x10 image contains an 8x8 detection square and one
    # white cell on each side. tagsize is the 8-cell BLACK square, not 10.
    cell = size_mm * mm / 8
    outer = cell * 10
    left = (width - outer) / 2
    bottom = (height - outer) / 2 + 7 * mm

    canvas.setFillColorRGB(0, 0, 0)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(14 * mm, height - 18 * mm, f"APRILTAG / {role.upper()} {tag_id}")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(14 * mm, height - 26 * mm,
                      f"Family: {FAMILY}    ID: {tag_id}    Black outer edge: {size_mm:g} mm")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(14 * mm, height - 33 * mm,
                      "Keep the white margin. All text and scale marks stay outside it.")

    # Vector rectangles keep every tag cell sharp at any printer resolution.
    for row in range(10):
        for col in range(10):
            if image.getpixel((col, row)) == 0:
                canvas.rect(left + col * cell, bottom + (9 - row) * cell,
                            cell, cell, stroke=0, fill=1)

    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(width / 2, bottom - 8 * mm,
                             f"Measure BLACK square: {size_mm:g} x {size_mm:g} mm")
    canvas.drawCentredString(width / 2, bottom - 14 * mm,
                             f"White-margin square: {size_mm * 1.25:g} x {size_mm * 1.25:g} mm")

    canvas.setLineWidth(0.6)
    ruler_left = (width - 100 * mm) / 2
    ruler_y = 25 * mm
    canvas.line(ruler_left, ruler_y, ruler_left + 100 * mm, ruler_y)
    for tick in range(0, 101, 10):
        length = 3 if tick % 50 == 0 else 1.8
        canvas.line(ruler_left + tick * mm, ruler_y - length * mm,
                    ruler_left + tick * mm, ruler_y + length * mm)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width / 2, 17 * mm, "Check with a ruler: this line is 100 mm.")
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(width / 2, 10 * mm,
                             "PRINT 100% / ACTUAL SIZE - DISABLE FIT TO PAGE")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 12 * mm, 5 * mm, f"{page_no} / {page_count}")
    canvas.showPage()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-ids", type=int, nargs="*", default=[0, 1, 2, 3])
    parser.add_argument("--robot-ids", type=int, nargs="+", default=[10, 11, 12, 13])
    parser.add_argument("--fixed-size-mm", type=float, default=150)
    parser.add_argument("--robot-size-mm", type=float, default=90)
    parser.add_argument("--output-dir", type=Path, default=Path("output/apriltags_90mm"))
    parser.add_argument("--pdf", type=Path,
                        default=Path("output/pdf/apriltag36h11_ground150_robot90_A4.pdf"))
    args = parser.parse_args()
    ids = args.fixed_ids + args.robot_ids
    if len(set(ids)) != len(ids) or any(i < 0 or i > 586 for i in ids):
        parser.error("Use unique tag36h11 IDs between 0 and 586.")
    # Fixed headers/footers and an outer quiet zone must all fit on A4.
    if any(not 20 <= size <= 150 for size in (args.fixed_size_mm, args.robot_size_mm)):
        parser.error("This A4 layout supports black-square edges from 20 to 150 mm.")

    source_dir = args.output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    args.pdf.parent.mkdir(parents=True, exist_ok=True)
    specs = ([(i, "fixed", args.fixed_size_mm) for i in args.fixed_ids]
             + [(i, "robot", args.robot_size_mm) for i in args.robot_ids])
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(lambda s: get_source(s[0], source_dir), specs))

    canvas = Canvas(str(args.pdf), pagesize=A4, pageCompression=1)
    canvas.setTitle("AprilTag tag36h11 - fixed markers and robot markers")
    canvas.setAuthor("Multi-agent research platform")
    manifest = []
    for page, ((tag_id, role, size_mm), (im, url, sha)) in enumerate(zip(specs, sources), 1):
        png_path = args.output_dir / f"{FAMILY}_id{tag_id:03d}_{role}.png"
        im.resize((1600, 1600), Image.Resampling.NEAREST).save(png_path)
        draw_page(canvas, im, tag_id, role, size_mm, page, len(specs))
        manifest.append({
            "family": FAMILY, "id": tag_id, "role": role, "pdf_page": page,
            "black_edge_mm": size_mm, "tagsize_m": size_mm / 1000,
            "white_margin_each_side_mm": size_mm / 8,
            "outer_edge_with_white_margin_mm": size_mm * 1.25,
            "source_url": url, "source_sha256": sha,
            "png_file": png_path.name,
        })
    canvas.save()
    (args.output_dir / "manifest.json").write_text(
        json.dumps({"pdf": str(args.pdf), "png_note":
                    "PNG previews have no guaranteed physical print size; use the vector PDF at 100%.",
                    "tags": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {args.pdf} ({len(specs)} A4 pages)")
    print(f"PNG previews, cached official sources and manifest: {args.output_dir}")


if __name__ == "__main__":
    main()
