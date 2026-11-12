# 固件与首车验收

先把一个完整控制闭环测清楚，再复制其他车辆。当前固件配置允许电机输出（`motorsEnabled=true`），但左右编码器每圈计数为按减速比换算的 60，且计数、方向、PI 参数和实际限速仍需实测标定；首次上电必须架空测试，不能直接落地运行。

四辆车现已从 A12、12 V、1:100 更换为同系列 1:20 编码电机。34 mm 轮配名义额定 500 rpm 对应约 0.89 m/s；固件线速度及轮速上限为 0.89 m/s、角速度上限为 3.00 rad/s，主控默认限速为 0.50 m/s、1.50 rad/s。加速度限制已移除。每圈计数由旧配置的 300 换算为 60，假设编码器相同，仍需分别实测左右轮。

## 配置与构建 {#configure-and-build}

安装 PlatformIO，在仓库根目录执行：

```bash
python3 -m pip install platformio==6.1.18
cp esp32_software/firmware/include/secrets.example.h esp32_software/firmware/include/secrets.h
# 在 secrets.h 填写 Wi-Fi 和主控 IPv4；该文件被 Git 忽略
pio run -d esp32_software/firmware -e general-driver
```

`general-driver` 是 car-01，其余是 `car-02`、`car-03`、`car-04`。烧录时明确选择环境：

```bash
pio run -d esp32_software/firmware -e car-02 -t upload
pio device monitor -d esp32_software/firmware -e car-02
```

## 分阶段验收 {#staged-acceptance}

| 阶段 | 操作与证据 | 进入下一阶段前确认 |
| --- | --- | --- |
| 断电检查 | 极性、绝缘、保险、紧固、三点接地、球轮和线束空间 | 物料与接线匹配，无擦地与松动 |
| 禁止输出 | 手转左右轮记录若干整圈计数；万用表交叉检查电压 | 分别填写真实计数，排除 VCC/GND 图纸冲突 |
| 架空低速 | 左右电机/编码器方向、前进与左转、PI 初调 | 反馈符号正确，无持续发散或异常 |
| 单车落地 | 最低稳定速度、直行/原地转向、停止时间与距离 | 在当前地面可控，保护假设符合测量 |
| 相机联动 | 全场位置/航向误差、帧龄、遮挡与相机移动 | 不可信定位能导致失效，恢复不自动解锁 |
| 故障注入 | 断网、停主控、编码器异常、欠压、设备重启 | 停车与锁定符合规则，故障原因可见 |
| 双车到四车 | 身份、控制权、联合动作、车距保护、持续运行 | 保存运行记录，再接自动策略 |

实际电机每圈计数必须按固件使用的单相上升沿计数方法测量，不能套用商家四倍频数值。左右轮分开标定。电机、编码器和电源优先使用已购成品转接线；散装端子和压线工具不属于首车验收的必需物料，但每根线的针序仍要逐线核对。

## 关键硬件边界 {#important-hardware-boundaries}

当前参考引脚、电压阈值和诊断细节见 [固件 README](https://github.com/yaoqih/acfield/blob/main/esp32_software/firmware/README.md)。电机/编码器接线应按针号与实测确认，不能只按线色。

3S 欠压保护初值是总压低于 10.5 V 持续 1 s 锁存停车；总压不能替代逐节监测。实体断电开关和电源保护属于装配方案的一部分。首车还应核对满充供电、温升与电池固定。

## 留下最小测量记录 {#keep-a-minimal-measurement-record}

为每车保存物料修订、轮径/轮距、每圈计数、方向、PI 与限制、定位偏移、停止测试条件及结果。对保护阈值的每次调整记录依据。硬件修订和参数文件应能关联到运行日志。
