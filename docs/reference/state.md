# 状态数据字典

算法读取 `GET /api/state`。WebSocket 快照使用相同字段，并增加 `server_time_ms`。

**先看有效标记，再用数值。** 定位过期后 `x/y/theta` 会保留上次结果；`visible=false` 时应等待新定位。设备离线后，编码器和轮速反馈会变为 `null`。

电压、电量、版本和设备状态等字段可能保留最后值，使用它们时也要检查 `online` 和 `heartbeat_age_ms`。

## 快照与健康 {#snapshot-and-health}

| 字段 | 含义与使用方式 |
| --- | --- |
| `mode` | `demo` 为主控模拟器，`hardware` 为真实设备链路 |
| `session` | 主控控制会话；切模式、保存配置或重启会改变。改变后重新读取配置并建立控制会话 |
| `timestamp` | 主控统一时间，Unix 秒；表示组装快照的时刻 |
| `estop` / `system_fault` | 全局停止 / 后台任务故障。后者无故障为 `null` |
| `allow_unlocalized_control` | 是否跳过定位与位置保护。算法仍需自行判断观测有效性 |
| `arena.width/height` | 场地 X/Y 范围，米，原点为 `(0,0)` |
| `clock` | 主控时间来源、NTP 状态和待校正量；字段见 `GET /api/time` |
| `camera` | `connected` 表示已获得可用的已标定实时帧，`available` 表示相机帧仍较新，`fps` 为报告帧率，`reason` 为当前说明；部分等待状态省略 `available` |
| `events` | 有界的最近事件列表，元素为 `time`（Unix 秒）和 `message`；完整记录查看 JSONL |
| `robots` | 按 `config.id` 查询车辆，顺序不作为身份依据 |

