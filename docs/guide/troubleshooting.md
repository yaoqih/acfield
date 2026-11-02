# 故障排查

先读取 `/api/health`、`/api/state` 中的事件和车端串口，再决定改配置。停车原因通常比“按钮没反应”更接近故障来源。

| 现象 | 优先检查 |
| --- | --- |
| 页面能打开，小车不能动 | 全局停止是否释放；是否显式解锁；控制 ID 是否一致 |
| 真实模式不能解锁 | 设备身份与绑定、心跳、定位有效、固件版本、故障锁存 |
| 一解锁就停车 | 定位跳变、车距/边界包络、心跳或动作到期 |
| 相机在线但定位失效 | 实际帧龄、标签遮挡、场地标定、来源声明和质量门限 |
| 运行几百毫秒后停止 | 是否在 TTL 期限内续发；策略/服务是否阻塞 |
| 第二个页面不能控制 | 同车控制权互斥；先在原控制源锁定或等待超时 |
| 日志不完整 | health 的 dropped/error、磁盘与目录权限 |
| 固件编译成功但电机不动 | motorsEnabled、每圈计数、故障锁存、方向与接线 |

## 前端缺失

`./run.sh` 会在缺少产物时尝试安装并构建前端。若失败，检查 Node 版本与依赖安装；手动执行 `npm --prefix frontend ci` 和 `npm --prefix frontend run build`。已有旧构建时，源码改动后需要重新构建。

## 契约测试被跳过

后端测试需要主机 C++ 编译器和 PlatformIO 安装的 ArduinoJson。先运行：

```bash
python3 -m pip install platformio==6.1.18
pio pkg install -d esp32_software/firmware -e general-driver
```

本地缺依赖时测试明确跳过；CI 设置 `ACFIELD_REQUIRE_FIRMWARE_CONTRACT=1`，依赖缺失必须报错，避免测试假绿。

## 端口占用

控制默认 HTTP 8000、设备 UDP 9999、视觉 HTTP 5050。检查旧进程是否仍在运行；不要为解决占用直接增加控制服务 worker。可以修改端口，但服务、固件与示例的地址必须一致。

## 提交有效的问题报告

附平台提交、运行模式、操作系统、固件与硬件版本、最小复现步骤、相关事件与停车原因。说明哪些是实测、哪些是推测。移除凭据和私有数据后，使用 [Bug Report](https://github.com/yaoqih/acfield/issues/new/choose) 模板提交。
