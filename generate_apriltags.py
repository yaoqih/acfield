#!/usr/bin/env python3
"""Create vector A4 PDFs and PNG previews from official tag36h11 images."""

import argparse
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

import reportlab
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


SOURCE_BASE = "https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11"
FAMILY = "tag36h11"
LABEL_FONT = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
pdfmetrics.registerFont(TTFont("ACFieldLabel", str(LABEL_FONT)))
ANNOTATION_GRAY = 48  # Small, low-contrast marks inside the black detection ring.


def marker_primitives(image, tag_id, size_mm, annotated=True):
    """Shared PDF/PNG geometry, in mm from the complete label's bottom left.

    Only the interior of the black ring is annotated. The code cells, ring
    edges and full one-cell white quiet zone retain their official geometry.
    The arrow points to the canonical top edge (corners 0 and 1 in vision).
    """
    cell = size_mm / 8
    for row in range(10):
        for col in range(10):
            if image.getpixel((col, row)) == 0:
                yield ("rect", 0, col * cell, (9 - row) * cell, cell, cell)
    if annotated:
        # All positions are well inside the solid black ring, never the data.
        yield ("text", ANNOTATION_GRAY, 5 * cell, 1.42 * cell,
               .154 * cell, f"ID {tag_id:02d}")
        yield ("text", ANNOTATION_GRAY, 5 * cell, 8.22 * cell,
               .115 * cell, "FRONT")
        for x1, y1, x2, y2 in [(5, 8.48, 5, 8.84),
                                  (4.89, 8.71, 5, 8.84),
                                  (5.11, 8.71, 5, 8.84)]:
            yield ("line", ANNOTATION_GRAY, x1 * cell, y1 * cell,
                   x2 * cell, y2 * cell, .023 * cell)


def draw_marker(canvas, image, tag_id, size_mm, left, bottom):
    """Vector output; left and bottom are PDF points."""
    canvas.saveState()
    canvas.translate(left, bottom)
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(0, 0, size_mm * 1.25 * mm, size_mm * 1.25 * mm,
                stroke=0, fill=1)
    for kind, gray, *values in marker_primitives(image, tag_id, size_mm):
        canvas.setFillGray(gray / 255)
        canvas.setStrokeGray(gray / 255)
        if kind == "rect":
            canvas.rect(*(v * mm for v in values), stroke=0, fill=1)
        elif kind == "text":
            x, y, font_mm, text = values
            canvas.setFont("ACFieldLabel", font_mm * mm)
            canvas.drawCentredString(x * mm, y * mm, text)
        else:
            x1, y1, x2, y2, line_mm = values
            canvas.setLineWidth(line_mm * mm)
            canvas.setLineCap(1)
            canvas.line(x1 * mm, y1 * mm, x2 * mm, y2 * mm)
    canvas.restoreState()


