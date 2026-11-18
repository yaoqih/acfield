# Versions, compatibility and upgrades

**Pin code, firmware and calibration together for each experiment.** Page footers show the build commit. `modified` indicates uncommitted changes at build time. The deployed site may be ahead of your checkout, so compare against your local commit.

## Current combinations {#compatibility}

| Layer | Current convention | Upgrade checks |
| --- | --- | --- |
| Server / Python SDK / console | Same platform commit, evolving HTTP and WebSocket interfaces | First experiment, state fields, ownership and cleanup |
| Normal firmware | 0.2.9, protocol `v1/explicit-arm`, encoder regulation by default | Version, counts, directions, device limits, PI |
| Diagnostic firmware | 0.2.5-encoder-diagnostic, dedicated PWM mapping | Restore normal firmware after [diagnosis](./troubleshooting#encoder-diagnostics) |
| Vision profile | Specific camera, resolution, focus, tags and arena | Verify saved extrinsics before enabling them |
| Hardware | Record V11, compact candidates and purchased parts separately | [Hardware compatibility](../hardware/compatibility) |

Fields can be added within one protocol version. Older servers rejected telemetry carrying `warning`, so update server and firmware together. Firmware 0.2.1 latched `battery_sensor`, which current firmware reports as a warning. The repository currently has no formal Release tags. Pin complete commits for experiments. [Changelog](https://github.com/yaoqih/acfield/blob/main/CHANGELOG.md)

## Back up {#backup}

Stop motion, then export server configuration and record the revision from the repository root.

```bash
mkdir -p output/upgrade-backup
curl --fail http://127.0.0.1:8000/api/config -o output/upgrade-backup/server-config.json
git rev-parse HEAD
git status --short
```

Record firmware environment, version and local `config.h` edits. Save runtime settings in the vision UI, then shut down server and vision before copying files.

```bash
cp robot_server/data/config.sqlite3 output/upgrade-backup/config.sqlite3
cp output/vision-settings.json output/upgrade-backup/vision-settings.json
```

These are default paths. Substitute actual `ROBOT_DB` and `--runtime-config` paths. Unsaved files may be absent. The vision runtime file includes `profile` and `saved_world`. A server configuration export alone cannot restore camera intrinsics or saved extrinsics. Archive run logs separately.

## Pin and verify {#pin-and-verify}

Preserve workspace changes before checking out the complete commit to evaluate. A separate checkout can retain the existing environment.

```bash
git fetch origin
git worktree add ../acfield-pinned <full-commit>
cd ../acfield-pinned
uv sync --frozen --python 3.12 --extra test
npm ci
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
```

Restore backups to the new checkout's actual runtime paths. Start demo, complete [your first experiment](./first-experiment), and verify complete records, stopping and ownership release. Build and flash the appropriate firmware environments and verify per-robot measurements.

Defaults apply to new configurations. SQLite retains saved limits and tag dimensions. Saving server configuration stops robots, creates a new session, and synchronizes the vision rectangle and robot tags. See [coordinates](../reference/coordinates). Recheck localization, directions, limits and stopping before physical experiments.

## Roll back {#rollback}

Stop both services, return to the previous checkout, and restore its database, vision runtime file and firmware. Reinstall from its lockfiles and rebuild, then verify versions and calibration. Report the failed revision, symptoms and minimal logs in an issue.
