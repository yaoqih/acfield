# HTTP 与 WebSocket

主控通常位于 `http://127.0.0.1:8000`，运行时 OpenAPI 在 `/docs`。视觉服务通常位于 `http://127.0.0.1:8765`，是另一套接口；两者的 `/api/state` 内容不同。

## 主控接口清单 {#endpoints}

| 方法与路径 | 用途 |
| --- | --- |
| `GET /api/health` | 模式、关键任务、就绪与记录健康 |
| `GET /api/state` | 当前场地、车辆、相机与事件快照 |
| `GET /api/time` | `server_time_ms`、时钟来源、NTP 状态与待校正量 |
| `GET /api/config` | 当前持久配置 |
| `PUT /api/config` | 校验并保存；要求全部车辆锁定 |
| `PUT /api/mode` | `{"mode":"demo"}` 或 `hardware`；切换后保持全局停止 |
| `GET /api/vision/config?url=...` | 读取视觉服务状态与相机配置 |
| `POST /api/vision/cameras` | 扫描视觉服务主机上的相机 ID 0–5 |
| `POST /api/vision/operations` | 执行 `calibrate`、`load_world`、`reset_world`；全部车辆保持锁定 |
| `POST /api/robots/{id}/arm` | `{"enabled":true}` 解锁；`false` 锁定 |
| `POST /api/robots/{id}/release` | 控制 ID 仍匹配时停车锁定，返回 `released` |
| `POST /api/robots/{id}/command` | 单车速度命令 |
| `POST /api/commands` | 统一校验一批多车速度 |
| `POST /api/stop` | 全局停车并锁定 |
| `POST /api/reset-stop` | 释放全局停止，不解锁车辆 |
| `GET /api/camera/stream` | 转发配置的视觉 MJPEG |
| `WS /ws` | 约每 25 ms 最新状态、时钟同步与有序单车控制 |

## 动作格式与限制 {#action-format-and-limits}

```json
{
  "car-01": {"v": 0.05, "omega": 0.0, "ttl_ms": 300},
  "car-02": {"v": 0.05, "omega": 0.0, "ttl_ms": 300}
}
```

上例用于 `/api/commands`。单车端点接收内部速度对象。`v` 单位 m/s、schema 范围 −1 到 1，`omega` 单位 rad/s、范围 −6 到 6；实际取车辆配置与设备限制的较小值。TTL 为 100–500 ms。Schema 上限不是推荐实车速度。

