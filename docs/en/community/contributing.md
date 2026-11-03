# Contributing and versioning

ACField welcomes Chinese and English issues, documentation corrections, reproduction reports and code. Full guidelines are in [CONTRIBUTING.md](https://github.com/yaoqih/acfield/blob/main/CONTRIBUTING.md).

## Useful contributions {#useful-contributions}

Reproducible failures, installation fixes on other systems, physical measurements, coordinate/calibration explanations and compatibility notes matter alongside code. Explain the experiment a new feature supports and how its behavior can be checked.

## Local checks {#local-checks}

```bash
# Repository root
npm ci
npm run docs:build
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build

# Backend
cd robot_server
uv sync --python 3.12 --extra test
uv run pytest -q
```

See [troubleshooting](../guide/troubleshooting) for vision, firmware and cross-component dependencies. CI requires actual-firmware parser tests to execute. Physical validation still needs measurement; a green build cannot replace it.

## Version principles {#version-principles}

Preview interfaces may change. Document compatibility changes and review both endpoints when protocols change. Pin commits until a stable release cadence exists.

Each release should record server/firmware versions, protocol revision, reference hardware, configuration/log formats and performed software/physical checks. No formal release tags have been created yet.

## Platform and paper repositories {#platform-and-paper-repositories}

The main repository maintains common infrastructure and small examples. Paper repositories maintain methods, training and frozen experiments. Documentation source stays with the platform and is built automatically. Users should not need several repositories to obtain a compatible base system.

## Maintenance continuity {#maintenance-continuity}

CODEOWNERS currently identifies the repository maintainer. A laboratory handover should assign at least two maintainers with appropriate access and module owners matching actual duties. Moving to a lab organization also requires updating release addresses, website configuration and citations.
