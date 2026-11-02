#!/usr/bin/env python3
"""Check physical label geometry and decode PNGs plus rasterized print PDFs.

Install requirements-apriltag.txt, requirements-print.txt and Poppler first.
This checks digital artwork, not printed labels under the arena camera.
"""
import argparse
import faulthandler
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np
from pypdf import PdfReader

from apriltag_live import Detector

ROOT = Path(__file__).resolve().parent
MM = 72 / 25.4


def check_pdf_geometry(pdf, tags, directory):
    reader = PdfReader(pdf)
    assert len(reader.pages) == len(tags), pdf
    report = []
    for page, tag in zip(reader.pages, tags):
        size = tag['black_edge_mm']
        cell = size * MM / 8
        rects = []

        def rectangle(op, args, cm, tm):
            if op != b're':
                return
            x, y, w, h = map(float, args)
            if abs(w - cell) < .001 and abs(h - cell) < .001:
                a, b, c, d, e, f = cm
                rects.extend((a * px + c * py + e, b * px + d * py + f)
                             for px, py in [(x, y), (x+w, y+h)])

        text = page.extract_text(visitor_operand_before=rectangle)
        assert f'ID {tag["id"]:02d}' in text and 'FRONT' in text
        assert abs(float(page.mediabox.width) / MM - 210) < .001
        assert abs(float(page.mediabox.height) / MM - 297) < .001
        points = np.asarray(rects)
        source = cv2.imread(str(directory / 'source' / f'tag36_11_{tag["id"]:05d}.png'), 0)
        assert len(rects) == 2 * int(np.sum(source == 0))
        dimensions = np.ptp(points, axis=0) / MM
        assert np.max(np.abs(dimensions - size)) < .001, dimensions
        outer = size * 1.25
        left, bottom = (210 - outer) / 2, (297 - outer) / 2 + 7
        expected_min = np.array([left + size / 8, bottom + size / 8])
        assert np.max(np.abs(points.min(axis=0) / MM - expected_min)) < .001
        report.append({'pdf': str(pdf.relative_to(ROOT)), 'page': len(report)+1,
                       'id': tag['id'], 'black_edge_mm': dimensions.tolist(),
                       'outer_edge_mm': outer})
    return report