def marker_preview(image, tag_id, size_mm, pixels=1600):
    """Rasterize the same physical geometry as the PDF, without page furniture."""
    result = Image.new("L", (pixels, pixels), 255)
    draw = ImageDraw.Draw(result)
    scale = pixels / (size_mm * 1.25)
    for kind, gray, *values in marker_primitives(image, tag_id, size_mm):
        if kind == "rect":
            x, y, width, height = values
            draw.rectangle((round(x * scale), pixels - round((y + height) * scale),
                            round((x + width) * scale) - 1,
                            pixels - round(y * scale) - 1), fill=gray)
        elif kind == "text":
            x, y, font_mm, text = values
            font = ImageFont.truetype(str(LABEL_FONT), round(font_mm * scale))
            draw.text((x * scale, pixels - y * scale), text, font=font,
                      anchor="ms", fill=gray)
        else:
            x1, y1, x2, y2, line_mm = values
            draw.line((x1 * scale, pixels - y1 * scale,
                       x2 * scale, pixels - y2 * scale),
                      fill=gray, width=max(1, round(line_mm * scale)))
    return result


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
                      "Keep the full white margin. Small ID and FRONT marks sit inside the black ring.")

    draw_marker(canvas, image, tag_id, size_mm, left, bottom)
    # Crop guides sit entirely outside the white quiet zone.
    canvas.setStrokeGray(.55)
    canvas.setLineWidth(.25)
    for x, sx in [(left, -1), (left + outer, 1)]:
        for y, sy in [(bottom, -1), (bottom + outer, 1)]:
            canvas.line(x + sx * mm, y, x + sx * 4 * mm, y)
            canvas.line(x, y + sy * mm, x, y + sy * 4 * mm)

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
    parser.add_argument("--robot-size-mm", type=float, default=104)
    parser.add_argument("--output-dir", type=Path, default=Path("output/apriltags_104mm"))
    parser.add_argument("--pdf", type=Path,
                        default=Path("output/pdf/apriltag36h11_ground150_robot104_A4.pdf"))
    parser.add_argument("--robot-pdf", type=Path,
                        help="Also write a separate A4 PDF containing only robot labels.")
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

    if args.robot_pdf and args.robot_pdf.resolve() == args.pdf.resolve():
        parser.error("--robot-pdf must differ from --pdf.")
    canvas = Canvas(str(args.pdf), pagesize=A4, pageCompression=1, invariant=1)
    canvas.setTitle("AprilTag tag36h11 - fixed markers and robot markers")
    canvas.setAuthor("AClab / ACField")
    manifest = []
    for page, ((tag_id, role, size_mm), (im, url, sha)) in enumerate(zip(specs, sources), 1):
        png_path = args.output_dir / f"{FAMILY}_id{tag_id:03d}_{role}.png"
        marker_preview(im, tag_id, size_mm).save(png_path)
        draw_page(canvas, im, tag_id, role, size_mm, page, len(specs))
        manifest.append({
            "family": FAMILY, "id": tag_id, "role": role, "pdf_page": page,
            "black_edge_mm": size_mm, "tagsize_m": size_mm / 1000,
            "white_margin_each_side_mm": size_mm / 8,
            "outer_edge_with_white_margin_mm": size_mm * 1.25,
            "source_url": url, "source_sha256": sha,
            "png_file": png_path.name,
            "annotation": {"location": "inside black ring",
                           "gray_rgb": [ANNOTATION_GRAY] * 3,
                           "id_text": f"ID {tag_id:02d}",
                           "front": "canonical top edge, corners 0 and 1"},
        })
    canvas.save()
    if args.robot_pdf:
        args.robot_pdf.parent.mkdir(parents=True, exist_ok=True)
        robot_canvas = Canvas(str(args.robot_pdf), pagesize=A4, pageCompression=1, invariant=1)
        robot_canvas.setTitle("ACField - robot top-cover labels")
        robot_canvas.setAuthor("AClab / ACField")
        robot_specs = [(spec, source) for spec, source in zip(specs, sources)
                       if spec[1] == "robot"]
        for page, ((tag_id, role, size_mm), (im, _, _)) in enumerate(robot_specs, 1):
            draw_page(robot_canvas, im, tag_id, role, size_mm, page, len(robot_specs))
        robot_canvas.save()
        print(f"Created {args.robot_pdf} ({len(robot_specs)} A4 pages)")
    (args.output_dir / "manifest.json").write_text(
        json.dumps({"pdf": str(args.pdf),
                    "robot_pdf": str(args.robot_pdf) if args.robot_pdf else None,
                    "layout": "full square, no screw cutouts or screw avoidance",
                    "png_note":
                    "PNG previews have no guaranteed physical print size; use the vector PDF at 100%.",
                    "tags": manifest}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {args.pdf} ({len(specs)} A4 pages)")
    print(f"PNG previews, cached official sources and manifest: {args.output_dir}")


if __name__ == "__main__":
    main()
