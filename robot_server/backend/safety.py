"""Conservative swept circles for manual control, not a path planner."""
import math

HORIZON = 1.0  # pose age + telemetry freshness + max 500ms TTL + scheduling allowance
MARGIN = .04
DECELERATION = .30  # must be verified against measured stopping distance


def radius(r):
    c = r.config
    return math.hypot(c.length/2 + abs(c.body_offset_x), c.width/2 + abs(c.body_offset_y))


def position(r, v, omega, t):
    theta = r.theta
    if abs(omega) < 1e-6:
        return r.x + v*math.cos(theta)*t, r.y + v*math.sin(theta)*t
    return (r.x + v/omega*(math.sin(theta+omega*t)-math.sin(theta)),
            r.y - v/omega*(math.cos(theta+omega*t)-math.cos(theta)))


def check(fleet, r, v, omega, now, targets=None):
    """Sample exact differential-drive arcs, inflating for between-sample travel."""
    padding = radius(r) + MARGIN + v*v/(2*DECELERATION)
    step = HORIZON / 12
    padding += abs(v)*step
    for i in range(13):
        t = i*step
        x, y = position(r, v, omega, t)
        if not (padding <= x <= fleet.settings.arena_width-padding and
                padding <= y <= fleet.settings.arena_height-padding):
            return "场地边界保护"
        for other in fleet.robots.values():
            if other is r or (other.pose_at == 0 and other.boot_id is None):
                continue
            if not other.pose_at or now-other.pose_at > .2:
                return "其他小车定位失效，等待确认场地占用"
            ov, ow = (targets or {}).get(other.config.id, (other.target_v, other.target_omega))
            ox, oy = position(other, ov, ow, t)
            distance = padding + radius(other) + ov*ov/(2*DECELERATION) + abs(ov)*step
            if math.hypot(x-ox, y-oy) <= distance:
                return "车间距离保护"
    return None
