# General Driver for Robots 固件 0.2.1

适用 SKU23730 / ESP32-WROOM-32UE + TB6612FNG，与 `robot_server` 配套。主控是ESP32，无需STM32或额外串口桥。供应商示例不在本仓分发；平台参考见 [ACField 文档](https://yaoqih.github.io/acfield/hardware/bringup)。

## 配置与构建

1. `cp include/secrets.example.h include/secrets.h`，填写实际Wi-Fi和主控电脑IPv4。凭据文件不会进入版本控制。
2. `include/config.h`采用V10/V11名义轮径34mm、轮距122mm、初调上限0.10m/s及0.30rad/s；需要实物验证。左右轮计数默认为0，**不能用旧例程462或商家四倍频计数代替**。
3. 保持`motorsEnabled=false`，烧录后查看控制台“左/右编码计数”，手动分别转轮若干整圈，取计数差绝对值/圈数。本固件只在编码器一相RISING时计数；填写左右各自`pulsesPerTurn`。无编码器电机不适用。
4. 确认电机线序（资料中PIN5的VCC/GND有冲突），编码器用3.3V。A接左、B接右；架空、低速验证`motorSign`和`encoderSign`，两轮前进反馈为正，左转角速度为正。之后才启用电机、整定前馈/PI及最大轮速。默认PI数值不是已完成的电机标定。
5. 用万用表校验INA219回传电压，验证欠压阈值及板卡版本。默认3S总压低于10.5V持续1s锁存停车；总压不替代逐节保护。欠压、传感器或编码器故障排除后重启车端重新解锁。

```sh
cd esp32_software/firmware
pio run                    # car-01
pio run -t upload
pio run -e car-02           # 其余car-03/car-04同理
pio run -e car-02 -t upload
pio device monitor
```

四车必须选各自环境烧录，不能四块板都用car-01身份。未创建secrets.h时使用占位网络值，仍可编译。

## 执行规则

独立50Hz运动任务检查TTL并更新PI，Wi-Fi/UDP和I2C在网络任务执行；共享状态通过互斥保护。控制周期超100ms触发故障，约1s ESP任务看门狗作为后备。正常指令有效期100–500ms，过期归零并取消解锁。重复包不会延长TTL。

启动、断网恢复后先停车绑定，再显式解锁；车端确认后主控才允许运动。正常零速drive保持解锁；stop取消解锁；超时或链路恢复都不会自动继续运动。故障锁存时只接受停车，排除原因后重启设备。

新会话或断网重绑须回显新鲜且晚于上次绑定的遥测；用递增遥测界限阻止历史会话报文重绑，移除了固定32个历史会话槽。绑定首包过旧会被拒绝，服务端会以最新遥测重试。

已实现目标轮速协调限幅、加速度限制、条件积分、编码器长时间无响应/反向异常、过速、欠压和电压传感器异常停车。诊断阈值是初调值，需低速实车验证；不能据编译成功认定堵转诊断/停止距离已经通过。

无响应检测同时要求至少800ms无脉冲，且目标累计行程达到3个编码脉冲距离；按实测编码分辨率换算，覆盖默认原地转向，也允许低速/低分辨率编码器较长的脉冲间隔。

遥测含左右累计原始编码计数、左右轮速、车速、电压、固件版本、状态/停机原因、有效速度限制与ack。没有可信电量估计时battery仍为null。公开板图INA219支路不包含电机总电流，本固件不提供虚假的电机电流/整包电流。

协议及主控启动方式见 [robot_server说明](../../robot_server/README.md)。两端必须一起升级：旧固件缺少action和显式状态，不能满足新服务端的解锁确认。

## 引脚与验证

电机A：PWM25/IN1=21/IN2=17，电机B：PWM26/IN1=22/IN2=23。编码器A在GPIO34上升沿读35，B在16上升沿读27。GPIO34/35没有内部上拉，确认实际板载信号偏置。INA219地址0x42，I2C SDA32/SCL33。

```sh
clang++ -std=c++11 -Wall -Wextra -Werror -I include test/protocol_test.cpp -o /tmp/robot-protocol-test
/tmp/robot-protocol-test
# 从robot_server运行：.venv/bin/python -m pytest -q
```

服务端测试会编译`test/device_peer.cpp`，用真实服务端报文调用固件的`command_wire.h`和`protocol.h`，覆盖丢首包、绑定、解锁、超时和重连。需先执行过`pio run`安装ArduinoJson，并有clang++/g++。

实车依次验证：架空正反方向/计数、落地低速整定、松手/断网/遮标签/关闭主控停车、编码器断线停车、欠压、重启保持停车。软件保护不替代实体断电开关。电机方向、满充供电瞬态、温升与真实停止时间仍需实物测试。
