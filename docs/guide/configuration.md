# 运行与配置

启动方式决定初值：`./run.sh` / `.\run.bat` 默认使用局域网实车模式，并允许无定位手动控制；直接运行 `python -m backend.app` 默认是本机演示。无硬件运行请使用[快速开始](./quickstart)中的显式变量。

网页顶部可切换模拟数据与真实设备。切换会停车、全局停止并重建会话；释放全局停止后仍须重新解锁。选择只影响当前运行，重启由 `ROBOT_MODE` 决定。手机遥控入口为 `http://服务器局域网IP:8000/mobile`。

## 主控环境变量 {#server-environment-variables}

下表区分直接启动后端与启动脚本的默认值；已有环境变量优先。

| 变量 | 直接启动后端 / 启动脚本默认 | 用途 |
| --- | --- | --- |
| `ROBOT_MODE` | `demo` / `hardware` | `demo` 不打开设备 UDP，`hardware` 不运行模拟器 |
| `ROBOT_HOST` | `127.0.0.1` / `0.0.0.0` | 控制 HTTP 监听地址 |
| `ROBOT_PORT` | `8000` | 控制 HTTP 端口 |
| `ROBOT_UDP_HOST` | `127.0.0.1` / `0.0.0.0` | 设备 UDP 监听地址 |
| `ROBOT_UDP_PORT` | `9999` | 设备 UDP 端口 |
| `ROBOT_ALLOW_UNLOCALIZED_CONTROL` | `0` / `1` | `1` 跳过定位新鲜度、场地边界与车距检查；修改后需重启 |
| `ROBOT_VISION_URL` | 未设置 | 显式覆盖数据库中保存的视觉服务 URL |
| `ROBOT_DEFAULT_VISION_URL` | 未设置 / `http://127.0.0.1:8765` | 没有保存地址时的后备值；脚本随视觉端口调整 |
| `ROBOT_START_VISION` | 仅脚本使用，`1` | `0` 不启动本地视觉服务 |
| `ROBOT_VISION_PORT` | 仅脚本使用，`8765` | 本地视觉端口 |
| `ROBOT_VISION_RUNTIME_CONFIG` | 仅脚本使用，未设置 | 覆盖视觉配置路径；默认文件位于仓库根目录 `output/vision-settings.json` |
| `ROBOT_NTP_SERVER` | `pool.ntp.org` | 每 300 s 尝试校时；空字符串禁用；离线沿用本机时间映射 |
| `ROBOT_DB` | `robot_server/data/config.sqlite3` | 持久配置 |
| `ROBOT_LOG_DIR` | 数据库旁的 `runs/` | 主控运行日志 |

无定位模式仍要求设备绑定、心跳新鲜、无故障、显式解锁、控制权及有限指令期限。它会关闭依赖位置的保护，不能据此判断场地定位链路已经可用。需要定位保护的实验显式设 `ROBOT_ALLOW_UNLOCALIZED_CONTROL=0`；当前值可在 `/api/state` 的 `allow_unlocalized_control` 查看。

## 启动地址与局域网访问 {#startup-addresses-and-lan-access}

在 `robot_server/` 启动时，终端会显示控制台、API 和检测到的主机 IPv4。脚本默认已监听局域网；若只需让其他电脑访问演示服务，可运行：

