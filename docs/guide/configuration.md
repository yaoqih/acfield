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

## 相机视觉服务 {#camera-vision-service}

在仓库根目录运行 `python apriltag_live.py --source demo`（虚拟标签只用于验证流程），或使用真实相机：

```bash
python apriltag_live.py --source 0 --port 8765
```

在主控「实验配置 → 相机与视觉」中读取服务配置，刷新设备列表并选择相机。主控和视觉服务可以在不同电脑上运行；填写的是主控服务器可访问的视觉服务地址，摄像头 ID 则属于视觉服务所在的电脑。采集分辨率和帧率是请求值，应对照页面显示的实际图像尺寸和帧率调整。

内参必须来自当前相机和分辨率的实测标定。标签边长取 AprilTag 黑色外框实测尺寸，安装高度取场地地面到标签中心的实测高度。按场地原点填写四个固定标签的 ID 和坐标，确认测量后保存并连接相机；全部固定标签同时可见时，执行「标定并保存」。切换相机或修改内参、尺寸和坐标后需重新标定。重新启动视觉服务会断开相机；可用界面的连接操作恢复，并核验已保存的标定。

视觉相机配置保存在仓库根目录 `output/vision-settings.json`；主控配置存于 `robot_server/data/config.sqlite3`。旧的 `apriltag_live.json` 仍用于初始默认值，界面运行配置不会覆盖它。请备份相机内参和固定标签实测坐标。

## 真实模式示例 {#hardware-mode-example}

完成硬件与相机标定后，在 `robot_server/` 运行：

```bash
ROBOT_MODE=hardware ROBOT_UDP_HOST=0.0.0.0 ROBOT_VISION_URL=http://127.0.0.1:8765 ./run.sh
```

运行主控时先启动仓库根目录的 `apriltag_live.py`，默认地址为 `http://127.0.0.1:8765`。也可在网页中填写视觉服务地址；服务地址将保存在主控配置中。

## 车辆与场地配置 {#robot-and-arena-configuration}

通过控制台修改，或使用 `GET/PUT /api/config`。配置包括场地大小、车辆身份、标签 ID、车体轮廓、控制点/标签偏移和速度限制。保存前所有车必须锁定；保存会停车并重建会话。

真实模式保存时，控制台把小车的 AprilTag ID、黑框边长和安装高度同步到视觉服务。航向修正在主控端填写。黑框边长不包括白色边缘；参考标签黑框为 104 mm，含白边外框为 130 mm。安装高度从场地地面量至标签中心并实测填写。不同相机或视觉服务共享同一配置时，请确保实验期间只有主控服务管理该视觉配置。

默认车体包络约 200 × 160 mm，是保守初值，并非 V11 的实测外廓。不要只按打印底盘大小缩小包络，应把轮、标签板及安装偏移一起测量。

## 控制权与网络 {#ownership-and-networking}

解锁和非零动作使用同一 `X-Control-ID`。它用于控制权互斥，不是用户身份认证。不同页面或策略不能覆盖同车正在执行的非零命令，但可以请求停车。

初版面向本机和可信实验局域网，没有账号鉴权或 UDP 身份认证。GitHub Pages 只发布静态文档，不托管控制服务，也不会通过网站直接控制实验室小车。

## 开发模式 {#development-mode}

```bash
# 后端，robot_server/ 内
uv run --python 3.12 --extra test pytest -q

# 前端，仓库根目录
npm --prefix robot_server/frontend run dev
```

前端开发服务器代理 API 到本机 8000。使用单进程、单 worker；重计算策略放到外部进程。
