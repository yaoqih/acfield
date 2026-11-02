# Third-party notices

Original ACField code, documentation and reference design files are distributed under Apache-2.0. Third-party material retains its original license.

## AprilTag marker images

Canonical tag36h11 images in `output/apriltags/source/`, `output/apriltags_90mm/source/` and `output/apriltags_104mm/source/` originate from [AprilRobotics/apriltag-imgs](https://github.com/AprilRobotics/apriltag-imgs). Printed PNG/PDF markers are derived from these images. The upstream BSD-2-Clause license is reproduced in [`third_party/apriltag-imgs-LICENSE`](third_party/apriltag-imgs-LICENSE). Generation manifests record source URLs and SHA-256 hashes.

## Embedded label font

The printable label PDFs embed a subset of Bitstream Vera Sans, provided with ReportLab; PNG annotations use the same font. Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. Bitstream Vera is a trademark of Bitstream, Inc. Its copyright and permission notice are reproduced in [`third_party/bitstream-vera-LICENSE`](third_party/bitstream-vera-LICENSE). The font is installed with ReportLab rather than bundled as a separate font file in this repository.

## Dependencies and board references

Python, JavaScript, PlatformIO and CAD dependencies are installed separately and retain their respective licenses. Consult the dependency manifests and lockfiles. Waveshare General Driver for Robots is the reference controller board; vendor firmware, schematics and documentation are not redistributed here. The board name identifies compatibility. Mechanical models use simplified purchased-part envelopes. Supplier dimensions must be checked against actual components.