def main():
    faulthandler.enable()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-reports', action='store_true')
    args = parser.parse_args()
    directory = ROOT / 'output/apriltags_104mm'
    manifest = json.loads((directory / 'manifest.json').read_text())
    tags = manifest['tags']
    assert [t['id'] for t in tags] == [0, 1, 2, 3, 10, 11, 12, 13]
    assert all(t['black_edge_mm'] == (104 if t['role'] == 'robot' else 150) for t in tags)
    geometry, rendered = [], []
    with tempfile.TemporaryDirectory(prefix='acfield-labels-') as temporary:
        for key in ['pdf', 'robot_pdf']:
            pdf = ROOT / manifest[key]
            pdf_tags = tags if key == 'pdf' else [t for t in tags if t['role'] == 'robot']
            geometry.extend(check_pdf_geometry(pdf, pdf_tags, directory))
            prefix = Path(temporary) / key
            subprocess.run(['pdftoppm', '-r', '144', '-gray', '-png', str(pdf), str(prefix)],
                           check=True, capture_output=True)
            paths = sorted(Path(temporary).glob(f'{key}-*.png'))
            assert len(paths) == len(pdf_tags)
            rendered.extend((cv2.imread(str(path), 0), tag) for path, tag in zip(paths, pdf_tags))

    results = []
    for backend in ['native', 'opencv']:
        detector = Detector(backend=backend)
        count, max_error, margins = 0, 0., []

        def decode(image, tag_id, expected=None):
            nonlocal count, max_error
            found = detector.detect(image)
            assert len(found) == 1 and found[0]['id'] == tag_id, (backend, tag_id, found)
            assert found[0].get('hamming') in (None, 0)
            margin = found[0].get('margin')
            if margin is not None:
                assert margin >= 30
                margins.append(margin)
            if expected is not None:
                error = float(np.max(np.abs(np.asarray(found[0]['corners']) - expected)))
                assert error < 3, (backend, tag_id, error)
                max_error = max(max_error, error)
            count += 1

        for tag in tags:
            tag_id = tag['id']
            print(f'Checking {backend}: preview ID {tag_id}', flush=True)
            source_path = directory / 'source' / f'tag36_11_{tag_id:05d}.png'
            assert hashlib.sha256(source_path.read_bytes()).hexdigest() == tag['source_sha256']
            original = cv2.imread(str(directory / tag['png_file']), 0)
            source = cv2.imread(str(source_path), 0)
            canonical = cv2.resize(source, (1600, 1600), interpolation=cv2.INTER_NEAREST)
            difference = original != canonical
            # Quiet zone and code cells stay untouched; only dark ring marks differ.
            allowed = np.zeros((1600,1600), bool)
            allowed[160:320,160:1440] = True
            allowed[1280:1440,160:1440] = True
            assert difference.any() and np.all(allowed[difference])
            assert np.all(original[difference] <= 48)
            assert np.all(original[:160] == 255) and np.all(original[-160:] == 255)
            assert np.all(original[:,:160] == 255) and np.all(original[:,-160:] == 255)
            for size in [80,160,400]:
                image = cv2.resize(original, (size,size), interpolation=cv2.INTER_AREA)
                corners = np.float32([[size*.1,size*.1],[size*.9-1,size*.1],
                                      [size*.9-1,size*.9-1],[size*.1,size*.9-1]])
                for turn in range(4):
                    rotated = np.rot90(image, turn).copy()
                    expected = corners.copy()
                    for _ in range(turn):
                        expected = np.column_stack([expected[:,1], size-1-expected[:,0]])
                    decode(rotated, tag_id, expected)
                    src = np.float32([[0,0],[size-1,0],[size-1,size-1],[0,size-1]])
                    dst = np.float32([[.12,.06],[.98,.18],[.84,.96],[.02,.80]]) * (size-1)
                    matrix = cv2.getPerspectiveTransform(src, dst)
                    warped = cv2.warpPerspective(rotated, matrix, (size,size), borderValue=255)
                    warped = cv2.GaussianBlur(warped, (3,3), .6)
                    expected = cv2.perspectiveTransform(expected.reshape(1,4,2), matrix)[0]
                    decode(warped, tag_id, expected)
        for image, tag in rendered:
            print(f'Checking {backend}: PDF ID {tag["id"]}, shape={image.shape}', flush=True)
            outer = tag['outer_edge_with_white_margin_mm']
            left, bottom = (210-outer)/2, (297-outer)/2+7
            inset, size = tag['white_margin_each_side_mm'], tag['black_edge_mm']
            x, y = left + inset, 297 - bottom - inset - size
            expected = np.float32([[x,y],[x+size,y],[x+size,y+size],[x,y+size]]) * (144/25.4)
            decode(image, tag['id'], expected)
        results.append({'backend':backend, 'cases':count, 'failures':0,
                        'max_corner_error_px':max_error,
                        'minimum_decision_margin':min(margins) if margins else None})
    report = {'scope':'Digital artwork only; no screw occlusion or physical-camera test.',
              'png_cases':'8 IDs x 3 pixel sizes x 4 rotations x 2 perspectives x 2 backends',
              'pdf_cases':'12 A4 pages rasterized by Poppler at 144 dpi x 2 backends',
              'results':results}
    if args.write_reports:
        for name, data in [('pdf_geometry_check.json',geometry),('detection_check.json',report)]:
            (directory / name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    print(f'Validated {len(geometry)} vector PDF pages at <0.001 mm tolerance.')


if __name__ == '__main__':
    main()
