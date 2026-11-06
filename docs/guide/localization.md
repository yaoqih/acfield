# 视觉定位与标定

定位服务由根目录 `apriltag_live.py` 和 `web/` 提供，独立于小车控制服务。它支持真实相机、视频回放与合成演示；只有符合来源与标定条件的相机数据能进入硬件控制链路。

## 先运行视觉演示 {#start-the-vision-demo}

在仓库根目录：

```bash
uv sync --python 3.12 --extra test
uv run --python 3.12 python apriltag_live.py --source demo
```

打开终端显示的地址，默认 **http://127.0.0.1:8765**。合成场景用于检查检测、标定和导出流程。它包含自己定义的 120 mm 标签与 120 mm 高度，不表示参考硬件尺寸，也不能驱动真实车辆。

## 物理标签 {#physical-tags}

公共设备布局与相机覆盖关系见[场地与相机布置](../hardware/arena)。

95 mm 首件候选使用 `tag36h11`，车顶为 **72 mm 黑框、四周各 4 mm 白边、80 mm 成品**，不留出血。[12 张 PNG，ID 10–21](https://github.com/yaoqih/acfield/blob/main/hardware_design/acrylic_95/tag_images/tag36h11_80mm_white4_12ids_png.zip) 按 100% 实际大小打印，图案上边朝车头。安装孔和螺丝不得遮挡图案，4 mm 白边需在全场实测识别。使用新车时，以实测黑框边长更新视觉和控制台设置，名义 `size_m=0.072`；实测高度及控制点偏移。现有运行配置不会自动切换，ID 18–21 也需先配置。场地标签独立按实际尺寸配置。

以下为旧版 V11 标签资料：使用 `tag36h11`，场地 ID 0–3，小车 ID 10–17，均为 **104 mm 黑框、130 mm 含白边外尺寸**，不留出血。两份 PDF 按相同顺序包含全部 12 个 ID：

- [A4 打印版](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_A4.pdf)：每页一个标签，附尺寸、裁切标记和 100 mm 校验标尺。
- [130 × 130 mm 纯标签版](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_130mm_tag_only.pdf)：每页就是完整标签，无页眉、标尺、裁切标记或额外页面留白。

检测尺寸指黑色外框，不包含白边。黑框 **104 × 104 mm**，四周各保留 **13 mm** 白边，完整尺寸为 **130 × 130 mm**。纯标签版保留这圈检测必需的白色静区。两份文件都按 100% 实际大小打印，禁用适应纸张；A4 版可尺量 100 mm 标尺，沿白边外侧的标记裁切。

### V11 车顶整面布局 {#full-cover-layout}

[![整面车顶标签 ID 10：白边内无文字，黑框内含低对比度 ID 和前向箭头](/images/robot-tag.png)](/images/robot-tag.png)

标签覆盖 130 mm 顶盖整面，不为螺丝缩小或开缺口。ID 使用约 5.7 pt 小字，前向箭头及 FRONT 放在另一侧黑框内部，颜色为接近黑底的深灰 `#303030`。编码单元、黑框边缘和白色静区保持完整。箭头朝图案的标准上边，安装时对准车体前方（+X）；视觉朝向采用同一边，正常安装的 `heading_offset_deg=0`。

当前公开视觉配置仍采用 V11 初值：场地和小车标签 `size_m` 均为 `0.104`，小车 `height_m=0.0646`。ID 10–17 默认都是通用小车身份；编队、围堵、覆盖等角色由实验自行配置。新紧凑车请按上面的实测值配置，不要沿用 V11 数值；更换场地标签还需更新尺寸、实测坐标并重新标定。

数字图稿通过两种检测后端共 624 次检查，覆盖多尺度、四个旋转方向、透视与轻微模糊，以及两份 PDF 共 24 页的实际栅格化结果；同时核对黑框尺寸、页面尺寸和完整白边。这不代替贴装后在全场相机下的实测，尤其是螺丝处纸面起伏和反光。

从仓库根目录重新生成：

```bash
uv run --python 3.12 python generate_apriltags.py
# 检测还需 Poppler 的 pdftoppm
uv run --python 3.12 python verify_apriltags.py --write-reports
```

也可只装打印所需依赖：`python -m pip install -r requirements-print.txt`。

两份 V11 PDF 是提交到仓库的发布文件。V11 逐张 PNG、生成清单和检查报告写入被忽略的 `output/apriltags/`；新紧凑版 PNG 与 ZIP 则保存在 `hardware_design/acrylic_95/tag_images/`。官方源图统一保留在 `assets/apriltags/`，供打印、演示和检测测试共用。合成演示仍使用独立定义的尺寸。紧凑版可运行 `uv run python hardware_design/acrylic_95/tag_images/generate.py` 重建并检查全部 12 张图片，数字检查不代替实拍识别。

## 标定顺序 {#calibration-order}

1. 在固定焦距、焦点和分辨率下，使用外部相机标定工具获得内参与畸变参数，填入 `apriltag_live.json` 的 `camera`。
2. 测量地面标签在统一坐标系中的位置、黑框尺寸和朝向，填写配置并设置 `world.configured=true`。
3. 固定相机后，在界面发起场地外参标定。检查重投影误差，并用已知位置实测全场坐标误差。
4. 填写车顶标签真实尺寸、离地高度及朝向修正。95 mm 候选名义高度约 59 mm，V11 约 64.6 mm，仅作设计参考。
5. 在主控配置标签相对驱动轴中点的偏移；验证直行时朝向正确，避免两端重复加同一安装角。
6. 覆盖标签、冻结相机和移动相机，检查数据过期与标定失效行为。

公开配置默认 `camera=null`、场地未配置；它不是某个实验室的已标定文件。`--source 0` 通常打开第一台相机；其他选项以 `--help` 为准。

## 接入主控的条件 {#hardware-integration-requirements}

硬件模式要求数据声明 `source_kind=camera`、`world_calibrated=true`、`tag36h11` 与 `demo=false`。适配器不把像素坐标当米，也不把重复帧当新定位。

已提供质量信息时，短边少于 35 px、解码裕量少于 30、非零 Hamming 或不合理的连续位置跳变会使定位无效。OpenCV 缺少某些质量指标时不会仅因缺字段拒绝。门限是初值，应结合场地像素、光照和误差实测修订。

定位超过 200 ms 失效。应同时检查源帧龄、检测龄与处理延迟；只看服务在线无法发现冻结画面。
