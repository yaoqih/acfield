# 快速开始

先显式选择无硬件演示，确认控制台与接口。演示模式不会打开设备 UDP 通信。启动脚本本身默认采用局域网实车模式；以下命令覆盖这些默认值。

## 环境 {#requirements}

需要 Git、Python 3.11+（推荐 3.12）、Node.js 20.19+ 或 22.12+。推荐用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境。

macOS / Linux：

```bash
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_UDP_HOST=127.0.0.1 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

打开[控制台](http://127.0.0.1:8000)。后续启动也要在 `robot_server/` 使用上述环境变量；直接运行 `./run.sh` 会采用脚本的实车默认值。

Windows PowerShell：

```powershell
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
cd robot_server
$env:ROBOT_MODE = "demo"
$env:ROBOT_HOST = "127.0.0.1"
$env:ROBOT_UDP_HOST = "127.0.0.1"
$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"
.\run.bat
```

首次启动会在需要时安装前端依赖并构建页面。后续在同一 PowerShell 会话的 `robot_server` 目录运行 `.\run.bat`；新终端需重新设置上述变量。按 Ctrl+C 关闭服务。控制服务和视觉服务都会启动；相机与设备网络还需在实际 Windows 环境中验证。

没有 uv 时：

```bash
cd acfield
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_UDP_HOST=127.0.0.1 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

以上无 uv 的命令适用于 macOS/Linux。Windows 建议使用上述 uv 命令，以统一根目录的 `.venv`。

## 第一次操作 {#first-interaction}

1. 点击场地中的小车，检查右侧状态。
2. 直接拖动方向摇杆，主控自动准备控制。松开后页面请求停车；电脑上也可聚焦摇杆并按住方向键操作。
3. 在输入框外按空格，或点击全局停止，锁定所有车辆。
4. 释放全局停止后，可直接重新操作摇杆；不会恢复旧动作。

摇杆相对车头控制：上前进、下后退，斜向通过左右轮速差走弧线。右前方时左轮目标较快、右轮较慢，左前方相反；倒车时左后方让车尾向左后方走，右后方让车尾向右后方走，此时车头朝相反一侧转动。在前后方向两侧各 45° 的行驶区域内，弧线为内侧轮保留至少平均轮速 30% 的同向目标。越靠近左右侧，前后速度越小、旋转越强；过渡中内侧轮会经过零速。普通固件 0.2.8 默认按目标轮速比例输出开环 PWM，实际速度随电量和负载变化，极低输出时可能无法连续起转。

摇杆左右控制转动速度，持续偏转会持续转动车头。行驶转向上限为车辆有效角速度上限与 1.5 rad/s 中的较小值；直行附近采用较柔和的转向曲线，便于微调方向。在有效上限为 0.5 m/s、6 rad/s 时，满幅前进偏转 5° 约下发 2.6°/秒的转向目标。左右横向上下各 20° 内为原地转向区，前后速度为零；从横向偏离 20° 到 45° 时平滑过渡到行驶。纯横向满幅输入使用车辆完整的有效角速度上限，摇杆幅度越大转得越快。

摇杆通过有序 WebSocket 每 25 ms 发送最新目标（40 Hz），有效期 300 ms。页面失焦或隐藏本身不锁定；键盘松键或摇杆失去键盘焦点会清除按键，触摸松手、指针取消会停止当前输入，服务端仍检查指令期限。实车模式会等待浏览器和设备完成时钟同步；演示模式立即执行，不能用来测量实车延迟。

## 查看接口 {#inspect-the-api}

另开终端：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/state
```

查看[自动接口文档](http://127.0.0.1:8000/docs)。保持控制服务运行并释放全局停止，另开终端，在仓库根目录运行下面的单车速度示例；默认控制 `car-01`，两秒后请求停车并锁定。

```bash
# macOS / Linux
.venv/bin/python examples/velocity_control.py --duration 2
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe examples\velocity_control.py --duration 2
```

例子默认拒绝硬件模式；实车操作必须显式添加 `--hardware`，并先完成[首车验收](../hardware/bringup)。

没有 uv 时，用当前 Python 环境执行 `python -m pip install -e ./sdk/python`，然后用同一环境运行示例。独立算法环境的安装与完整接口见 [Python SDK](./python-sdk)。

手机遥控使用 `http://服务器局域网IP:8000/mobile`。演示命令只监听本机；需远程访问时按[运行与配置](./configuration#startup-addresses-and-lan-access)调整监听地址。

## 接下来 {#next-steps}

- 理解系统为什么如此组织：[设计理念](../design/philosophy)。
- 替换示例中的策略：[接入控制算法](./control)。
- 检查存储与监听配置：[运行与配置](./configuration)。
- 准备实物：[参考硬件](../hardware/overview)。