`GET /api/health` 的 `status` 为 `ok` 或 `degraded`，HTTP 状态分别为 200 或 503。`ready` 表示所有配置车辆符合当前主控前提。`run_id` 定位日志目录，`recording_dropped/error` 检查记录完整性。UDP 计数见[接口参考](./api#endpoints)。

`clock` 包含 `source`（`local` / `ntp`）、`ntp_at`（最近 NTP 成功的 Unix 秒）、`ntp_error`（最近错误或 `null`）、`pending_correction_ms`（尚待缓慢校正的毫秒数）。相机 `connected` 以小于 200 ms 的已标定帧为前提，`available` 允许小于 1 s 的实时相机帧；逐车有效性仍以 `visible` 为准。

## 每台车 {#robot-fields}

| 字段 | 来源、单位与有效条件 |
| --- | --- |
| `config` | 保存的身份、尺寸、偏移与限速；字段见[坐标与配置](./coordinates) |
| `online` / `heartbeat_age_ms` | 设备遥测是否在心跳期限内 / 距最近遥测的毫秒数；从未收到为 `null` |
| `visible` / `pose_age_ms` | 定位是否在有效期限内 / 最近定位的数据龄；未定位或主动失效时年龄为 `null` |
| `x/y/theta` | 轮轴中点的世界坐标，米 / 米 / 弧度，航向逆时针为正。`visible=false` 时可能保留旧值 |
| `bound` / `armed` / `arm_pending` | 停车绑定完成 / 已确认控制准备 / 正在等待 arm 确认 |
| `control_owner` | 当前控制 ID，空闲为 `null` |
| `target_v/target_omega` | 主控当前目标，m/s、rad/s，包含主控限幅；诊断固件的 `target_v` 使用 PWM 传输映射 |
| `effective_max_v` / `effective_max_omega` | 当前有效目标上限；设备限制与车辆配置共同决定 |
| `measured_v` / `measured_omega` | 设备由编码器估算的车速与角速度，m/s、rad/s；在线且设备提供时有效。demo 为模拟反馈 |
| `wheel_left` / `wheel_right` | 设备估算的左右轮地面速度，m/s，前进为正；离线或缺测为 `null` |
| `encoder_left` / `encoder_right` | 设备累计原始计数，未应用 `encoderSign`；重启会重新计数，离线或缺测为 `null` |
| `estimated_v` | 主控从连续位置计算的纵向速度，经平滑，m/s；至少两次相邻有效定位后可用 |
| `acceleration` | 上述平滑视觉速度的差分，m/s²；定位无效或样本不足为 `null` |
| `imu` | 设备传感器样本，见下节；离线、旧固件或传感器不可用时为 `null` |
| `voltage_v` / `battery` | 电压 V / 电量估计 %；未知为 `null`。demo 电量为显示用模拟值 |
| `firmware` / `device_state` | 设备版本 / `unbound`、`disarmed`、`armed`、`fault`；demo 可能为 `null` |
| `seq` / `ack_seq` | 主控最近命令序号 / 设备确认序号；初始 `ack_seq=-1` |
| `command_status` | `idle` 初始、`sent` 已发送、`confirmed` 已确认、`expired` 已超期；描述主控跟踪的命令状态 |
| `applied_seq` | 设备最近已处理的控制更新序号；与 `ack_seq` 分别观察，缺失为 `null` |
| `sampled_at_ms` | 设备组装遥测时的统一 Unix 毫秒；先检查校时状态 |
| `clock_synced` / `clock_uncertainty_ms` | 设备是否可接受定时运动 / 估计校时误差，毫秒；未知误差为 `null` |
| `fault` / `warning` | 锁存故障 / 提示性警告，无则 `null`；代码见[故障表](../guide/troubleshooting#fault-codes) |
| `reason` | 主控当前控制或等待说明 |
| `stop_reason` / `last_stop_reason` | 设备当前停机说明 / 主控保留的最近停车原因，缺失为 `null` |
| `motion_echo_rejections` | 设备本次开机因遥测回显过期或未知而拒收运动命令的次数，旧固件为 `null` |
| `encoder_diagnostic` | 对已识别诊断固件返回 `max_pwm` 和 `pwm_per_mps`，普通固件为 `null` |
| `diagnostic_running` / `diagnostic_remaining_ms` | 主控是否维持诊断输出 / 剩余毫秒；未运行时后者为 `null` |
| `corners` / `trail` | 当前车体矩形四角 / 有界历史 XY 点列，世界米；均可能包含过期位置，使用前检查 `visible` |

### IMU {#imu-fields}

| 字段 | 含义 |
| --- | --- |
| `sampled_mono_us` | 读取完成时的设备单调微秒，不能直接与主控时间相减 |
| `sensor_ticks` | 芯片原始 24 位时间戳，会回绕 |
| `age_ms` | 设备发送遥测时该样本的年龄，未包含后续网络等待 |
| `saturated` | 是否达到传感器量程边界 |
| `accel_m_s2` | 芯片 XYZ 加速度，m/s²，包含重力 |
| `gyro_rad_s` | 芯片 XYZ 角速度，rad/s，包含零偏 |

IMU 轴向使用芯片坐标系。用于车体运动分析前，先完成安装轴向与零偏标定。`acceleration` 使用视觉差分，两者的采样、坐标系和滤波过程不同。

## 正常与过期 {#fresh-and-stale}

下面是单车字段节选。完整的序列化样例可下载[新鲜状态](/examples/state-fresh.json)与[过期状态](/examples/state-stale.json)，由状态实现生成，作为接口样例使用。

```json
{"online": true, "visible": true, "x": 0.84, "y": 0.84, "theta": 0.0, "pose_age_ms": 25, "measured_v": 0.05}
```

```json
{"online": false, "visible": false, "x": 0.84, "y": 0.84, "theta": 0.0, "pose_age_ms": 4000, "measured_v": null}
```

<!-- docs-test: state-reader -->
```python
from acfield import Client

with Client("http://127.0.0.1:8000") as client:
    robot = client.state().robot("car-01")
    if robot.online and robot.visible and robot.pose_age_ms is not None:
        print(robot.x, robot.y, robot.theta, robot.pose_age_ms)
    else:
        print("Waiting for fresh state")
```

## 时间怎么比较 {#time-bases}

| 时间 | 用法 |
| --- | --- |
| `timestamp`、日志 `time` | 同一主控的统一 Unix 秒，可选取实验时间段 |
| `server_time_ms`、`sampled_at_ms` | 统一 Unix 毫秒，设备值需要先确认同步及误差 |
| 日志 `monotonic`、定位事件 `at` | 主控进程使用的单调秒，适合计算间隔 |
| IMU `sampled_mono_us` | 设备单调微秒，只能在同设备、同次开机内直接比较 |

HTTP 响应时间还包含网络等待。评估采样到执行延迟时，记录时钟基准、同步误差与配对方法，详见[协议时序](./protocol#clock-synchronization-and-scheduling)。
