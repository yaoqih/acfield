# 记录与复现

一次实验至少留下**运行条件、原始事件、分析结果**。[第一次实验](./first-experiment)给出可直接运行的采集和分析命令。

## 文件在哪里 {#what-is-recorded}

主控每次启动创建一个运行目录，默认位于 `robot_server/data/runs/<run_id>/`。修改 `ROBOT_DB` 后跟随数据库目录，也可用 `ROBOT_LOG_DIR` 单独指定根目录。`GET /api/health` 返回当前 `run_id`。

```text
runs/<run_id>/
├── config.json       启动会话、模式、配置、视觉地址、协议
└── events.jsonl      每行一个事件，持续追加
output/first-run/
├── experiment.json  示例脚本生成的单次实验清单
├── summary.json     分析结果
├── trajectories.csv
└── trajectories.png
```

一个主控运行可以包含多次实验。`config.json` 保存启动配置，后续变化查看 `configuration` 事件。日志当前没有独立 schema 版本，解析时固定平台 commit，并保留原始文件。

## 每行怎么读 {#event-schema}

```json
{"time": 1800000000.125, "monotonic": 100.125, "kind": "pose", "data": {"robot_id": "car-01", "x": 0.84, "y": 0.84, "theta": 0.0, "at": 100.12}}
```

`time` 是入队时的主控 Unix 秒，`monotonic` 是同进程的单调秒，`kind` 选择事件类型，`data` 保存对应数据。

| `kind` | `data` 主要字段与用途 |
| --- | --- |
| `startup` | `session`，启动会话 |
| `configuration` | `session`、`settings`，保存后的完整配置 |
| `mode` | `session`、`mode`，切模式后的新会话 |
| `event` | `message`，可读的运行提示 |
| `control` | `owner`、`requested`、`accepted`，成功有 `applied`，拒绝有 `reason` |
| `command` | 实际命令的 `session`、`robot_id`、`seq`、`action`、`v`、`omega`、`ttl_ms` 等，实车还含设备回显字段 |
| `telemetry` | 设备报文的 `robot_id`、`boot_id`、`ack_session`、`ack_seq`、轮速、编码器等；demo 无真实遥测 |
| `pose` | `robot_id`、`x`、`y`、`theta`、`at`；位置为轮轴中点，`at` 为主控单调秒 |
| `stop` | `robot_id`、`reason`，主控停车原因 |
| `udp_rejected` | `endpoint`、`reason`、`fields`，拒收线索 |

以下是接受与拒绝的格式示例。`applied` 表示主控采用的目标，设备确认和实际运动要继续查证。

```json
{"time": 1800000000.13, "monotonic": 100.13, "kind": "control", "data": {"owner": "example-controller", "requested": {"car-01": {"v": 0.6, "omega": 0.0, "ttl_ms": 300, "execute_at_ms": null}}, "accepted": true, "applied": {"car-01": {"v": 0.5, "omega": 0.0}}}}
```

```json
{"time": 1800000000.14, "monotonic": 100.14, "kind": "control", "data": {"owner": "example-controller", "requested": {"car-01": {"v": 0.05, "omega": 0.0, "ttl_ms": 300, "execute_at_ms": null}}, "accepted": false, "reason": "全局停止已锁定"}}
```

## 选取一次实验 {#suggested-experiment-manifest}

速度示例增加 `--output` 后，写入 `schema_version=1` 的 `experiment.json`。

| 字段 | 作用 |
| --- | --- |
| `run_id`、`session`、`mode`、`robots` | 定位日志、会话和参与车辆 |
| `start_time`、`end_time` | 首尾状态的主控 Unix 秒，用于截取日志 |
| `requested`、`initial`、`final` | 请求参数与首尾状态，提前失败时可能缺少 `final` |
| `result`、`error` | `completed` / `aborted`，失败时有原因 |
| `recording_dropped`、`recording_error` | 结束时的记录健康信息，提前失败时可能缺失 |
| `platform_commit`、`worktree_dirty` | 示例所在检出的 Git 版本和修改状态，无法读取时为 `null` |

示例与主控使用同一检出版本。分机部署时另记主控与固件 commit。实车实验再保存硬件修订、标定文件及校验值、控制器版本、任务参数、初始摆位、电量、地面和重复次数。

分析器按 `run_id` 找日志，按主控 Unix 时间截取区间，使用定位 `at` 算轨迹间隔。未完成实验和区间内的会话变更会报错。事件数量只统计参与车辆的相关事件。

## 动作、确认和运动怎么对上 {#correlate-events}

实车按命令的 `session + robot_id + seq` 关联遥测 `ack_session + ack_seq`，同时核对 `boot_id`。ACK 表示设备协议已处理，实际速度看编码器和定位。最新累计 ACK 不能证明每条中间动作都独立执行。

`command` 可能早于对应的 `control`，相邻行配对会出错。定位目前没有动作 ID；测量观测到执行延迟时，实验层还需记录观测 ID、动作 ID、采样时间、执行反馈和时钟误差。详见[时间基准](../reference/state#time-bases)。

## 检查记录完整性 {#recording-integrity}

运行前后检查 `/api/health` 的 `recording_dropped=0`、`recording_error=null`。队列容量为 2048，满队列会丢弃事件。结束后正常关闭服务，等待写入完成，再复制和分析。

`gaps_over_200ms` 统计定位空档，路径长度跳过这些区间。记录正常也可能有相机空档，两项都要检查。

## 重复性与归档 {#discuss-repeatability-at-each-layer}

demo 按主机实际时间积分恒定速度圆弧，每步最多推进 100 ms，调度与命令到达时间会影响轨迹。固定步长算法评测需由实验层保存初态、步长、种子和动作序列。

实车同时报告位置/航向误差、初始误差、重复次数和异常运行处理方法。完整物理重演还需要模型与实验定义。

## 数据与仓库 {#data-and-repositories}

小型公开 demo 数据和图可随文档提交，标明模式与版本。长视频、模型和研究数据放入 Release 或数据归档，附校验值和许可证。个人配置、SQLite 与设备凭据保留在本地。
