"""Wall-clock interface demo with exact constant-velocity differential-drive arcs."""
import math
import time
from .safety import position, radius


class Simulator:
    def __init__(self, fleet):
        self.fleet = fleet
        self.previous = time.monotonic()
        count = len(fleet.robots)
        cols = 2 if count <= 4 else math.ceil(math.sqrt(count * fleet.settings.arena_width / fleet.settings.arena_height))
        rows = 2 if count <= 4 else math.ceil(count / cols)
        for i, r in enumerate(fleet.robots.values()):
            x = fleet.settings.arena_width * (.28 + .44*(i % 2)) if count <= 4 else fleet.settings.arena_width * (i % cols + .5) / cols
            y = fleet.settings.arena_height * (.28 + .44*((i//2) % 2)) if count <= 4 else fleet.settings.arena_height * (i // cols + .5) / rows
            fleet.pose(r, x, y, [0, math.pi/2, -math.pi/2, math.pi][i % 4], self.previous)
            r.battery = max(0, 96-i*7)

    def step(self, now):
        dt = max(0, min(.1, now-self.previous))
        self.previous = now
        for r in self.fleet.robots.values():
            r.seen_at = now
            x, y = position(r, r.target_v, r.target_omega, dt)
            theta = math.atan2(math.sin(r.theta+r.target_omega*dt), math.cos(r.theta+r.target_omega*dt))
            margin = radius(r)
            if not (margin <= x <= self.fleet.settings.arena_width-margin and
                    margin <= y <= self.fleet.settings.arena_height-margin):
                self.fleet.stop(r, "模拟场地边界 · 已锁定")
                x, y, theta = r.x, r.y, r.theta
            r.measured_v, r.measured_omega = r.target_v, r.target_omega
            self.fleet.pose(r, x, y, theta, now)
