# 记录与复现

记录的作用是帮助解释每次运行：控制器要求什么、平台允许什么、设备报告什么，以及为什么停止。

## 平台已经记录什么 {#what-is-recorded}

每次主控启动在数据库旁的 `runs/` 创建独立目录。配置与事件分别保存，`events.jsonl` 使用每行一个 JSON 对象，记录定位、动作、遥测、停车与配置等事件。控制记录包含原始动作、限幅结果和拒绝原因。

后台使用有界队列，`/api/health` 暴露运行 ID、丢弃计数和写入错误。队列满或写入失败会影响证据完整性，实验脚本应预先约定中止或标记无效的规则。

这些日志属于工程运行记录；一次主控运行 ID 不等同于一次论文实验回合。

## 建议补充实验清单 {#suggested-experiment-manifest}

```yaml
experiment: formation-reference
platform_commit: <git commit>
firmware_commit: <git commit>
hardware_revision: V11-first-article
calibration_id: <measured configuration hash>
controller: <method and version>
scenario: <initial poses and task parameters>
seed: <simulation seed, if applicable>
run_id: <server run id>
episode_id: <experiment-owned id>
result: success | failure | aborted
```

这是建议格式，不是当前解析器支持的配置文件。实验层还应保存策略实际观测、动作、推理耗时、消息及终止判据。

## 重复性需要分层讨论 {#discuss-repeatability-at-each-layer}

固定种子与步长能约束仿真，但不能消除实车初始摆位、地面摩擦、电量和视觉条件变化。实车记录初始误差、环境、重复次数和异常运行处理方式。

平台日志目前不提供完整的物理重演或一键轨迹回放。后续可以基于日志加入可视化与回合评测，但不能把已有事件文件描述为完整研究复现框架。

## 数据与仓库 {#data-and-repositories}

不要提交本机 SQLite、Wi-Fi 凭据或原始长视频。小型公开示例结果可随版本提供；较大数据集、视频与模型权重应放在 Release 或数据归档，并保存校验值、许可证和生成版本。
