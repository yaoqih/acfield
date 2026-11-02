# Changelog

## Unreleased

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
