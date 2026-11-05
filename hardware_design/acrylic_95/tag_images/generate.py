"""Rebuild and decode compact labels using the repository's canonical sources."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import json

import cv2
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
SOURCE = ROOT / "assets/apriltags"


def main():
    records = {r["id"]:r for r in json.loads((SOURCE/"sources.json").read_text())}
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    paths = []
    for tag_id in range(10,22):
        record = records[tag_id]
        data = (SOURCE/record["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
        with Image.open(SOURCE/record["file"]) as src:
            src = src.convert("L")
        assert src.size == (10,10)
        black = src.crop((1,1,9,9)).resize((1440,1440),Image.Resampling.NEAREST)
        output = Image.new("L",(1600,1600),255)
        output.paste(black,(80,80))
        path = P/f"tag36h11_id{tag_id:02d}_80mm_black72mm.png"
        output.save(path,dpi=(508,508),optimize=True)
        with Image.open(path) as actual:
            assert actual.size == (1600,1600)
            assert abs(actual.info["dpi"][0]-508) < .1
            pixels = np.asarray(actual)
            assert np.all(pixels[:80,:] == 255) and np.all(pixels[-80:,:] == 255)
            assert np.all(pixels[:,:80] == 255) and np.all(pixels[:,-80:] == 255)
            assert np.array_equal(pixels[80:1520,80:1520],np.asarray(black))
        pixels = np.asarray(output)
        for turns in range(4):
            rotated = np.ascontiguousarray(np.rot90(pixels, turns))
            corners, ids, _ = detector.detectMarkers(rotated)
            assert ids is not None and len(ids) == 1 and int(ids[0, 0]) == tag_id
            quad = corners[0].reshape(4, 2)
            assert np.all((quad >= 0) & (quad < 1600))
        paths.append(path)
    with ZipFile(P/"tag36h11_80mm_white4_12ids_png.zip","w",ZIP_DEFLATED) as archive:
        for path in [*paths,P/"README.md"]:
            archive.write(path,path.name)
    with ZipFile(P/"tag36h11_80mm_white4_12ids_png.zip") as archive:
        for path in paths:
            assert archive.read(path.name) == path.read_bytes()
    print("12 labels: source hashes, dimensions, margins, 48 OpenCV AprilTag decodes and ZIP contents PASS")


if __name__ == "__main__":
    main()
