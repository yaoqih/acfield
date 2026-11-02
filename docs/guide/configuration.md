# 运行与配置

主控服务默认本机监听、演示模式。真实设备模式需要明确指定，且不会同时运行内置模拟器。

## 主控环境变量 {#server-environment-variables}

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `ROBOT_MODE` | `demo` | `demo` 或 `hardware` |
| `ROBOT_HOST` | `127.0.0.1` | HTTP 监听地址 |
| `ROBOT_PORT` | `8000` | HTTP 端口 |
| `ROBOT_UDP_HOST` | `127.0.0.1` | 设备监听地址，局域网接入常设为 `0.0.0.0` |
| `ROBOT_UDP_PORT` | `9999` | UDP 端口 |
| `ROBOT_VISION_URL` | 空 | 已标定相机服务 URL |
| `ROBOT_DB` | `robot_server/data/config.sqlite3` | 持久配置 |
| `ROBOT_LOG_DIR` | 数据库旁的 `runs/` | 运行日志目录 |

## 启动地址与局域网访问 {#startup-addresses-and-lan-access}

通过 `./run.sh` 或 `python -m backend.app` 启动时，终端会显示控制台地址、API 文档地址和检测到的主机 IPv4。默认只监听本机；另一台电脑需要连接 SDK 时，在 `robot_server/` 运行：

```bash
ROBOT_HOST=0.0.0.0 ./run.sh
```

然后把输出的 `LAN / SDK` 地址传给 `Client("http://主机IP:8000")`。IPv4 来自主机名解析和路由表检测，可能包含 VPN 地址；选择客户端实际可达的实验网络地址。打印检测 IP 不会自动修改监听地址。

## 真实模式示例 {#hardware-mode-example}

完成硬件与相机标定后，在 `robot_server/` 运行：

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ROBOT_VISION_URL=http://127.0.0.1:5050 ./run.sh
```

主控与视觉服务在同一电脑运行最便于初期联调。`5050` 是视觉默认端口，按实际启动配置填写。

## 车辆与场地配置 {#robot-and-arena-configuration}

通过控制台修改，或使用 `GET/PUT /api/config`。配置包括场地大小、车辆身份、标签 ID、车体轮廓、控制点/标签偏移和速度限制。保存前所有车必须锁定；保存会停车并重建会话。

服务器中的 `tag_size` 只用于记录，不会回写视觉配置。实际标签尺寸、安装高度和标签朝向在 `apriltag_live.json` 中设置，两个模块需要对应核对。参考硬件使用 104 mm 黑框、含白边 130 mm 的整面标签。车辆视觉配置使用 size_m=0.104，服务器中也记录 tag_size=0.104；标签面名义高度 height_m=0.0646，装车后实测更新。旧配置或合成场景中的尺寸不能直接套用到实物。

默认车体包络约 200 × 160 mm，是保守初值，并非 V11 的实测外廓。不要只按打印底盘大小缩小包络，应把轮、标签板及安装偏移一起测量。

## 控制权与网络 {#ownership-and-networking}

解锁和非零动作使用同一 `X-Control-ID`。它用于控制权互斥，不是用户身份认证。不同页面或策略不能覆盖同车正在执行的非零命令，但可以请求停车。

初版面向本机和可信实验局域网，没有账号鉴权或 UDP 身份认证。GitHub Pages 只发布静态文档，不托管控制服务，也不会通过网站直接控制实验室小车。

## 开发模式 {#development-mode}

```bash
# 后端，robot_server/ 内
uv run --extra test pytest -q

# 前端，仓库根目录
npm --prefix robot_server/frontend run dev
```

前端开发服务器代理 API 到本机 8000。使用单进程、单 worker；重计算策略放到外部进程。
