# 完成第一次实验

**用 demo 跑一次双车运动，保存记录，再画出轨迹。** 全程约 5 分钟，无需相机和小车。先按[快速开始](./quickstart)启动服务，以下命令均在仓库根目录执行。

## 运行并保存 {#run-and-save}

保持服务运行，释放控制台的全局停止，关闭其他正在控制车辆的页面。

<!-- docs-test: experiment-command -->
```bash
uv run --frozen python examples/velocity_control.py \
  --robots car-01 car-02 --duration 2 --v 0.05 --omega 0.2 \
  --output output/first-run
```

预期输出包含 `Controlling car-01, car-02 for 2 s`、`Experiment completed` 和清单路径。两车低速走弧线，约两秒后请求停车并释放控制权。`output/first-run/experiment.json` 保存参数、首尾状态、主控运行 ID、会话和代码版本。每次运行换一个输出目录。

若显示 `aborted`，先查看清单中的 `error` 与[故障排查](./troubleshooting)。已有全局停止、控制权冲突或定位失效都会中断示例。

## 分析与画图 {#analyze-and-plot}

回到服务终端按 Ctrl+C，等待服务退出，使日志写入完成。然后运行分析器。

<!-- docs-test: analysis-command -->
```bash
uv run --frozen python examples/analyze_run.py output/first-run --plot
```

若主控自定义了日志目录，补充 `--logs /你的日志根目录`。结果写在同一实验目录。

| 文件 | 看什么 |
| --- | --- |
| `experiment.json` | 本次任务参数、版本、是否完成、首尾状态 |
| `summary.json` | 采样数、观测时长、路径长度、首尾位移、超过 200 ms 的定位空档 |
| `trajectories.csv` | 每车的相对时间、世界 X/Y 与航向 |
| `trajectories.png` | 等比例世界坐标轨迹，圆点为起点，叉号为终点 |

两秒、0.05 m/s 的理想路径约为 **0.10 m**。启动握手和系统调度会带来偏差，先检查数量级与空档，再比较误差。分析器跳过超过 200 ms 的轨迹间隔，图中也断线；路径长度因此可能偏小。

![由真实 demo 日志生成的双车轨迹](/examples/first-run/trajectories.png)

图来自仓库示例的一次 demo 运行。可下载[实验清单](/examples/first-run/experiment.json)、[结果摘要](/examples/first-run/summary.json)和[轨迹表](/examples/first-run/trajectories.csv)。这些数据用于核对流程和文件格式，实车性能需要单独测量。

原始事件随仓库保存在 `docs/public/examples/first-run/logs/`。无需启动服务即可复查。

```bash
uv run --frozen python examples/analyze_run.py docs/public/examples/first-run \
  --logs docs/public/examples/first-run/logs --plot
```

## 换成自己的策略 {#replace-the-policy}

在 `examples/velocity_control.py` 的循环内，使用 `state` 计算每台车的 `Velocity`。先按 `robot.online`、`robot.visible` 和 `pose_age_ms` 判断观测是否可用。完整含义见[状态字典](../reference/state)。

保持每轮约 100 ms 的发送节奏。策略耗时超过 300 ms 的命令期限时会停车，先记录推理耗时再提高复杂度。多车目标放在同一次 `control.commands(actions)` 提交。

实车运行先完成[首车验收](../hardware/bringup)，再显式增加 `--hardware`。保存固件版本、硬件修订、标定文件、策略版本和环境条件。日志字段与配对方法见[记录与复现](./recording)。
