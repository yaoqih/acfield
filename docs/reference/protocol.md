# 设备协议与时序

当前设备使用 UDP JSON 协议 `version=1` 的显式 arm 握手修订。网页首次新动作由主控自动完成该握手，无需手动解锁；停车或重连后旧动作不会恢复，新输入可直接准备控制。服务端与本仓固件应一起使用；历史 v1 报文不一定具备当前必需字段，不能只依据数字 1 判断兼容。

## 身份与会话 {#identity-and-sessions}

`robot_id` 是持久车号，`boot_id` 每次设备启动改变，遥测与命令各有递增序号。主控用 `session` 标识控制会话，设备只接受符合当前启动、会话及序号规则的指令。

设备约以 40 Hz 向主控 UDP 9999 发送遥测，主控回发来源端点。默认四车身份为 `car-01` 到 `car-04`，不能把四块板全部烧成同一个身份。

## 状态转换 {#state-transitions}

```text
启动 / 断联
    ↓
unbound ── 新鲜遥测回显 + stop ──► disarmed
                                     │
                               显式 arm + 确认
                                     ↓
                                   armed
                                     │
                       stop / TTL / 链路或设备故障
                                     ↓
                              disarmed / fault
```

故障锁存后需排除原因并重启设备。重连只恢复通信条件，不恢复运动。

## 命令示例 {#example-command}

```json
{
  "version": 1,
  "type": "command",
  "action": "drive",
  "session": "server-session",
  "robot_id": "car-01",
  "boot_id": "per-boot-id",
  "telemetry_seq": 42,
  "seq": 8,
  "v": 0.05,
  "omega": 0.0,
  "ttl_ms": 300,
  "stop": false
}
```

- `stop`：双零速度、`stop=true`，停车并取消解锁，也用于绑定新会话。
- `arm`：双零速度、`stop=true`；已绑定、无故障且回显新鲜才可显式解锁。
- `drive`：已解锁后执行速度；运动必须回显当前启动最近发送的遥测。双零且 `stop=true` 只停车，不重新解锁。

绑定新会话须回显 200 ms 内且晚于上次绑定界限的遥测；旧会话历史报文不能重新绑定。普通固件运动回显窗口为 200 ms；`0.2.4/0.2.5-encoder-diagnostic` 仅将运动窗口放宽为 1500 ms，以容忍遥测暂时延迟。解锁仍需 200 ms 内回显。重复命令不会刷新运动 TTL。

## 遥测 {#telemetry}

包含身份、启动 ID、序号、`device_state`、固件版本、`ack_session/ack_seq`、`applied_seq`、`sampled_at_ms`、`clock_synced`、`clock_uncertainty_ms`、电压、编码计数、左右轮速、速度限制、故障与停车原因。`ack_seq` 是协议接受，`applied_seq` 是控制更新已处理，都不代表物理运动已发生。`sampled_at_ms` 是遥测构建时刻，轮速来自最近控制周期；未知测量填 `null` 或省略。

`measured_v`、`measured_omega`、`wheel_left/right` 接受所有有限数值；它们是原始反馈，编码器受干扰时可以超出物理速度范围，不能因此丢弃整包心跳、ACK 与原始计数。NaN/Infinity 仍拒收。测速范围不改变运动命令及设备限制的校验。

可选 `motion_echo_rejections` 为运动指令因遥测回显过期或未知而被拒收的开机累计次数。它只记录协议运动新鲜度检查的拒收，不代表所有丢包或拒收。

协议解析与状态机源文件位于 `esp32_software/firmware/include/command_wire.h` 和 `protocol.h`。跨端测试会编译实际解析器，让服务端生成的报文进入真实固件逻辑。

可选 `warning` 字段只报告警告，不改变解锁或运动状态。固件电压传感器读取失败或读数超出 7–16 V 时发送 `warning="battery_sensor"`、`voltage_v=null`，有效读数恢复后自动清除警告。异常读数中断欠压计时；有效电压连续低于 10.5 V 达 1 s 仍触发锁存故障 `fault="battery_low"`。完整代码、触发条件与恢复方式见[故障与警告表](../guide/troubleshooting#fault-codes)。

## 时钟同步与排程 {#clock-synchronization-and-scheduling}

主控启动时将本机 UTC 映射到单调时钟，默认每 300 s 尝试 NTP，以最多 1 ms/s 渐进修正；不会修改系统时间。离线仍能运行，但统一时间不等于准确 UTC。`GET /api/time` 可查看来源和待校正量。TTL、心跳与失联检查使用单调时间。

ESP32 通过 UDP、浏览器通过 WebSocket 每秒发起四时间戳 `time_sync`，以低 RTT 样本估计偏移。车端超过 15 s 未同步或估计误差超过 20 ms 时拒绝定时运动；误差估计依赖网络路径与漂移假设，不是精度保证。

非零 `drive` 可携带 `execute_at_ms`（主控统一 Unix 毫秒）。网页不指定执行时间，由主控根据最新车端校时状态选择：已同步时添加 +60 ms，未同步时即时发送。主控只接受显式执行时刻在当前时间后 15–150 ms 的非零动作。即时路径不保证固定延迟；demo 立即执行，不能证明排程性能。

编码器诊断页对支持的诊断固件使用 HTTP/WS 命令选项 `immediate: true`，主控不会补上执行时间。车端继续接受原有未指定时间的指令，按本地单调时钟检查 TTL；固件线协议无需新增字段。`hold: true` 仅允许通过 WebSocket 启动，由主控维持续发，连接断开或停车后清除。该选项仅用于双轮诊断 PWM，详见[主控 API](./api)。

设备将执行时刻转换为单调期限并放入有界队列，由 10 ms 控制任务处理。到达时执行时刻已过、等待超过 150 ms 或不小于 TTL 的包会被拒绝；队列已收包超过执行期限 20 ms 则丢弃，队列满丢弃新包。TTL 从接收开始计时，包含排程等待；重复包不续期。接受的零速命令清空未来运动，`stop` 还会取消解锁；故障与失联不等待排程。

详细设计与验收方法见 [TIMING.md](https://github.com/yaoqih/acfield/blob/main/robot_server/TIMING.md)。应配套更新主控、前端与固件，不能只凭 `version=1` 判断时序兼容。

## 当前时序配置 {#current-timing-configuration}

| 环节 | 配置值 | 含义 |
| --- | --- | --- |
| 车端运动任务 | 100 Hz | 检查 TTL 与更新轮速控制 |
| 车端遥测 | 40 Hz | 设备状态与反馈 |
| 主控循环与状态推送 | 40 Hz | 周期目标 25 ms，最新快照 |
| 网页摇杆目标 | 40 Hz | 有序 WebSocket，跳过错过的周期 |
| Python 速度示例 | 约 10 Hz | 示例频率；算法需结合推理与链路实测 |
| 心跳期限 | 普通与诊断均为 3 s | 遥测返回过期锁定 |
| 持续诊断时长 | 120 s | 主控计时，调 PWM 不延长 |
| 定位期限 | 200 ms | 过期失效 |
| 默认动作期限 | 300 ms | 可配 100–500 ms |
| 绑定/解锁重试 | 150 ms | 维持相应序号重试 |

这些是软件门限和调度目标，不是已测量的无线延迟或物理停止时间。测量端到端延迟时应明确时钟基准，不能直接相减不同设备未同步的时间戳。
