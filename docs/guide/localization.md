# 视觉定位与标定

定位服务由根目录 `apriltag_live.py` 和 `web/` 提供，独立于小车控制服务。它支持真实相机、视频回放与合成演示；只有符合来源与标定条件的相机数据能进入硬件控制链路。

## 先运行视觉演示 {#start-the-vision-demo}

在仓库根目录：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-apriltag.txt
.venv/bin/python apriltag_live.py --source demo
```

打开终端显示的地址，默认 **http://127.0.0.1:5050**。合成场景用于检查检测、标定和导出流程。它包含自己定义的 120 mm 标签与 120 mm 高度，不表示参考硬件尺寸，也不能驱动真实车辆。

## 物理标签 {#physical-tags}

公共设备布局与相机覆盖关系见[场地与相机布置](../hardware/arena)。

使用 `tag36h11`：地面 ID 0–3，车辆 ID 10–13。下载[完整 8 页 A4 打印文件](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_ground150_robot104_A4.pdf)，或[仅车顶 ID 10–13 的 4 页文件](https://github.com/yaoqih/acfield/blob/main/output/pdf/apriltag36h11_robot104_4tags_A4.pdf)。地面黑框仍为 150 mm，车顶黑框改为 104 mm。

检测尺寸指黑色外框，不包含白边。车顶黑框 **104 × 104 mm**，四周各保留 **13 mm** 白边，完整裁切尺寸正好是 **130 × 130 mm**。100% 实际大小打印，禁用适应纸张，尺量 PDF 中的 100 mm 标尺；沿白边外侧的裁切标记裁切。

### 车顶整面布局 {#full-cover-layout}

[![整面车顶标签 ID 10：白边内无文字，黑框内含低对比度 ID 和前向箭头](/images/robot-tag.png)](/images/robot-tag.png)

标签覆盖 130 mm 顶盖整面，不为螺丝缩小或开缺口。ID 使用约 5.7 pt 小字，前向箭头及 FRONT 放在另一侧黑框内部，颜色为接近黑底的深灰 `#303030`。编码单元、黑框边缘和白色静区保持完整。箭头朝图案的标准上边，安装时对准车体前方（+X）；视觉朝向采用同一边，正常安装的 `heading_offset_deg=0`。

当前公开视觉配置中，车辆 ID 10–13 的 `size_m=0.104`，名义 `height_m=0.0646`。实际贴纸高度仍需装车后测量；已有本地配置不会自动迁移。服务器的 `tag_size` 也应记录为 `0.104`。

数字图稿通过两种检测后端共 408 次检查，覆盖多尺度、四个旋转方向、透视与轻微模糊，以及 PDF 实际栅格化结果；同时核对了黑框尺寸与完整白边。这不代替贴装后在全场相机下的实测，尤其是螺丝处纸面起伏和反光。

从仓库根目录重新生成：

```bash
python -m pip install -r requirements-print.txt
python generate_apriltags.py --robot-pdf output/pdf/apriltag36h11_robot104_4tags_A4.pdf
# 检测还需 requirements-apriltag.txt 与 Poppler 的 pdftoppm
python verify_apriltags.py --write-reports
```

PNG 用于预览，打印请使用矢量 PDF。旧 90 mm 文件保留为历史备选，合成演示仍使用自己的 120 mm 素材与尺寸。

## 标定顺序 {#calibration-order}

1. 在固定焦距、焦点和分辨率下，使用外部相机标定工具获得内参与畸变参数，填入 `apriltag_live.json` 的 `camera`。
2. 测量地面标签在统一坐标系中的位置、黑框尺寸和朝向，填写配置并设置 `world.configured=true`。
3. 固定相机后，在界面发起场地外参标定。检查重投影误差，并用已知位置实测全场坐标误差。
4. 填写车顶标签真实尺寸、离地高度及朝向修正。V11 名义标签面高度约 64.6 mm，仅作设计参考。
5. 在主控配置标签相对驱动轴中点的偏移；验证直行时朝向正确，避免两端重复加同一安装角。
6. 覆盖标签、冻结相机和移动相机，检查数据过期与标定失效行为。

公开配置默认 `camera=null`、场地未配置；它不是某个实验室的已标定文件。`--source 0` 通常打开第一台相机；其他选项以 `--help` 为准。

## 接入主控的条件 {#hardware-integration-requirements}

硬件模式要求数据声明 `source_kind=camera`、`world_calibrated=true`、`tag36h11` 与 `demo=false`。适配器不把像素坐标当米，也不把重复帧当新定位。

已提供质量信息时，短边少于 35 px、解码裕量少于 30、非零 Hamming 或不合理的连续位置跳变会使定位无效。OpenCV 缺少某些质量指标时不会仅因缺字段拒绝。门限是初值，应结合场地像素、光照和误差实测修订。

定位超过 200 ms 失效。应同时检查源帧龄、检测龄与处理延迟；只看服务在线无法发现冻结画面。