速度对象可带 `execute_at_ms`（主控统一时间，Unix 毫秒）。非零动作的显式执行时刻须在主控当前时间后 15–150 ms；真实模式还要求车端时钟已同步。省略时，已同步设备默认预留 60 ms；未同步设备走即时兼容路径。零速不等待排程并清空未来运动。详见[设备时序](./protocol#clock-synchronization-and-scheduling)。

HTTP 解锁和非零动作必须带同一 `X-Control-ID`。零速度可请求停车，但不会解除锁定或全局停止。`release` 也必须带控制 ID：服务端原子检查控制源并停车锁定；不匹配或已释放返回 `{"released":false}`，不会影响新控制源。显式锁定与全局停止仍可停止其他控制源。Python 程序优先使用 [SDK](../guide/python-sdk) 的控制会话。

## WebSocket 消息 {#websocket-messages}

连接 `/ws` 后会收到与 `/api/state` 类似的最新快照，额外含 `server_time_ms`；快照不带消息 `type`，不要将其当作控制回执。同步请求为 `{"type":"time_sync","t1":客户端采样时间}`，响应回显 `t1`，并包含主控接收 `t2` 与发送 `t3`（毫秒）。客户端在接收时取 `t4` 形成四时间戳样本。

先通过 HTTP 解锁，再发送单车控制：

```json
{
  "type": "control",
  "seq": 1,
  "robot_id": "car-01",
  "owner": "my-controller",
  "command": {"v": 0.05, "omega": 0.0, "ttl_ms": 300}
}
```

`seq` 是连接内严格递增的整数；`owner` 长度 1–64，连接内不得更换，并与 HTTP 解锁 ID 一致。成功返回 `{"type":"control_ack","seq":1,"packet":{...}}`，业务拒绝返回 `control_error`、原 `seq` 与 `message`。非法序号或控制源会关闭连接；断开时按控制源条件释放其车辆。

`control_ack` 只表示主控接受动作，不是车端 ACK。网页每 25 ms 发送最新摇杆目标，错过周期跳过补发；真实模式等待浏览器/车端校时后，以采样时刻 +100 ms 排程。通道断开或拥塞时，页面通过 HTTP 备用路径停车锁定，恢复后重新解锁。

## 响应与状态 {#responses-and-state}

非法 HTTP 输入返回 422，车辆不存在返回 404，控制权、定位、保护或解锁条件不满足通常返回 409。联合校验失败不会下发本批新的部分运动动作，并锁定本批属于该控制源的车辆。

`armed` 在真实模式仅在设备确认后成立；`ack_seq` 表示协议接受，`applied_seq` 表示车端控制更新已处理，均不证明物理运动。检查轮速、编码器与视觉反馈。

`ready` 针对全部配置车辆，主控支持 1–16 条车辆记录，提供四个参考固件环境。`allow_unlocalized_control=true` 会跳过定位新鲜度、边界与车距保护；绑定、心跳、故障、解锁与 TTL 仍生效。运行初值见[配置](../guide/configuration)。

真实模式 `PUT /api/config` 可附带 `vision` 档案。主控先锁车，再让视觉服务应用，成功后才保存主控配置；失败时保持全局停止。

## 状态数据 {#state-data}

身份在 `robots[].config.id`，位置为 `x/y/theta`。同时检查在线、定位、解锁、故障、命令确认、轮速、电压和停车原因；未知值 `null` 不等于零。每车还有 `clock_synced`、`clock_uncertainty_ms`、`sampled_at_ms`、`applied_seq`。快照 `timestamp` 单位秒，WebSocket `server_time_ms` 和遥测采样时间单位毫秒。

HTTP 与 WebSocket 提供最新快照，没有逐条历史送达保证。页面“服务器推送”仅表示距本页面上次收到快照的单调时间，不是遥测龄或端到端延迟。实验使用日志并补充观测/动作关联。

## 独立视觉接口 {#vision-service-endpoints}

以下路径属于视觉服务（默认 8765），不在主控 `/api` 下：

| 方法与路径 | 用途 |
| --- | --- |
| `GET /api/state`、`GET /api/config` | 检测快照；配置与状态 |
| `POST /api/config` | 校验、应用并保存完整相机档案，等待采集线程确认 |
| `POST /api/cameras` | 扫描视觉主机相机 |
| `POST /api/operations` | `{"action":"calibrate"}`、`load_world`、`reset_world` |
| `POST /api/control` | 排队输入源、检测、记录或清轨迹操作；202 只表示入队 |
| `GET/POST /api/preview` | `{"width":0,"fps":30}`；只影响预览，当前进程有效 |
| `POST /api/calibration` | ChArUco `capture`、`solve`、`reset`；板参数见[标定指南](../guide/localization#charuco-intrinsics) |
| `POST /api/calibration/apply` | 保存当前采样求解内参或实测场地坐标，清除旧外参 |
| `GET /stream.mjpg`、`GET /api/snapshot.jpg` | MJPEG 与当前截图 |
| `GET /api/export.json`、`GET /api/export.csv` | 导出当前状态/标签数据 |
| `GET /calibration`、`GET /calibration/board.pdf` | 标定页面与默认 A4 板 |

视觉服务没有 `/api/health`。写操作限制同源页面；直接修改配置前锁定全部车辆，完成后让主控重新读取配置。
