"""Index supplied parameter images and copy existing fabrication files for the docs."""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_DATE = "2026-11-15"
IMAGE_SOURCES = [
    ("主控板接口1.png", ["B01"], "https://item.taobao.com/item.htm?id=923727056922"),
    ("主控板参数2.png", ["B01"], "https://item.taobao.com/item.htm?id=923727056922"),
    ("主控板尺寸.png", ["B01"], "https://item.taobao.com/item.htm?id=923727056922"),
    ("电机参数.png", ["B02"], "https://item.taobao.com/item.htm?id=777868414369"),
    ("电机尺寸.png", ["B02"], "https://item.taobao.com/item.htm?id=777868414369"),
    ("电机接线.png", ["B02"], "https://item.taobao.com/item.htm?id=777868414369"),
    ("电机支架.png", ["B02"], "https://item.taobao.com/item.htm?id=777868414369"),
    ("轮子尺寸.png", ["B05"], "https://item.taobao.com/item.htm?id=708154853977"),
    ("万向轮参数.png", ["B06"], "https://item.taobao.com/item.htm?id=923727056922"),
    ("电池.png", ["B03", "B04"], "https://item.taobao.com/item.htm?id=39418236809"),
    ("摄像头参数.png", ["B11"], "https://item.taobao.com/item.htm?id=655976902051"),
]
FABRICATION_FILES = [
    "hardware_design/acrylic_95/95x80_flat_cutting_dxf.zip",
    "hardware_design/acrylic_95/bottom_plate_95.1x80_flat_4mm.dxf",
    "hardware_design/acrylic_95/top_plate_95x80_flat_2mm.dxf",
    "hardware_design/acrylic_95/tag_images/tag36h11_80mm_white4_12ids_png.zip",
]


def fingerprint(path: Path) -> dict:
    content = path.read_bytes()
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    images = ROOT / "docs/public/images"
    entries = []
    for filename, bom_ids, source_url in IMAGE_SOURCES:
        path = images / filename
        content = path.read_bytes()
        if content[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError(f"Expected PNG: {path}")
        width, height = struct.unpack(">II", content[16:24])
        entries.append({
            "filename": filename,
            "path": path.relative_to(ROOT).as_posix(),
            "bom_ids": bom_ids,
            "source_url": source_url,
            "source_basis": "User-supplied image and associated purchasing URL; exact upstream image URL and capture date unknown.",
            "captured_at": None,
            "width_px": width,
            "height_px": height,
            **fingerprint(path),
        })
    write_json(images / "hardware-parameters.json", {
        "archived_on": ARCHIVE_DATE,
        "rights": "Original supplier/brand material retains its respective rights.",
        "images": entries,
    })

    destination = ROOT / "docs/public/downloads/hardware"
    destination.mkdir(parents=True, exist_ok=True)
    files = []
    for source_path in FABRICATION_FILES:
        source = ROOT / source_path
        target = destination / source.name
        shutil.copyfile(source, target)
        expected = fingerprint(source)
        if fingerprint(target) != expected:
            raise ValueError(f"Copy differs from source: {target}")
        files.append({"source_path": source_path, "filename": target.name, **expected})
    write_json(destination / "manifest.json", {
        "archived_on": ARCHIVE_DATE,
        "basis": "Copies of existing project files; first-article design, unresolved tag/fastener conflict.",
        "files": files,
    })
    print(f"Indexed {len(entries)} unchanged images; copied and verified {len(files)} fabrication/printing files.")


if __name__ == "__main__":
    main()
