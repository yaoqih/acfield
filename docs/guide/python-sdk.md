# Python SDK

SDK 把 HTTP 请求、类型解析、控制权和退出清理放进一个小型 Python 包，让算法代码专注于读取状态和产生动作。包名和导入名均为 `acfield`，源代码位于 `sdk/python/`，与服务端在同一仓库维护、分别安装。

当前为 **0.1.0 开发预览**，提供同步 HTTP 客户端与受控生命周期。它不依赖后端内部模块、前端、PlatformIO、NumPy 或训练框架。

## 安装 {#installation}

在仓库根目录、你的算法虚拟环境中执行：

```bash
python -m pip install ./sdk/python

# 修改 SDK 时使用可编辑安装
python -m pip install -e './sdk/python[test]'
```

仓库的共享环境会同时安装主控和 SDK；从根目录执行：

```bash
uv sync --python 3.12 --extra test
.venv/bin/python examples/velocity_control.py --robots car-01 car-02 --duration 2
```

也可以直接从 Git 安装：

```bash
python -m pip install 'acfield @ git+https://github.com/yaoqih/acfield.git@main#subdirectory=sdk/python'
```

复现实验时将 `main` 替换为实际验证过的完整提交 SHA。包目前没有发布到 PyPI，请使用上述本地或 Git 安装方式。

## 只读状态 {#read-only-state}

```python
from acfield import Client

with Client("http://127.0.0.1:8000") as client:
    health = client.health()
    state = client.state()
    robot = state.robot("car-01")
    print(health.mode, robot.x, robot.y, robot.theta)
    print(robot.measured_v, robot.command_status, robot.reason)
```

`State`、`RobotState`、`Health` 和命令回执提供类型提示与响应校验。按稳定 ID 查车，避免依赖列表顺序。未知测量保留 `None`，不会变成零；服务端新增字段保留在模型中，可以通过 `model_dump()` 读取。

`health()` 遇到服务端返回的 503 仍返回 `status="degraded"` 的健康对象，便于查看故障。连接失败和无效响应仍抛异常。`ready` 表示全部配置车辆的前提，而控制会话只检查所选车辆。

## 一个双车控制循环 {#a-two-robot-control-loop}

先运行[演示服务](./quickstart)，再执行：

```python
import time
from acfield import Client, Velocity

with Client() as client:
    with client.control("car-01", "car-02") as control:
        end = time.monotonic() + 2.0
        while time.monotonic() < end:
            tick = time.monotonic()
            state = control.state()
            # 在这里用策略 policy(state) 计算新动作。
            actions = {
                ident: Velocity(v=0.05, omega=0.0, ttl_ms=300)
                for ident in control.robots
            }
            receipts = control.commands(actions)
            time.sleep(max(0.0, min(0.1 - (time.monotonic() - tick),
                                    end - time.monotonic())))
```

这里每约 100 ms 显式发送一次新动作，TTL 为 300 ms，运行两秒。`v` 使用 m/s，`omega` 使用 rad/s，逆时针为正；模型中的上限不是推荐实车速度，服务端还会根据车辆有效限制限幅。回执反映实际接受的限幅值。

示例中的状态是全局快照；受限观测和通信规则仍需实验层实现。不要直接把全局快照提供给声称只使用局部信息的策略。

## 控制会话做了什么 {#what-a-control-session-does}

进入 `with client.control(...)` 时，SDK 检查服务健康、运行模式、所选车绑定/在线/定位与故障状态，拒绝已有控制源的车辆，逐车请求解锁，并轮询等待 `armed=true` 与控制 ID 一致。进入代码块时，解锁已得到服务端所记录的确认。

`control.state()` 检查新的快照；`control.commands()` 也会在发送前检查状态，并限制动作只能指向本会话所选车辆。服务端继续负责最终的控制权、TTL、边界和车距校验。服务器会话改变或车辆失去解锁时，会话报错，不会静默重新解锁。

正常结束、异常、Ctrl+C，以及解锁到一半失败，都会尝试释放已请求车辆的控制权。`POST /api/robots/{id}/release` 由服务端在同一个事件循环操作中检查控制源并停车锁定，避免“先查状态、再锁车”之间被其他控制器接管的竞态。释放不属于本客户端的车返回 `released=false`。

::: tip 生命周期边界
`Client.close()` 只关闭 HTTP 连接；需要自动释放控制权时使用 `control()`。低层 `arm()` 需要调用者自己配对 `release()`。独立控制器使用独立 `Client`，不要复用同一控制 ID 或重叠管理同一客户端的控制会话。
:::

