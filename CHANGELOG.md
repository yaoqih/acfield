# Changelog

## Unreleased

### Documentation and experiment workflow

- Added bilingual state dictionaries with generated fresh/stale snapshots,
  coordinate diagrams, offset calculations and complete configuration examples.
- Added an executable two-robot tutorial, experiment manifests, a JSONL analyzer,
  trajectory CSV/plots and a small dataset captured from the actual demo server.
- Documented event fields, time bases, command/ACK correlation and recording gaps.
- Added hardware compatibility tables, quantitative calibration procedures and
  explicitly illustrative acceptance records.
- Simplified quick start, moved joystick details into manual control, and moved
  historical telemetry investigations into a case study.
- Added backup, commit pinning, upgrade and rollback instructions, and displayed
  the build revision on documentation pages.
- Generate published defaults from real configuration and execute core tutorial
  snippets in CI with bilingual and JSON/model checks.

### Runtime corrections

- Keep duplicate or delayed vision frames from refreshing camera availability.
- Integrate exact demo arcs and enforce the configured body boundary margin.
- Refresh browser-test builds and isolate console settings between tests.

These changes are tracked for the next release. Use a complete commit to identify
the development version used for an experiment.

- Replaced transparent CAD previews with depth-buffered assembly/exploded views,
  corrected the assembled tag-cover orientation, and added bilingual 3 × 3 m
  arena/camera/network drawings with reproducible figure sources.

- Replaced the one-way English link with VitePress locale routing, complete
  English documentation, translated menus and same-topic language switching.

- Print console/API addresses and detected host IPv4 at server startup, including
  the LAN SDK URL when bound to all IPv4 interfaces.

- Added the independently installable `acfield` Python SDK with typed snapshots,
  explicit single/joint velocity commands, HTTP error details and managed control
  sessions that wait for arming confirmation and release on exit.
- Added atomic, ownership-conditional `POST /api/robots/{id}/release` so cleanup
  cannot disarm a new controller. Existing explicit disarm semantics are unchanged.
- Migrated the bounded velocity example to the SDK, documented its lifecycle and
  installation, and added installed-package integration CI on Python 3.11–3.13.

### Initial public development preview

- Curated the server, console, AprilTag service and ESP32 firmware.
- Included one V11 reference design with generation sources and geometry checks.
- Added design rationale, operating guides, research boundaries and a bounded Python example.
- Added platform CI and documentation deployment to GitHub Pages.
- Fixed native AprilTag resource cleanup order exposed by Linux CI; repeated
  detector creation, detection and destruction now has subprocess regression coverage.

This preview does not imply a stable 1.0 API, physical performance certification, research benchmark or published paper.