```bash
ROBOT_MODE=demo ROBOT_HOST=0.0.0.0 ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

把可达的 `LAN / SDK` 地址传给 `Client("http://主机IP:8000")`，手机在该地址后加 `/mobile`。IPv4 来自主机名解析和路由表，可能包含 VPN 地址。打印检测 IP 不会修改监听地址。直接启动后端时，`ROBOT_HOST=0.0.0.0` 才会开放控制 HTTP 的局域网监听。

## 相机视觉服务 {#camera-vision-service}

`./run.sh` / `.\run.bat` 同时启动主控和本机视觉服务，退出时关闭其启动的视觉进程；`python -m backend.app` 不启动视觉。首次启动不连接相机，之后恢复已保存的连接状态。演示模式可以配置实物相机，但小车位置仍来自模拟器。

在主控「实验配置 → 相机与视觉」中读取配置、刷新设备并选择相机。摄像头 ID 属于运行视觉服务的电脑。采集分辨率与帧率是请求值，应核对实际图像尺寸与采集帧率。内参与场地外参按[视觉定位与标定](./localization#calibration-order)操作；独立标定页提供 ChArUco 内参采集与求解。

修改 `ROBOT_VISION_PORT` 可避开占用。使用独立服务时设 `ROBOT_START_VISION=0`，并保存其 URL。原版 `apriltag_live.py` 只监听 `127.0.0.1`；跨电脑使用需要另行设置受控转发或部署方式，修改 `ROBOT_HOST` 不会开放视觉服务。

视觉配置默认保存在仓库根目录 `output/vision-settings.json`；自定义相对路径按视觉进程工作目录解析（启动脚本为 `robot_server/`）。`apriltag_live.json` 提供初始默认值，运行界面不会覆盖它。预览宽度/帧率只影响 MJPEG 显示，重启恢复默认，不改变采集与检测配置。

独立标定前锁定所有小车；标定后在主控重新读取相机配置再保存，避免用旧草稿覆盖新内参。备份运行配置中的内参、实测坐标与标签尺寸；重启后使用「核验并加载」重新验证场地外参。

## 真实模式示例 {#hardware-mode-example}

完成硬件验收与相机标定后，在 `robot_server/` 运行定位保护模式：

```bash
ROBOT_MODE=hardware ROBOT_HOST=0.0.0.0 ROBOT_UDP_HOST=0.0.0.0 \
  ROBOT_ALLOW_UNLOCALIZED_CONTROL=0 ./run.sh
```

`./run_hardware.sh` / `.\run_hardware.bat` 显式选择实车模式，但仍继承主脚本的无定位默认值；需要定位保护时也必须设置该变量为 `0`。Windows 在运行脚本前用 `$env:ROBOT_ALLOW_UNLOCALIZED_CONTROL = "0"` 设置。

## 车辆与场地配置 {#robot-and-arena-configuration}

通过控制台或 `GET/PUT /api/config` 配置场地、车辆身份、标签 ID、车体轮廓、控制点/标签偏移和速度限制。保存前所有车必须锁定；保存会停车并重建会话。

真实模式保存时，控制台把小车的 AprilTag ID、黑框边长和安装高度同步到视觉服务。航向修正在主控端填写。95 mm 亚克力候选标签名义黑框 72 mm、成品 80 mm，旧 V11 为 104/130 mm。安装高度从地面量到标签中心。现有配置不会随硬件方案自动迁移；共享视觉服务时确保只有一个主控管理其配置。

A12 1:20 电机的新建车辆主控限速为 `0.50 m/s`、`1.50 rad/s`。真实模式取车辆配置与设备报告限制的较小值；当前固件上限为 `0.89 m/s`、`3.00 rad/s`，无设备限速报告时回退到 `0.10 m/s`、`0.30 rad/s`。模拟模式直接使用配置限速。已有数据库保留原值，更换电机后需在实验设置中更新对应车辆。默认约 200 × 160 mm 的车体包络是保守初值，需测量包含轮、标签板与安装偏移的实际外廓。

## 控制权与网络 {#ownership-and-networking}

HTTP 解锁和非零动作使用同一 `X-Control-ID`，WebSocket 控制的 `owner` 也须与其一致。其他页面或策略不能覆盖同车的非零运动，但可以请求停车。控制 ID 只用于互斥。

系统面向本机和可信实验局域网，没有账号鉴权或 UDP 身份认证。GitHub Pages 只发布静态文档。

## 开发模式 {#development-mode}

以下均在仓库根目录执行：

```bash
uv run --python 3.12 --extra test pytest -q
uv run --python 3.12 --extra test pytest sdk/python/tests -q
npm --prefix robot_server/frontend run dev
```

前端开发服务器代理 API 到本机 8000。已有 `frontend/dist/index.html` 时启动脚本不会自动重建；修改源码后运行 `npm --prefix robot_server/frontend run build`。后端使用单进程、单 worker，重计算策略放到外部进程。
