# 当前紧凑车身的标签打印

- 完整8页：`../pdf/apriltag36h11_ground150_robot90_A4.pdf`
- 只补打4个车顶：`../pdf/apriltag36h11_robot90_4tags_A4.pdf`
- 地面ID0–3黑框150mm，含白边187.5mm；车顶ID10–13黑框90mm，含白边112.5mm，适配130mm顶板。

必须按100%/实际大小打印，禁用适应页面。尺量黑框及页底100mm标尺，保留完整白边。车身改变不要求换AprilTag编码或ID；只有物理标签尺寸改变才需要改打印尺寸。地面与车顶允许不同边长，不需要为了统一而缩小地面标签。

现有视觉配置未改。真正换上90mm车顶标签时，将对应size_m改为0.09，填实测标签高度、航向和控制点偏移，再验证定位；不要用新版标签配旧尺寸做真实控制。场地标签大小仍为0.15。

`manifest.json`记录编码来源和尺寸，`pdf_geometry_check.json`验证8页黑框的矢量几何。PDF已渲染检查；这不替代打印后尺量和相机远端识别测试。

从项目根目录重新生成（默认采用当前150/90mm组合）：

```sh
python3 generate_apriltags.py
python3 generate_apriltags.py --fixed-ids --output-dir output/apriltags_robot90 --pdf output/pdf/apriltag36h11_robot90_4tags_A4.pdf
```

旧 120 mm 图案仅作为合成检测测试素材保留在 output/apriltags/；本仓物理打印入口统一使用本页的 150/90 mm PDF。
