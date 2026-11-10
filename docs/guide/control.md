# 接入控制算法

当前最短接入路径是：读取状态 → 逐车解锁并确认 → 提交联合速度 → 持续检查状态 → 结束时停车锁定。还没有需要学习的策略插件框架。

Python 算法推荐通过 [Python SDK](./python-sdk) 接入：`Client` 负责 HTTP 与类型解析，`client.control(...)` 负责等待解锁、检查控制权和退出释放。SDK 可独立安装到算法环境，不需要导入服务端模块。

## 一个有边界的例子 {#a-bounded-example}

先按[快速开始](./quickstart)运行演示服务，再在仓库根目录运行：

```bash
.venv/bin/python examples/velocity_control.py --duration 2

# 两车以同一批请求提交动作
.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

示例默认直行 0.05 m/s、每 100 ms 更新、TTL 300 ms，最多运行 30 s。它只负责速度接口演示，不是编队算法。它会检查模式、就绪和解锁状态，并在退出路径中请求参与车停车锁定。Ctrl+C 同样进入清理流程；进程被强制终止时则依赖服务器与设备 TTL。

默认拒绝真实模式。完成实际标定和验收后，可以显式添加 `--hardware`。例子不会自动解除全局停止，也不会接管其他控制源。

## 状态如何理解 {#understand-state}

`GET /api/state` 返回场地、小车、事件和相机状态。车辆身份位于 `robots[i].config.id`，位置为 `x/y/theta`；同时检查 `armed`、在线与定位状态。字段以运行时的 OpenAPI 和返回值为准。

`GET /api/health` 的 `ready` 表示全部配置车辆满足绑定、在线、故障等前提，定位新鲜度是否必需由 `allow_unlocalized_control` 决定；它不表示已解锁，也不表示硬件已经通过物理验收。

## 联合动作 {#joint-actions}

```http
POST /api/commands
Content-Type: application/json
X-Control-ID: my-controller

{
  "car-01": {"v": 0.05, "omega": 0, "ttl_ms": 300},
  "car-02": {"v": 0.05, "omega": 0, "ttl_ms": 300}
}
```

`v` 单位 m/s，`omega` 单位 rad/s，逆时针为正。解锁时使用相同的控制 ID，并等待各车 `armed=true`。校验失败返回 409，本批新的运动动作不会部分下发。

## 替换控制器 {#replace-the-controller}

在示例的 `run()` 循环中，用观测计算每台车的 `v/omega`，保留模式检查、状态确认、定时与退出清理。对慢推理策略，应把推理放到独立进程，并给结果绑定观测时刻和有效期限。

目标点、二维速度或轨迹需要增加明确的差速跟踪器。不要把理想平面速度直接映射成轮速，也不要通过一直续发旧动作绕过算法超时。

## 研究实验额外需要什么 {#additional-research-requirements}

任务初始化、回合与终止判据、受限观测、消息约束和指标由实验层管理。平台当前没有自动隔离各 agent 的全局状态访问。详见[研究边界](../design/research)与[记录与复现](./recording)。
