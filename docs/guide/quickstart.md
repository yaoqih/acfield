# 快速开始

**先让四辆模拟小车动起来。** 完成后可以操作控制台、查看状态，再运行一次带记录的实验。

## 环境与启动 {#requirements}

安装 Git、Python 3.11+（推荐 3.12）、Node.js 20.19+ 或 22.12+ 和 [uv](https://docs.astral.sh/uv/)。以下命令启动本机 demo。

::: code-group
```bash [macOS / Linux]
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --frozen --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
ROBOT_MODE=demo ROBOT_HOST=127.0.0.1 ROBOT_START_VISION=0 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

```powershell [Windows PowerShell]
git clone https://github.com/yaoqih/acfield.git
cd acfield
uv sync --frozen --python 3.12 --extra test
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
cd robot_server
$env:ROBOT_MODE = "demo"
$env:ROBOT_HOST = "127.0.0.1"
$env:ROBOT_START_VISION = "0"
$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"
.\run.bat
```
:::

终端出现 `Application startup complete` 后打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。应看到四辆在线小车与场地。按 Ctrl+C 退出。后续启动继续使用这些环境变量；启动脚本默认采用局域网实车模式。

| 环境 | 验证范围 |
| --- | --- |
| Ubuntu，Python 3.12，Node 22 | CI 覆盖主控、视觉、前端、文档和浏览器流程 |
| Ubuntu，Python 3.11 / 3.12 / 3.13 | SDK 安装与真实 API 集成测试 |
| macOS，Python 3.12 | 本地软件与浏览器测试；相机按具体设备验收 |
| Windows PowerShell | 提供启动脚本；相机、驱动与设备网络待实机验证 |

独立 Python 环境与无需 uv 的安装方式见 [Python SDK](./python-sdk#installation)。相机准备见[视觉定位](./localization)。

## 第一次操作 {#first-interaction}

1. 点击一辆车，确认右侧显示在线与定位有效。
2. 拖动摇杆，上为前进、下为后退、左右为转向；松手请求停车。
3. 点击全局停止，确认所有车停下。
4. 释放全局停止，再用一次新输入恢复控制。

方向键和摇杆响应细节见[手动控制](./manual-control)。手机入口为 `/mobile`，局域网访问方式见[监听配置](./configuration#startup-addresses-and-lan-access)。

## 查看接口 {#inspect-the-api}

另开终端。

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/state
```

健康响应应包含 `status="ok"`、`mode="demo"`、`ready=true`、`recording_dropped=0`。状态响应应包含四辆车，`online` 和 `visible` 为 `true`。也可打开[交互接口文档](http://127.0.0.1:8000/docs)。

## 接下来 {#next-steps}

- **做一次完整实验**，运行双车、保存日志和画图。[第一次实验](./first-experiment)
- **接自己的算法**，先看状态、坐标和控制生命周期。[控制接入](./control) · [状态字典](../reference/state) · [坐标配置](../reference/coordinates)
- **准备真实设备**，先确认硬件版本再逐车测量。[硬件兼容表](../hardware/compatibility) · [首车验收](../hardware/bringup)
