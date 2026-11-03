# Contributing to ACField

Questions and issues are welcome in Chinese or English. For substantial features, open an issue explaining the experiment, missing behavior, timing requirements and smallest useful change. Small fixes can go directly to a pull request.

## Development

- Python: from the repository root, run `uv sync --python 3.12 --extra test`. This installs the control server, SDK, vision service, CAD/print tools and test dependencies into the root `.venv`; the root `uv.lock` is the single Python lockfile.
- Platform tests: run `uv run --python 3.12 --extra test pytest -q` from the repository root. Run SDK tests with `cd sdk/python && uv run --python 3.12 pytest -q`; both commands use the same root `.venv`. Firmware contract tests also need a host C++ compiler and PlatformIO's ArduinoJson.
- Console: `npm --prefix robot_server/frontend ci` then `npm --prefix robot_server/frontend run build`.
- Vision-only setup: install `requirements-apriltag.txt`; run `python -m pytest -q tests/test_apriltag_live.py` from the root.
- Firmware: install PlatformIO and build the four environments.
- Docs: `npm ci && npm run docs:build`; preview with `npm run docs:dev`.

Protocol tests compile the actual firmware parser. Install a C++ compiler and run `pio pkg install -d esp32_software/firmware -e general-driver` first. CI requires these tests to execute. Set `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1` to require them locally.

## Review expectations

Keep changes focused. Update documentation and add regression coverage when changing control, timing, protocol or failure behavior. Distinguish software checks from physical measurements. Protocol changes must update both ends together and explain compatibility. Preserve safe startup, explicit arming, finite command lifetimes and fault stops. Never commit credentials, private recordings or local databases.

## Repository boundaries

The main repository maintains the common platform and small examples. Paper-specific training, weights and experiments should depend on a pinned platform commit in a separate repository.

Commit editable code/design sources, tests, documentation, dependency lockfiles and third-party notices. Keep official AprilTag source images once in `assets/apriltags/`; demos, printing and tests share them.

Generated files are committed only when they directly serve users: the two current printable PDFs in `output/pdf/`, current STL files and assembly model/parameters, and figures used or linked by the documentation. SVG and PNG documentation figures intentionally support web reading and presentation downloads. Update these artifacts with their sources.

Do not commit individual tag previews, generated manifests/check reports, local CAD audit reports or duplicate preview images. They can be reproduced with the documented commands and are ignored by Git. Historical size variants, shopping carts and design comparisons belong in Git history. Keep the current generic BOM, print order and wiring references. Avoid adding backups, caches, recordings, local databases or personal supplier quotations.

## License

Contributions are licensed under Apache-2.0. Identify provenance and licenses for third-party material.
