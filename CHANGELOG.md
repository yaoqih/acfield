# Changelog

## Unreleased — initial public development preview

- Curated the server, console, AprilTag service and ESP32 firmware.
- Included one V11 reference design with generation sources and geometry checks.
- Added design rationale, operating guides, research boundaries and a bounded Python example.
- Added platform CI and documentation deployment to GitHub Pages.
- Fixed native AprilTag resource cleanup order exposed by Linux CI; repeated
  detector creation, detection and destruction now has subprocess regression coverage.

This preview does not imply a stable 1.0 API, physical performance certification, research benchmark or published paper.
