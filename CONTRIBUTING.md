# Contributing to ACField

Questions and issues are welcome in Chinese or English. For substantial features, open an issue explaining the experiment, missing behavior, timing requirements and smallest useful change. Small fixes can go directly to a pull request.

## Development

- Backend: `cd robot_server && uv sync --extra test && uv run pytest -q`.
- Python SDK: from the root, install `python -m pip install -e './robot_server[test]' -e './sdk/python[test]'`, then run `python -m pytest sdk/python/tests -q`. Keep API and SDK protocol changes in one pull request.
- Console: `npm --prefix robot_server/frontend ci` then `npm --prefix robot_server/frontend run build`.
- Vision: install `requirements-apriltag.txt`; run `python -m pytest -q tests/test_apriltag_live.py` from the root.
- Firmware: install PlatformIO and build the four environments.
- Docs: `npm ci && npm run docs:build`; preview with `npm run docs:dev`.

Protocol tests compile the actual firmware parser. Install a C++ compiler and run `pio pkg install -d esp32_software/firmware -e general-driver` first. CI requires these tests to execute. Set `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1` to require them locally.

## Review expectations

Keep changes focused. Update documentation and add regression coverage when changing control, timing, protocol or failure behavior. Distinguish software checks from physical measurements. Protocol changes must update both ends together and explain compatibility. Preserve safe startup, explicit arming, finite command lifetimes and fault stops. Never commit credentials, private recordings or local databases.

## Repository boundaries

The main repository maintains the common platform and small examples. Paper-specific training, weights and experiments should depend on a pinned platform commit in a separate repository.

## License

Contributions are licensed under Apache-2.0. Identify provenance and licenses for third-party material.
