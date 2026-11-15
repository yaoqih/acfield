<script setup>
import { withBase } from 'vitepress'
</script>

# 硬件资料、CAD 与参数图片

整理日期：2026-11-15。优先列出主控板官方资料与加工文件，其后按主控、动力接线、电池、相机顺序归档参数图片。[详细 BOM](./bom) 记录本次选项和数量，[物料与机械设计](./overview) 说明现有设计。

## 主控板文档与 CAD {#controller-documents-and-cad}

主控板参考为 **Waveshare General Driver for Robots**。以下直接链接来自本次读取的[官方「相关资料」页](https://docs.waveshare.net/General_Driver_for_Robots/Resources-And-Documents/)，链接对应官方在线文件；本项目图纸见下一节。购买的“ROS机器人驱动板”仍需对照实物版本，不能只凭标题确定完全相同。

| 重要程度 | 资料 | 用途 | 官方入口 / 文件 |
| --- | --- | --- | --- |
| 1 | 主控板产品文档 | 板卡介绍、接口与开发入口 | [General Driver for Robots](https://docs.waveshare.net/General_Driver_for_Robots/) |
| 2 | 电路原理图 | 供电路径、电机驱动、编码器信号、电平与引脚复核 | [原理图 PDF](https://www.waveshare.net/w/upload/3/37/General_Driver_for_Robots.pdf) |
| 3 | 主控板二维 CAD | 核对 PCB 外廓、孔位与安装配合 | [DXF 图纸 ZIP](https://www.waveshare.net/w/upload/5/50/GENERAL-DRIVER-FOR-ROBOTS-STR-DXF.zip) |
| 4 | 主控板三维 CAD | 导入装配，检查元件、接口与外壳净空 | [STEP 模型 ZIP](https://www.waveshare.net/w/upload/8/8e/General_Driver_for_Robots_STEP.zip) |
| 5 | 主控板尺寸图 | 看图与人工测量对照 | [尺寸 PDF ZIP](https://www.waveshare.net/w/upload/0/0a/GENERAL-DRIVER-FOR-ROBOTS-STR-PDF.zip) |
| 6 | 编码器转速反馈例程 | 对照计数与转速读取方法 | [EncoderRpmFeedback.rar](https://www.waveshare.net/w/upload/3/3c/EncoderRpmFeedback.rar) |
| 7 | 编码电机控制 / 闭环例程 | 对照驱动与速度闭环实现 | [MotorCtrl.rar](https://www.waveshare.net/w/upload/0/08/MotorCtrl.rar) · [SpeedLoopCtrl.rar](https://www.waveshare.net/w/upload/1/18/SpeedLoopCtrl.rar) |
| 8 | 综合开源例程 | 查看上游固件组织 | [UGV01_BASE.zip](https://www.waveshare.net/w/upload/0/0c/UGV01_BASE.zip) |

导入 CAD 时确认毫米单位，并核对板卡版本、插座朝向与实际元件高度。官方示例用于参考，本项目固件与引脚以[固件与首车验收](./bringup)及仓库实际实现为准。

## 本项目加工与打印文件 {#fabrication-files}

以下文件由仓库已有设计复制到网站下载目录；底板、顶板与打印包均保持原文件内容。图纸仍是 **95 mm 首件候选**，顶板安装孔与标签黑框的冲突尚未解决，须先确定固定方案再加工。

| 优先级 | 文件 | 规格与交付说明 |
| --- | --- | --- |
| 1 | [底板 + 顶板 DXF ZIP](/downloads/hardware/95x80_flat_cutting_dxf.zip) | 毫米单位、1:1；首件各 1 片，底板 4 mm、顶板 2 mm；发给亚克力加工商时同时说明板厚和数量。 |
| 2 | <a :href="withBase('/downloads/hardware/bottom_plate_95.1x80_flat_4mm.dxf')" download>底板 DXF</a> | 95.1×80×4 mm；0.1 mm 长度差来自现有设计，不能自行改为 95 mm。 |
| 3 | <a :href="withBase('/downloads/hardware/top_plate_95x80_flat_2mm.dxf')" download>顶板 DXF</a> | 95×80×2 mm；标签区内有 4 个悬挂孔，不能让孔洞或凸起紧固件破坏图案。 |
| 4 | [12 款 AprilTag PNG ZIP](/downloads/hardware/tag36h11_80mm_white4_12ids_png.zip) | tag36h11、ID 10–21；80×80 mm 成品、72 mm 黑框、每边白边 4 mm，100% 比例，无出血。 |
| 5 | [尺寸、孔位与装配说明](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/dimensions.md) | 现有设计使用 45/15 mm 柱与 1:20 电机；本次采购为 50 mm 柱与 1:30 电机，不能直接视为已经适配。 |

源文件保存在 [hardware_design/acrylic_95](https://github.com/yaoqih/acfield/tree/main/hardware_design/acrylic_95)，下载副本的来源与 SHA-256 见[文件索引](/downloads/hardware/manifest.json)。本次没有修改切割轮廓、孔位或标签图案。

## 主控板参数图片 {#controller-parameters}

原图给出 ESP32-WROOM-32、TB6612FNG、XH2.54 电源接口与两路 PH2.0-6P 编码电机接口。尺寸图标 65 mm 横向外廓及 49/58 mm 安装孔距；板边、延伸接口及元件包络应结合 DXF/STEP 复核。文字图写输入 DC 7–13 V，板上丝印又标 DC 9–12.6 V，实际允许范围需按具体版本和原理图确认。

<details>
<summary>主控板接口位置：原图</summary>

![主控板接口位置与编号，原始图片](/images/主控板接口1.png)

</details>

<details>
<summary>主控板接口说明：原图</summary>

![主控板参数与接口说明，原始图片](/images/主控板参数2.png)

</details>

<details>
<summary>主控板尺寸：原图</summary>

![主控板尺寸与安装孔标注，原始图片](/images/主控板尺寸.png)

</details>

## 动力、尺寸与接线图片 {#drive-and-wiring}

本次 BOM 使用 A12、12 V、1:30。参数表对应列标称：空载 **730 rpm**、额定 **380 rpm**、额定扭矩 **19.6 mN·m**、额定电流 ≤0.22 A、堵转电流 0.4 A。配 Ø34 mm 轮，额定点理论线速度为 `π × 0.034 × 380 / 60 ≈ 0.68 m/s`，不是带车实测速度或控制限速。

接线图标 AB 双相霍尔、基础 **3 PPR**、3.3/5 V 供电、ZH1.5-6PIN；不能沿用其他编码器的 7 PPR。表格“减速后编码线数”的计数口径与实际减速齿数需核对，不直接把标称 1:30 乘成唯一正确计数。

| 线色（图片标注） | 电机端信号 | 与板端连接时的核对方式 |
| --- | --- | --- |
| 红 | 电机电源 +（M1） | 接实际驱动输出，架空确认正转方向。 |
| 绿 | 电机电源 −（M2） | 接另一驱动输出，不能当作编码器 GND。 |
| 蓝 | 霍尔 VCC | 接线图标 VCC；尺寸图 PIN5 文字误写/冲突为 GND，先核对实物，不按错误标签接线。 |
| 黑 | 霍尔 GND | 与控制板编码器地共地。 |
| 黄 | C1 / A 相 | 核对 A/B 相、方向与输入电平。 |
| 白 | C2 / B 相 | 核对 A/B 相、方向与输入电平。 |

线色只转录当前原图；实际线束可能变化。板端和电机端插头名称、针序、观察方向需逐项核验，不能按颜色或壳体方向直接对插。

<details>
<summary>电机性能参数：原图</summary>

![A12 电机不同电压及减速比的参数表，原始图片](/images/电机参数.png)

</details>

<details>
<summary>电机尺寸与插针：原图</summary>

![电机尺寸、ZH1.5-6PIN 接口与含冲突标注的针脚表，原始图片](/images/电机尺寸.png)

</details>

<details>
<summary>电机接线与编码器：原图</summary>

![电机六线颜色及 AB 霍尔编码器参数，原始图片](/images/电机接线.png)

</details>

<details>
<summary>电机支架尺寸：原图</summary>

![电机支架外形和约 18.5 mm 安装孔距，原始图片](/images/电机支架.png)

</details>

<details>
<summary>驱动轮尺寸：原图</summary>

![橡胶轮直径 34 mm、厚度 6.5 mm 与 3 mm D 轴孔，原始图片](/images/轮子尺寸.png)

</details>

<details>
<summary>CY-12B 万向轮尺寸与参数：原图</summary>

![CY-12B 尼龙主球、尺寸与供应商载荷表，原始图片](/images/万向轮参数.png)

</details>

## 电池与充电资料 {#battery-and-charging}

本次选项为 **102050×3S-1200 mAh**。现有图片是商家的通用电池参数，不是该组合的专用外形、接口或充电规范。图中写标准充电 0.1C、最大充电 0.5C（另有带条件的 0.2C），不能据此确认 1 A 充电器适配：对 1200 mAh，0.5C 为 0.6 A，1 A 约 0.83C，需取得所选成组电池的明确规格。3S 满充约 12.6 V，核对电芯/保护板、主接口、转换头与均衡/保护方式。

<details>
<summary>电池通用技术参数：原图</summary>

![电池商家通用参数，非本次 3S 组合的专用规格，原始图片](/images/电池.png)

</details>

## 相机参数与订购备注 {#camera-parameters}

本次选择 **H200S-60帧-3mm(110度无畸变)**，另备注 **1/4 螺孔、5 m 线，加 ¥20**。原图的默认线长是 1.5 m，因此保存原图时保留这一差异，5 m 定制长度以商家确认和到货实物为准。

原图写 1920×1080、USB2.0 High Speed、UVC、5 V、约 150–200 mA；帧率表中 1080p 60 fps 对应 **MJPG**，YUY2 在 1080p 下标为 5 fps。不能把“60帧”理解为任意格式都可达到 60 fps。镜头“110度无畸变”保留为商品选项，实测畸变、视场和 5 m 线下的持续采集稳定性仍需验证。

<details>
<summary>H200S 产品参数与帧率表：原图</summary>

![H200S 1080p 参数、MJPG 与 YUY2 帧率以及原默认 1.5 m 线，原始图片](/images/摄像头参数.png)

</details>

软件读回的设备参数与调节说明见 [H200S 相机参考参数](./h200s-camera)，场地安装见[场地与相机布置](./arena)。

## 原始图片保存与索引 {#image-archive}

11 张参数原图继续保存在 `docs/public/images/`，沿用原始中文文件名和文件内容。[图片索引 JSON](/images/hardware-parameters.json) 记录文件名、对应 BOM、用户提供的来源商品链接、像素尺寸、文件大小和 SHA-256。2026-11-15 是本次整理日期，原截图时间未提供；商品链接是来源定位线索，不表示已经独立核验商家的所有描述。

| 顺序 | 原始文件 | 对应物料 / 内容 |
| --- | --- | --- |
| 1 | [主控板接口1.png](/images/主控板接口1.png) | B01；接口位置与编号 |
| 2 | [主控板参数2.png](/images/主控板参数2.png) | B01；芯片与接口说明 |
| 3 | [主控板尺寸.png](/images/主控板尺寸.png) | B01；板外廓与安装孔 |
| 4 | [电机参数.png](/images/电机参数.png) | B02；12 V A12、1:30 等性能 |
| 5 | [电机尺寸.png](/images/电机尺寸.png) | B02；外形与针脚表 |
| 6 | [电机接线.png](/images/电机接线.png) | B02；六线信号及 3 PPR 霍尔参数 |
| 7 | [电机支架.png](/images/电机支架.png) | B02；原配支架尺寸 |
| 8 | [轮子尺寸.png](/images/轮子尺寸.png) | B05；34 mm 驱动轮 |
| 9 | [万向轮参数.png](/images/万向轮参数.png) | B06；CY-12B |
| 10 | [电池.png](/images/电池.png) | B03/B04；电池通用技术参数 |
| 11 | [摄像头参数.png](/images/摄像头参数.png) | B11；H200S 与帧率表 |

图片由用户提供，图内商家/品牌标识保留；原始内容权利归相应权利人。后续更新参数时另存新版本并更新索引，不用实测记录覆盖原始资料。

从仓库根目录运行 `python3 hardware_design/archive_hardware_docs.py` 可重建图片索引和加工下载副本；脚本校验复制内容一致，不改动原始图片或源图纸。
