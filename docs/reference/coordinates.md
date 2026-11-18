# 坐标与几何配置

世界坐标描述车在场地哪里，车体坐标描述标签和外廓装在车的哪里。配置中的长度均用米。

## 两个坐标系 {#frames}

```text
世界坐标（俯视）                  车体坐标（俯视）
Y                               +x 车头
↑  (0,H) ───────── (W,H)           ↑ 标签中心 T
│         θ ↺                      │ 偏移向量
│                          +y ←─── O
└─ (0,0) ───────── (W,0) → X        O 为驱动轴中点，+y 为车体左侧
```

`theta=0` 时车头沿世界 +X，`theta=π/2` 时沿世界 +Y。正 `omega` 让车头逆时针转动。

主控场地固定为 `[0, arena_width] × [0, arena_height]`。视觉服务可以描述多边形；主控同步配置时会将视觉边界写成这个矩形。先选好原点和轴向，再用同一坐标系实测固定标签，保持它们的世界坐标一致。固定标签中心可以位于边界内侧，按实测值填写。

## 偏移怎么填 {#offsets}

| 主控字段 | 定义 |
| --- | --- |
| `tag_offset_x/y` | 从轮轴中点到标签中心的车体系向量；前方为 +x，左侧为 +y |
| `heading_offset` | 加到视觉航向上的修正，弧度。视觉标签配置另有 `heading_offset_deg`，单位为度；主控同步小车标签时将视觉修正置零 |
| `length/width` | 矩形车体包络的前后长度 / 左右宽度，包含轮和突出件 |
| `body_offset_x/y` | 从轮轴中点到上述矩形中心的车体系向量 |
| `tag_size` / `tag_height` | 标签黑框边长 / 地面到标签中心高度，白边单独保留 |

```text
θ = visual_heading + heading_offset
x = tag_x − cos(θ) × tag_offset_x + sin(θ) × tag_offset_y
y = tag_y − sin(θ) × tag_offset_x − cos(θ) × tag_offset_y
```

实现会将修正后的航向归一到 `[-π,π]`。同一安装角补偿只在选定的一端配置。

### 30.5 mm 的例子 {#worked-example}

标签在轮轴前方 30.5 mm，填 `tag_offset_x=0.0305`、`tag_offset_y=0`、`heading_offset=0`。

| 车头 | 视觉标签中心（m） | 主控轮轴中点（m） |
| --- | --- | --- |
| +X，θ=0 | `(1.0305, 1.0000)` | `(1.0000, 1.0000)` |
| +Y，θ=π/2 | `(1.0000, 1.0305)` | `(1.0000, 1.0000)` |

30.5 mm 来自 95 mm 候选的名义布局，装车后重新测量。若车体矩形中心也前移，另填 `body_offset_x`。

## 一份完整主控配置 {#configuration-example}

下面用于解释字段。`tag_size`、高度和偏移按 95 mm 候选填写，速度采用较低的示例值，提交实车前换成自己的测量结果。保存会停车并重建会话。

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

保持车轴中点不动，手动转车一圈。校正后的位置应落在测量误差范围内；若画出明显圆圈，优先检查偏移长度、方向和角度单位。更多测量步骤见[验收记录](../hardware/bringup#keep-a-minimal-measurement-record)。
