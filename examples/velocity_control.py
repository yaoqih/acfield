#!/usr/bin/env python3
"""Bounded velocity-interface example. Not a formation or navigation policy."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from acfield import ACFieldError, Client, Velocity


def run(args):
    output = getattr(args, "output", None)
    if output:
        output.mkdir(parents=True, exist_ok=True)
        if (output / "experiment.json").exists():
            raise ValueError("Choose a new output directory for each experiment")
    with Client(args.url) as client:
        health, initial = client.health(), client.state()
        manifest = {
            "schema_version": 1, "run_id": health.run_id, "session": initial.session,
            "mode": initial.mode, "robots": args.robots,
            "requested": {"v": args.v, "omega": args.omega, "duration_s": args.duration, "ttl_ms": 300},
            "start_time": initial.timestamp, "end_time": None, "result": "aborted",
            "initial": {ident: initial.robot(ident).model_dump() for ident in args.robots},
        }
        try:
            with client.control(*args.robots, allow_hardware=args.hardware) as control:
                print(f'Controlling {", ".join(control.robots)} for {args.duration:g} s')
                end = time.monotonic() + args.duration
                while time.monotonic() < end:
                    tick = time.monotonic()
                    state = control.state()
                    # Replace these velocities with a policy using the observed state.
                    actions = {ident: Velocity(v=args.v, omega=args.omega) for ident in control.robots}
                    control.commands(actions)
                    time.sleep(max(0, min(.1 - (time.monotonic() - tick), end - time.monotonic())))
            final, final_health = client.state(), client.health()
            manifest.update(end_time=final.timestamp,
                            final={ident: final.robot(ident).model_dump() for ident in args.robots},
                            recording_dropped=final_health.recording_dropped,
                            recording_error=final_health.recording_error)
            if final.session != initial.session or final_health.run_id != health.run_id:
                raise ValueError("Server session changed during the experiment")
            if final_health.recording_dropped or final_health.recording_error:
                raise ValueError("Server recording is incomplete; inspect /api/health")
            manifest["result"] = "completed"
        except BaseException as exc:
            manifest["error"] = str(exc) or type(exc).__name__
            raise
        finally:
            if output:
                manifest.update(platform_commit=None, worktree_dirty=None)
                try:
                    root = Path(__file__).resolve().parents[1]
                    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                              capture_output=True, text=True)
                    changes = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                             capture_output=True, text=True)
                    manifest["platform_commit"] = revision.stdout.strip() if revision.returncode == 0 else None
                    manifest["worktree_dirty"] = bool(changes.stdout) if changes.returncode == 0 else None
                except OSError:
                    pass
                (output / "experiment.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                       encoding="utf-8")
                print(f"Experiment {manifest['result']}; server run {health.run_id}")
                print(f"Saved {output / 'experiment.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--robots', nargs='+', default=['car-01'])
    parser.add_argument('--duration', type=float, default=2.)
    parser.add_argument('--v', type=float, default=.05)
    parser.add_argument('--omega', type=float, default=0.)
    parser.add_argument('--hardware', action='store_true', help='Explicitly permit a calibrated hardware-mode server')
    parser.add_argument('--output', type=Path, help='Save experiment.json in a new experiment directory')
    args = parser.parse_args()
    if not math.isfinite(args.duration) or not 0 < args.duration <= 30:
        parser.error('--duration must be finite and in (0, 30] seconds')
    if not math.isfinite(args.v) or abs(args.v) > .1:
        parser.error('--v must be finite and within +/-0.1 m/s for this example')
    if not math.isfinite(args.omega) or abs(args.omega) > .3:
        parser.error('--omega must be finite and within +/-0.3 rad/s for this example')
    if len(args.robots) != len(set(args.robots)):
        parser.error('Robot IDs must be unique')
    try:
        run(args)
    except KeyboardInterrupt:
        print('Interrupted; requested disarm of owned robots.')
        return 130
    except (ACFieldError, ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
