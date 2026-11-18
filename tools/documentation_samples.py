"""Generate deterministic API illustrations using the actual snapshot serializer."""
import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "robot_server"))

from backend.clock import Clock
from backend.models import default_settings
from backend.simulator import Simulator
from backend.state import Fleet


def samples():
    status = Clock().status()
    with patch.dict(os.environ, {"ROBOT_ALLOW_UNLOCALIZED_CONTROL": "0"}), \
         patch("backend.state.time.monotonic", return_value=1000.), \
         patch("backend.state.clock.now_ms", return_value=1800000000000.), \
         patch("backend.state.clock.status", return_value=status):
        fleet = Fleet(default_settings(), "demo")
        fleet.session = "documentation-example"
        simulator = Simulator(fleet)
        simulator.step(1000.)
        fresh = fleet.snapshot()
        with patch("backend.state.time.monotonic", return_value=1004.), \
             patch("backend.state.clock.now_ms", return_value=1800000004000.):
            stale = fleet.snapshot()
    return {"fresh": fresh, "stale": stale}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, state in samples().items():
        path = ROOT / f"docs/public/examples/state-{name}.json"
        expected = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                raise SystemExit(f"Outdated {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
    print("State examples match the snapshot serializer")


if __name__ == "__main__":
    main()
