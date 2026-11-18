#!/usr/bin/env python3
"""Extract one experiment from a server event log and plot its trajectories."""
import argparse
import csv
import json
import math
from pathlib import Path


def analyze(folder, logs):
    manifest = json.loads((folder / "experiment.json").read_text(encoding="utf-8"))
    if manifest["result"] != "completed" or manifest["end_time"] is None:
        raise ValueError("The experiment was aborted; inspect experiment.json before analysis")
    events = logs / manifest["run_id"] / "events.jsonl"
    trajectories = {ident: [] for ident in manifest["robots"]}
    counts = {"accepted_controls": 0, "rejected_controls": 0, "command_packets": 0, "telemetry": 0}
    with events.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                if not manifest["start_time"] <= row["time"] <= manifest["end_time"]:
                    continue
                data, kind = row["data"], row["kind"]
                if kind in ("startup", "configuration", "mode") and data["session"] != manifest["session"]:
                    raise ValueError("Server session changed inside the experiment interval")
                if kind == "pose" and data["robot_id"] in trajectories:
                    values = [data[key] for key in ("at", "x", "y", "theta")]
                    if not all(type(value) in (int, float) and math.isfinite(value) for value in values):
                        raise ValueError("Pose contains non-finite or invalid values")
                    trajectories[data["robot_id"]].append(values)
                elif kind == "control" and set(data["requested"]) & set(trajectories):
                    counts["accepted_controls" if data["accepted"] else "rejected_controls"] += 1
                elif kind in ("command", "telemetry") and data["robot_id"] in trajectories:
                    counts["command_packets" if kind == "command" else "telemetry"] += 1
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"{events}:{line_number}: {exc}") from exc
    summary = {"run_id": manifest["run_id"], "mode": manifest["mode"], "events": counts, "robots": {}}
    for ident, samples in trajectories.items():
        if len(samples) < 2:
            raise ValueError(f"{ident}: at least two pose samples are required")
        distance, gaps = 0., 0
        for previous, current in zip(samples, samples[1:]):
            dt = current[0] - previous[0]
            if dt <= 0:
                raise ValueError(f"{ident}: pose times must increase")
            if dt > .2:
                gaps += 1
            else:
                distance += math.hypot(current[1] - previous[1], current[2] - previous[2])
        summary["robots"][ident] = {
            "samples": len(samples), "observed_duration_s": samples[-1][0] - samples[0][0],
            "path_length_m": distance, "gaps_over_200ms": gaps,
            "displacement_m": math.hypot(samples[-1][1] - samples[0][1], samples[-1][2] - samples[0][2]),
        }
    with (folder / "trajectories.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["robot_id", "elapsed_s", "x_m", "y_m", "theta_rad"])
        for ident, samples in trajectories.items():
            for at, x, y, theta in samples:
                writer.writerow([ident, at - samples[0][0], x, y, theta])
    (folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary, trajectories


def plot(folder, trajectories):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=(6, 4))
    for ident, samples in trajectories.items():
        xs, ys = [], []
        for index, row in enumerate(samples):
            if index and row[0] - samples[index - 1][0] > .2:
                xs.append(math.nan)
                ys.append(math.nan)
            xs.append(row[1])
            ys.append(row[2])
        line, = axes.plot(xs, ys, label=ident)
        axes.scatter(xs[0], ys[0], marker="o", s=25, color=line.get_color())
        axes.scatter(xs[-1], ys[-1], marker="x", s=35, color=line.get_color())
    axes.set(xlabel="World X (m)", ylabel="World Y (m)", title="Recorded trajectories")
    axes.set_aspect("equal", adjustable="datalim")
    axes.grid(alpha=.25)
    axes.legend()
    figure.tight_layout()
    figure.savefig(folder / "trajectories.png", dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path, help="Directory containing experiment.json")
    parser.add_argument("--logs", type=Path, default=Path("robot_server/data/runs"))
    parser.add_argument("--plot", action="store_true", help="Render trajectories.png using matplotlib")
    args = parser.parse_args()
    try:
        summary, trajectories = analyze(args.folder, args.logs)
        if args.plot:
            plot(args.folder, trajectories)
    except (OSError, ValueError, KeyError, ImportError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
