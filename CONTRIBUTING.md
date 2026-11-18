# Contributing to ACField

Questions and issues are welcome in Chinese or English. For substantial features, open an issue explaining the experiment, missing behavior, timing requirements and smallest useful change. Small fixes can go directly to a pull request.

## Development

- Python: from the repository root, run `uv sync --python 3.12 --extra test`. This installs the control server, SDK, vision service, CAD/print tools and test dependencies into the root `.venv`; the root `uv.lock` is the single Python lockfile.
- Platform tests: run `uv run --python 3.12 --extra test pytest -q` from the repository root. Run SDK tests with `cd sdk/python && uv run --python 3.12 pytest -q`; both commands use the same root `.venv`. Firmware contract tests also need a host C++ compiler and PlatformIO's ArduinoJson.
- Console: `npm --prefix robot_server/frontend ci` then `npm --prefix robot_server/frontend run build`.
- The localization test setup uses `python -m pip install -r requirements-apriltag.txt -r requirements-print.txt './robot_server[test]'`. Configuration tests exercise the real control API and require its dependencies. From the root, run `python -m pytest -q tests/test_apriltag_live.py tests/test_vision_configuration.py`.
- Firmware: install PlatformIO and build the four environments.
- Docs: `npm ci && npm run docs:build`; preview with `npm run docs:dev`.
- Browser regressions use the root npm dependencies and Chromium (`npx playwright install chromium`). Run `npm run console:test`, `npm run vision:test` and `npm run docs:test` sequentially. Console tests also need the frontend npm dependencies. Console and documentation tests build fresh assets before starting their servers. `DOCS_TEST_URL` selects an already-running documentation site instead.

Protocol tests compile the actual firmware parser. Install a C++ compiler and run `pio pkg install -d esp32_software/firmware -e general-driver` first. CI requires these tests to execute. Set `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1` to require them locally.

`uv run --frozen --extra test python -m pytest -q tests/test_documentation.py` checks generated firmware/server defaults, serialized state examples, bilingual executable snippets and JSON. It starts an isolated demo server, executes the documented experiment and analyzer, and verifies stopping and ownership release. This check uses the full workspace environment in the browser CI job.

After changing defaults, run `uv run --frozen python tools/documentation_defaults.py`. After changing state serialization, run `uv run --frozen python tools/documentation_samples.py`. Commit the generated reference files with the implementation. Update Chinese and English parameter descriptions together. Console browser tests reset fleet configuration through a shared fixture.

## VS Code local tests

Open the repository root in VS Code and accept the recommended Python and Playwright extensions. Run **Tasks: Run Task → ACField: Setup Local Tests** once to sync Python 3.12 from `uv.lock`, install both npm lockfiles, install Chromium and prepare the firmware dependencies. Prerequisites are `uv`, Node.js/npm (CI uses Node 22), a host C++ compiler and Poppler's `pdftoppm` for physical-label checks. macOS needs the Xcode command-line tools for C++; Linux also needs Playwright's Chromium system libraries, installed with `npx playwright install --with-deps chromium`.

The **Testing** panel discovers Python tests from `tests`, `robot_server/tests` and `sdk/python/tests`, with the workspace `.venv` as the default interpreter. If VS Code previously selected another interpreter, use **Python: Select Interpreter** to select this repository's `.venv`. The checked-in `.vscode/test.env` makes missing firmware-contract dependencies fail instead of silently skipping those tests. Individual tests support Run and Debug. The Playwright extension discovers the documentation, console and vision configurations; enable the desired configurations in its Testing sidebar. Documentation and console browser tests build fresh assets automatically in VS Code.

Use **Tasks: Run Test Task → CI: All Checks** for the local counterpart of both GitHub Actions workflows. Individual jobs are available under **Tasks: Run Task**:

| GitHub Actions job | VS Code task |
| --- | --- |
| SDK tests and strict types | `CI: SDK Tests`, `CI: SDK Types` |
| Backend, real firmware parser and native state machine | `CI: Control and Firmware Contract` (pytest also compiles/runs the native protocol regression) |
| Localization | `CI: Vision Tests` |
| Physical label generation and both detection backends | `CI: Verify Labels` (generates artwork first) |
| Console types and production bundle | `CI: Console Build` |
| Console and vision browser regressions | `ACField: Console Browser Tests`, `ACField: Vision Browser Tests` |
| All four firmware environments | `CI: Firmware Builds (4 Cars)` |
| Documentation build and browser regressions | `CI: Docs Tests` (builds first) |
| Executable documentation and generated references | `CI: Documentation Examples` |

These tasks run the same checks locally on Python 3.12 using the workspace's locked dependencies; GitHub additionally tests installed SDK packages on Python 3.11/3.12/3.13 in clean Ubuntu runners. Local tasks do not deploy Pages or upload artifacts. PlatformIO 6.1.18 runs in a cached temporary uv environment, keeping its dependencies separate from the server's environment. `ACField: All Python Tests` combines the Python suites in one run. Label checks regenerate files under `output/apriltags` and the two printable PDFs under `output/pdf`.

For an optional parallel Python run, select **ACField: All Python Tests (4 Workers)**. It uses pytest-xdist and the same strict firmware checks as the serial task. Performance depends on the machine and workload; worker startup and competing native builds can make it slower. The Testing panel remains serial so individual tests can be debugged normally. To experiment with another worker count from a terminal, run `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1 uv run --frozen --python 3.12 --extra test python -m pytest -n 2 -q tests robot_server/tests sdk/python/tests`.

## Review expectations

Keep changes focused. Update documentation and add regression coverage when changing control, timing, protocol or failure behavior. Distinguish software checks from physical measurements. Protocol changes must update both ends together and explain compatibility. Preserve startup stops, device-confirmed control handshakes, finite command lifetimes and fault stops. Never commit credentials, private recordings or local databases.

## Repository boundaries

The main repository maintains the common platform and small examples. Paper-specific training, weights and experiments should depend on a pinned platform commit in a separate repository.

Commit editable code/design sources, tests, documentation, dependency lockfiles and third-party notices. Keep official AprilTag source images once in `assets/apriltags/`; demos, printing and tests share them.

Generated files are committed when they directly serve users, including the two current printable PDFs in `output/pdf/`, current STL files and assembly model/parameters, documentation figures, generated default tables, state illustrations and the small public demo dataset under `docs/public/examples/first-run/`. The demo dataset includes its source JSONL, manifest, CSV, summary and plot. Regenerate it into a new directory with `uv run --frozen python tools/documentation_demo.py --output output/docs-demo`, inspect it, then update the published sample together. SVG and PNG documentation figures support web reading and downloads.

Do not commit individual tag previews, generated manifests/check reports, local CAD audit reports or duplicate preview images. They can be reproduced with the documented commands and are ignored by Git. Historical size variants, shopping carts and design comparisons belong in Git history. Keep the current generic BOM, print order and wiring references. Avoid adding backups, caches, recordings, local databases or personal supplier quotations.

## License

Contributions are licensed under Apache-2.0. Identify provenance and licenses for third-party material.
