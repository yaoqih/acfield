# Coordinates and Geometry

World coordinates locate a robot in the arena. Body coordinates locate its tag and outline relative to the axle. Configuration lengths use metres.

## Frames {#frames}

```text
World frame (top view)              Body frame (top view)
Y                                  +x nose
^  (0,H) ----------- (W,H)            ^ tag centre T
|          theta CCW                | offset vector
|                             +y <-- O
+- (0,0) ----------- (W,0) -> X        O = drive-axle midpoint
```

At `theta=0` the nose points along world +X. At `theta=pi/2` it points along world +Y. Positive `omega` turns the nose counterclockwise.

The server arena is `[0, arena_width] x [0, arena_height]`. Vision supports polygons; server configuration synchronization writes this rectangle into the vision boundary. Choose the origin and axes first, then measure fixed tags in that same frame. Fixed tag centres may lie inside the arena edge; enter their measured coordinates.

## Offsets {#offsets}

| Server field | Definition |
| --- | --- |
| `tag_offset_x/y` | Body-frame vector from axle midpoint to tag centre, forward +x and left +y |
| `heading_offset` | Correction added to vision heading, radians. Vision's separate `heading_offset_deg` uses degrees; server robot-tag synchronization sets the vision correction to zero |
| `length/width` | Front-to-back / left-to-right body rectangle, including wheels and protrusions |
| `body_offset_x/y` | Body-frame vector from axle midpoint to that rectangle's centre |
| `tag_size` / `tag_height` | Black-square side / height above the floor at tag centre; retain the white border separately |

```text
theta = visual_heading + heading_offset
x = tag_x - cos(theta) * tag_offset_x + sin(theta) * tag_offset_y
y = tag_y - sin(theta) * tag_offset_x - cos(theta) * tag_offset_y
```

The implementation wraps corrected heading to `[-π,π]`. Apply each mounting-angle correction once at the chosen layer.

### A 30.5 mm example {#worked-example}

For a tag 30.5 mm ahead of the axle, use `tag_offset_x=0.0305`, `tag_offset_y=0` and `heading_offset=0`.

| Nose direction | Observed tag centre (m) | Server axle midpoint (m) |
| --- | --- | --- |
| +X, theta=0 | `(1.0305, 1.0000)` | `(1.0000, 1.0000)` |
| +Y, theta=pi/2 | `(1.0000, 1.0305)` | `(1.0000, 1.0000)` |

The 30.5 mm value comes from the compact 95 mm candidate's nominal layout. Measure after assembly. Set `body_offset_x` separately if the body rectangle's centre is also forward of the axle.

## Complete server configuration {#configuration-example}

This example explains the fields. Tag dimensions and offsets follow the compact candidate, with low example speed limits. Replace them with your measurements before hardware use. Saving stops robots and creates a new session.

```json
{
  "vision_url": "http://127.0.0.1:8765",
  "arena_width": 3.0,
  "arena_height": 3.0,
  "robots": [{
    "id": "car-01", "name": "Robot 1", "tag_id": 10, "color": "#28786b",
    "tag_size": 0.072, "tag_height": 0.059,
    "length": 0.20, "width": 0.16,
    "body_offset_x": 0.0, "body_offset_y": 0.0,
    "tag_offset_x": 0.0305, "tag_offset_y": 0.0, "heading_offset": 0.0,
    "max_v": 0.10, "max_omega": 0.30
  }]
}
```

Keep the axle midpoint fixed and rotate the robot by hand. Corrected position should stay within measurement error. A clear circle suggests checking offset length, sign and angle units. See the [measurement record](../hardware/bringup#keep-a-minimal-measurement-record).