清理请求被服务端接受不等于物理停止已测得，仍要结合设备 ACK、轮速和视觉反馈。强制杀进程、断网或服务端不可达时，退出请求无法保证送达，停车依赖服务端和设备看门狗。

## 实车需要显式选择 {#explicit-hardware-selection}

```python
with Client("http://127.0.0.1:8000") as client:
    with client.control("car-01", allow_hardware=True, arm_timeout=1.5) as control:
        state = control.state()
        # 在完成标定、验收和策略适配后发送有期限的新动作。
```

默认会话拒绝硬件模式，也不自动释放全局停止。`allow_hardware=True` 是调用者明确选择真实模式，不代替[首车验收](../hardware/bringup)。低层 `arm()` 和显式停车接口直接对应服务器语义，不做模式拦截。

## 接口速查 {#api-overview}

| 方法 | 返回 / 语义 |
| --- | --- |
| `client.health()` | `Health`，包括 degraded 状态 |
| `client.state()` | `State`，`state.robot(id)` 按 ID 查询 |
| `client.config()` | 配置字典 |
| `client.arm(id)` | `ArmResult`，可能仍为 pending |
| `client.command(id, v=..., omega=..., ttl_ms=300)` | 单车 `CommandReceipt` |
| `client.commands({id: Velocity(...)})` | ID → 回执的字典，统一校验一批动作 |
| `client.release(id)` | 仅在控制 ID 仍匹配时停车锁定 |
| `client.disarm(id)` | 显式锁定指定车，不限制当前控制源 |
| `client.stop_all()` | 全局停止并锁定所有车 |
| `client.reset_stop()` | 显式释放全局停止，不解锁车辆 |
| `client.control(*ids, ...)` | 等待解锁确认、检查条件、退出释放的控制会话 |

回执表示服务端接受的指令包，不表示设备已 ACK，也不表示车体已按该速度运动。`seq/ack_seq/command_status` 和测量字段是不同证据，详见[接口参考](../reference/api)。

## 错误、超时与续发 {#errors-timeouts-and-renewal}

| 异常 | 含义 |
| --- | --- |
| `APIError` | HTTP 拒绝；保留 `status_code/detail/method/path` |
| `TransportError` | 连接或超时失败，服务端是否已处理可能未知 |
| `ProtocolError` | 成功响应不符合预期格式 |
| `ControlError` | 前置条件、解锁、控制权或服务器会话发生变化 |
| `CleanupError` | 一个或多个条件释放请求失败 |
| `ValueError` / Pydantic `ValidationError` | 本地参数无效，在联网前发现 |

所有 SDK 运行错误继承 `ACFieldError`。清理失败会继续尝试其他车辆；如果策略本身已有异常，则保留该异常，附加清理失败说明并发出警告。不要把清理异常吞掉后当作已完成停车。

默认 `timeout=0.5` 是 HTTPX 各网络阶段的超时，不是硬实时截止期限。`arm_timeout` 限制确认轮询等待，正在执行的 HTTP 请求可能额外占用一个请求超时。

SDK 不自动重试动作或解锁，也没有后台线程为旧动作续期。策略阻塞时应触发 TTL；重新联网或重新获得定位后也不会自动恢复运动。慢推理需要由实验层处理观测时刻、结果有效期与显式的新动作。

当前 SDK 与同仓服务端配套；条件释放依赖新增的 `/release` 接口，旧服务器会明确报错，不退回存在竞态的锁车方式。WebSocket 订阅、异步客户端和训练环境适配留待实际需求推进。

## 设计与验证 {#design-and-validation}

独立的包让算法环境只依赖 HTTPX 和 Pydantic；同仓维护让服务器协议变化与客户端适配在一个提交中评审。高层会话管理公共控制流程，低层方法保留准确的 HTTP 语义。这里没有引入策略基类、训练框架或隐藏的后台调度。

测试对接实际控制 API，并检查多车生命周期、控制权竞态、部分失败、超时结果不确定、等待车端确认、TTL 过期与格式错误。CI 在 Python 3.11、3.12、3.13 上安装打包后的 SDK 运行这些检查。

```bash
# 仓库根目录，共享开发环境
uv sync --python 3.12 --extra test
uv run --python 3.12 pytest sdk/python/tests -q
```
