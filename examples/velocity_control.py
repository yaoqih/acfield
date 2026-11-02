#!/usr/bin/env python3
"""Bounded velocity-interface example. Not a formation or navigation policy."""
import argparse
import math
import sys
import time
from acfield import ACFieldError, Client, Velocity


def run(args):
    with Client(args.url) as client:
        with client.control(*args.robots, allow_hardware=args.hardware) as control:
            print(f'Controlling {", ".join(control.robots)} for {args.duration:g} s')
            end = time.monotonic() + args.duration
            while time.monotonic() < end:
                tick = time.monotonic()
                state = control.state()
                # Replace these velocities with a policy using the observed state.
                # state.robot(ident) exposes typed pose, readiness and feedback.
                actions = {ident: Velocity(v=args.v, omega=args.omega) for ident in control.robots}
                control.commands(actions)
                time.sleep(max(0, min(.1 - (time.monotonic() - tick), end - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--robots', nargs='+', default=['car-01'])
    parser.add_argument('--duration', type=float, default=2.)
    parser.add_argument('--v', type=float, default=.05)
    parser.add_argument('--omega', type=float, default=0.)
    parser.add_argument('--hardware', action='store_true', help='Explicitly permit a calibrated hardware-mode server')
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
    except (ACFieldError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
