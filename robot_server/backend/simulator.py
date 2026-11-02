"""Deterministic demo. Moves only under user commands; no background autonomy."""
import math
import time


class Simulator:
    def __init__(self, fleet):
        self.fleet = fleet
        self.previous = time.monotonic()
        for i, r in enumerate(fleet.robots.values()):
            x = fleet.settings.arena_width * (.28 + .44*(i % 2))
            y = fleet.settings.arena_height * (.28 + .44*((i//2) % 2))
            fleet.pose(r, x, y, [0, math.pi/2, -math.pi/2, math.pi][i % 4], self.previous)
            r.battery = 96-i*7

    def step(self, now):
        dt = min(.1, now-self.previous)
        self.previous = now
        for r in self.fleet.robots.values():
            r.seen_at = now
            r.measured_v, r.measured_omega = r.target_v, r.target_omega
            theta = math.atan2(math.sin(r.theta+r.target_omega*dt), math.cos(r.theta+r.target_omega*dt))
            x = r.x + r.target_v*math.cos(theta)*dt
            y = r.y + r.target_v*math.sin(theta)*dt
            margin = math.hypot(r.config.length, r.config.width)/2
            if not (margin <= x <= self.fleet.settings.arena_width-margin and
                    margin <= y <= self.fleet.settings.arena_height-margin):
                self.fleet.stop(r, "模拟场地边界 · 已锁定")
                x, y = r.x, r.y
            self.fleet.pose(r, x, y, theta, now)
