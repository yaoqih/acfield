# 物料与机械设计

参考方案使用 Waveshare General Driver for Robots（SKU23730，ESP32 + TB6612）、双编码器减速电机与场外 AprilTag 定位。公开硬件整理为 **V11 参考设计**，仍需首件测量与试装；它没有被标记为已量产或已完成四车路试。

[![V11 完整装配与移除顶盖后的内部结构](/images/assembly.svg)](/images/assembly.svg)

## 装配与爆炸图 {#assembly-and-exploded-view}

[![V11 分层爆炸图：顶盖、主控、支柱、电池、电机、轮、底盘与辅助球轮](/images/exploded.svg)](/images/exploded.svg)

图中包含标签顶盖、主控板、4 根 50 mm 与 4 根 25 mm 支柱、3S 电池、两台编码器电机、两只驱动轮、打印底盘和辅助球轮。爆炸图沿安装方向分离部件，并将球轮翻转以露出球面；间距不代表实际装配尺寸，部分紧固件省略。

打印底盘与顶盖使用仓库 CAD 几何；采购件使用名义尺寸和简化外观，板上连接器不作为接线依据。顶盖的平整标签面朝上，加强筋朝下。原来的透明三角网格叠层预览已改为不透明表面与深度缓冲渲染。

点击图可打开原尺寸。[爆炸图 PNG](/images/exploded.png)可用于演示；[装配图 PNG](/images/assembly-zh.png)用于并排查看完整装配与内部结构。公共设备的布置见[场地与相机布置](./arena)。

## 机械参考 {#mechanical-reference}

| 参数 | V11 名义值 | 使用说明 |
| --- | --- | --- |
| 底盘/顶板外廓 | 130 × 130 mm | 总包络仍需包含轮、螺丝和装配偏移 |
| 轮直径 / 轮距 | 34 / 122 mm | 控制前实测有效值 |
| 驱动轴位置 | 几何中心后方 16 mm | 控制点位于轴中点 |
| 车顶标签面高度 | 约 64.6 mm | 装好后测量 |
| 车顶黑框 / 含白边 | 104 / 130 mm | 整面覆盖，不避螺丝；白边完整 |
| 打印件 | 底盘 + 标签板，共两件 | 不包含历史 modifier 或旧打印包 |

STL、参数、构建与审查源文件位于 [hardware_design/print_v11](https://github.com/yaoqih/acfield/tree/main/hardware_design/print_v11)。默认两个件统一 PETG、0.4 mm 喷嘴、0.2 mm 层高、4 圈外壁、5 层顶底、40% Gyroid/Cubic；实际材料用量、支撑与强度以切片和首件为准。

## 物料类别 {#bill-of-material-categories}

| 类别 | 参考内容 | 每车数量 |
| --- | --- | --- |
| 控制 | General Driver for Robots | 1 |
| 动力 | A12 12V 1:150 编码电机与支架 | 2 |
| 接地 | 34 mm 轮、CY12B 球轮 | 2 + 1 |
| 电源 | 3S 电池、带保险线束、断电开关 | 按接线方案 |
| 结构 | 两件打印件、25/50 mm M3 柱与紧固件 | 见加工清单 |
| 标签 | tag36h11 黑框 104 mm | 1 |
| 公共设备 | 相机/镜头/固定架、路由器、电脑、充电设备 | 按场地共用 |

目录内 CSV 保留当前物料、打印顺序和接线参考；个人购物车与旧报价已移至 Git 历史。清单未包含所有加工、运费、公共设备和缺件，电机、线束和电池的实物版本要逐项核验。无需为平台额外制作旧 STM32/串口桥或自制 PCB。

## 为什么是这套布局 {#why-this-layout}

两驱动轮与一个低阻支撑点对应差速模型；电池低位放置，标签板提供稳定几何参考。设计尽量使用通用紧固件和两件式打印结构，降低首次装配的复杂度。

车体稳定、球轮阻力、支架同轴度和编码器反馈，会直接影响低速控制。名义几何正确不能证明摩擦、回差、打印强度或停止行为合格。

## 可编辑与可审查 {#editable-and-inspectable}

使用仓库根目录的共享 Python 环境运行 CAD 工具：

```bash
uv sync --python 3.12 --extra test
uv run --python 3.12 python hardware_design/print_v11/build.py
uv run --python 3.12 python hardware_design/print_v11/audit.py
# 安装仓库 JS 依赖与渲染浏览器
npm ci
npx playwright install chromium
uv run --python 3.12 python hardware_design/print_v11/render.py
```

构建会重新生成 STL、装配与参数文件，审查会更新名义几何报告。供应商尺寸假设在参数中显式标记，变化时应重新生成与核对。渲染可以在 build 产生预览网格后运行。

首车确认后再复制其他车辆。详见[固件与首车验收](./bringup)。
