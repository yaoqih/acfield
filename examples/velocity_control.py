#!/usr/bin/env python3
"""Bounded velocity-interface example. Not a formation or navigation policy."""
import argparse
import math
import sys
import time
import uuid

import httpx


def checked_state(client, robots, owner=None):
    response = client.get('/api/state')
    response.raise_for_status()
    state = response.json()
    if state['estop'] or state.get('system_fault'):
        raise RuntimeError('Global stop or system fault is active; inspect the console.')
    selected = {r['config']['id']: r for r in state['robots']}
    for ident in robots:
        if ident not in selected:
            raise RuntimeError(f'Unknown robot: {ident}')
        robot = selected[ident]
        if not all(robot[key] for key in ('bound', 'online', 'visible')) or robot.get('fault'):
            raise RuntimeError(f'{ident} is not ready: {robot.get("reason")}')
        if owner and (not robot['armed'] or robot['control_owner'] != owner):
            raise RuntimeError(f'{ident} lost arming or control ownership: {robot.get("reason")}')
    return state, selected


def run(args):
    owner = 'example-' + uuid.uuid4().hex[:16]
    with httpx.Client(base_url=args.url.rstrip('/'), headers={'X-Control-ID': owner}, timeout=.5) as client:
        health = client.get('/api/health')
        health.raise_for_status()
        mode = health.json()['mode']
        if mode != 'demo' and not args.hardware:
            raise RuntimeError('Hardware mode requires --hardware after calibration and bring-up.')
        checked_state(client, args.robots)
        try:
            for ident in args.robots:
                response = client.post(f'/api/robots/{ident}/arm', json={'enabled': True})
                response.raise_for_status()
            deadline = time.monotonic() + 1.5
            while True:
                _, selected = checked_state(client, args.robots)
                if all(selected[i]['armed'] and selected[i]['control_owner'] == owner for i in args.robots):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('Timed out waiting for device arming confirmation.')
                time.sleep(.05)
            print(f'{mode}: controlling {", ".join(args.robots)} for {args.duration:g} s')
            end = time.monotonic() + args.duration
            while time.monotonic() < end:
                tick = time.monotonic()
                checked_state(client, args.robots, owner)
                # Replace this constant action with a controller using the observed state.
                actions = {ident: {'v': args.v, 'omega': args.omega, 'ttl_ms': 300} for ident in args.robots}
                response = client.post('/api/commands', json=actions)
                response.raise_for_status()
                time.sleep(max(0, min(.1 - (time.monotonic() - tick), end - time.monotonic())))
        finally:
            # Do not disarm a different controller if ownership has changed.
            try:
                response = client.get('/api/state')
                response.raise_for_status()
                for robot in response.json()['robots']:
                    ident = robot['config']['id']
                    if ident in args.robots and robot['control_owner'] == owner:
                        result = client.post(f'/api/robots/{ident}/arm', json={'enabled': False})
                        result.raise_for_status()
            except httpx.HTTPError as exc:
                print(f'Cleanup request failed; inspect the console. TTL still applies: {exc}', file=sys.stderr)


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
    except (RuntimeError, httpx.HTTPError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
