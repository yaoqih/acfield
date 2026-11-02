# 快速开始

先运行无硬件演示，确认控制台与接口。默认模式不会打开设备 UDP 通信。

## 环境

需要 Git、Python 3.11+（推荐 3.12）、Node.js 20.19+ 或 22.12+。推荐用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境。

```bash
git clone https://github.com/yaoqih/acfield.git
cd acfield/robot_server
uv sync --extra test
npm --prefix frontend ci
npm --prefix frontend run build
./run.sh
```

打开 **http://127.0.0.1:8000**。后续启动只需在 `robot_server/` 运行 `./run.sh`。

没有 uv 时：

```bash
cd acfield/robot_server
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
npm --prefix frontend ci
npm --prefix frontend run build
./run.sh
```

以上脚本面向 macOS/Linux。Windows 可在 WSL2 中运行；原生 Windows 可在建立对应虚拟环境并构建前端后运行 `python -m backend.app`，硬件网络配置需另行验证。

## 第一次操作

1. 点击场地中的小车，检查右侧状态。
2. 点击解锁，再按住方向按钮。松开后页面请求停车。
3. 在输入框外按空格，或点击全局停止，锁定所有车辆。
4. 释放全局停止后，需要重新解锁才能运动。

页面失焦或隐藏会停止续发并请求停车；服务端仍依靠自己的指令期限检查。默认按钮每 90 ms 续发，有效期 300 ms。

## 查看接口

另开终端：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/state
```

自动接口文档在 **http://127.0.0.1:8000/docs**。运行一个有时长上限的单车速度示例：

```bash
# 在仓库根目录；控制服务保持运行
uv pip install --python robot_server/.venv/bin/python -e ./sdk/python
robot_server/.venv/bin/python examples/velocity_control.py --duration 2
```

例子默认拒绝硬件模式；实车操作必须显式添加 `--hardware`，并先完成[首车验收](../hardware/bringup)。

没有 uv 时，用当前 Python 环境执行 `python -m pip install -e ./sdk/python`，然后用同一环境运行示例。独立算法环境的安装与完整接口见 [Python SDK](./python-sdk)。

## 接下来

- 理解系统为什么如此组织：[设计理念](../design/philosophy)。
- 替换示例中的策略：[接入控制算法](./control)。
- 检查存储与监听配置：[运行与配置](./configuration)。
- 准备实物：[参考硬件](../hardware/overview)。
