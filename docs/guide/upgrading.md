# 版本、兼容与升级

**一次实验固定一套代码、固件和标定。** 站点页尾显示构建时的短 commit；带 `modified` 表示工作区还有修改。部署站点可能领先于本机，按本机 commit 对照源码阅读。

## 当前兼容组合 {#compatibility}

| 层 | 当前约定 | 升级时核对 |
| --- | --- | --- |
| 主控 / Python SDK / 控制台 | 同一平台 commit，HTTP 与 WebSocket 接口随仓库演进 | 首次实验、状态字段、控制权与清理行为 |
| 普通固件 | 当前 0.2.9，协议 `v1/explicit-arm`，默认轮速闭环 | 版本字符串、计数、方向、设备限速、PI |
| 诊断固件 | 当前 0.2.5-encoder-diagnostic，专用 PWM 映射 | 排查后刷回普通固件，详见[诊断流程](./troubleshooting#encoder-diagnostics) |
| 视觉配置 | 与相机、分辨率、焦点、标签和场地对应 | 保存的外参须核验后启用 |
| 硬件 | V11、紧凑候选及新购配件分别记录 | [硬件兼容表](../hardware/compatibility) |

协议版本号相同也可能新增字段。旧主控曾拒绝带 `warning` 字段的遥测，主控与固件应配套更新。旧 0.2.1 的 `battery_sensor` 为锁存故障，当前版本为警告。当前仓库尚无正式 Release 标签，使用完整 commit 固定实验版本。[变更记录](https://github.com/yaoqih/acfield/blob/main/CHANGELOG.md)

## 升级前备份 {#backup}

先停车，在仓库根目录导出当前主控配置与版本。

```bash
mkdir -p output/upgrade-backup
curl --fail http://127.0.0.1:8000/api/config -o output/upgrade-backup/server-config.json
git rev-parse HEAD
git status --short
```

记下固件环境、版本和自己改过的 `config.h`。保存视觉页面中的运行设置，再停止主控与视觉服务，然后复制实际使用的文件。

```bash
cp robot_server/data/config.sqlite3 output/upgrade-backup/config.sqlite3
cp output/vision-settings.json output/upgrade-backup/vision-settings.json
```

上面是默认路径。使用 `ROBOT_DB` 或 `--runtime-config` 时替换为自己的路径；尚未保存的文件可能不存在。视觉运行文件包含 `profile` 和 `saved_world`，仅导出主控配置无法恢复相机内参与已保存外参。运行日志另行归档。

## 固定新版本并验证 {#pin-and-verify}

先确认工作区修改已妥善保存，再检出希望评估的完整 commit。也可用独立目录保留当前环境。

```bash
git fetch origin
git worktree add ../acfield-pinned <完整commit>
cd ../acfield-pinned
uv sync --frozen --python 3.12 --extra test
npm ci
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build
```

将备份恢复到新目录的实际运行路径。启动 demo，完成[第一次实验](./first-experiment)，确认记录完整、车辆停车与控制权释放正常。再按对应固件环境编译烧录，核对每车测量参数。

新代码默认值只影响新配置，SQLite 中已保存的限速、标签尺寸等会保留。主控保存配置会停车并新建会话，还会同步视觉场地矩形与小车标签，详见[坐标配置](../reference/coordinates)。实车实验前重新核验定位、方向、限速和停止测试。

## 回退 {#rollback}

停止两个服务，回到旧检出目录，恢复对应的数据库、视觉运行文件与固件。用旧锁文件重新安装和构建，再核对版本与标定。将失败的新版本、症状和最小日志记入 issue，便于复查。
