# 快速开始

先运行无硬件演示，确认控制台与接口。默认模式不会打开设备 UDP 通信。

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
./run.sh
```

打开[控制台](http://127.0.0.1:8000)。后续启动只需在 `robot_server/` 运行 `./run.sh`。

Windows PowerShell：

```powershell
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --python 3.12 --extra test
cd robot_server
.\run.bat
```

首次启动会在需要时安装前端依赖并构建页面。后续在 `robot_server` 目录运行 `.\run.bat`，按 Ctrl+C 关闭服务。控制服务和视觉服务都会启动；相机与设备网络还需在实际 Windows 环境中验证。

没有 uv 时：

```bash
cd acfield
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
./run.sh
```

以上无 uv 的命令适用于 macOS/Linux。Windows 建议使用上述 uv 命令，以统一根目录的 `.venv`。

## 第一次操作 {#first-interaction}

1. 点击场地中的小车，检查右侧状态。
2. 点击解锁，再拖动方向摇杆。松开后页面请求停车；电脑上也可聚焦摇杆并按住方向键操作。
3. 在输入框外按空格，或点击全局停止，锁定所有车辆。
4. 释放全局停止后，需要重新解锁才能运动。

页面失焦或隐藏会停止续发并请求停车；服务端仍依靠自己的指令期限检查。摇杆控制每 90 ms 续发，有效期 300 ms。

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

## 接下来 {#next-steps}

- 理解系统为什么如此组织：[设计理念](../design/philosophy)。
- 替换示例中的策略：[接入控制算法](./control)。
- 检查存储与监听配置：[运行与配置](./configuration)。
- 准备实物：[参考硬件](../hardware/overview)。
