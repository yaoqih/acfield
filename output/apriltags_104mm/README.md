# 整面车顶标签 / Full-cover labels

当前 V11 顶盖为 130 × 130 mm。车顶标签 ID 10–13 的黑框为 104 × 104 mm，四周各有 13 mm 完整白边，外尺寸正好是 130 × 130 mm。不做螺丝避让，不开缺口。地面 ID 0–3 保持 150 mm 黑框、187.5 mm 外尺寸。

- [完整 8 页 A4 PDF](../pdf/apriltag36h11_ground150_robot104_A4.pdf)
- [仅车顶 4 页 A4 PDF](../pdf/apriltag36h11_robot104_4tags_A4.pdf)
- [ID 10 预览](tag36h11_id010_robot.png)

ID 与 FRONT/箭头均在黑色边框内部，使用接近黑底的深灰色 #303030。车顶 ID 字号约 5.7 pt；不改编码单元、黑框边缘或白色静区。箭头指向图案标准上边，贴装时对准车体 +X 前方。正常安装的视觉 heading_offset_deg=0。裁切标记全部位于白边外，打印后保留完整白边。

按 100% / 实际大小打印，禁用适应纸张，先测页底 100 mm 标尺和黑框边长。相机配置 size_m=0.104 指黑框，不是 0.130；名义标签高度 height_m=0.0646 需装车后实测。已有本地视觉与服务器配置需分别核对。

从仓库根目录再生：

```sh
python -m pip install -r requirements-print.txt
python generate_apriltags.py --robot-pdf output/pdf/apriltag36h11_robot104_4tags_A4.pdf
# 另需 requirements-apriltag.txt 与 Poppler 的 pdftoppm
python verify_apriltags.py --write-reports
```

manifest.json 记录官方源图哈希、尺寸、页码与标注约定。pdf_geometry_check.json 核对两份 PDF 共 12 页的矢量尺寸。detection_check.json 记录两后端共 408 次数字检测：多尺度、四方向、透视和模糊，以及 Poppler 实际栅格化的 PDF。检测朝向与标准图案一致；原生后端的 Hamming 为 0，OpenCV 不提供该指标。

图稿检查不等于实物验收；贴装后需检查全场识别，尤其是螺丝处的纸面起伏、阴影和反光。PNG 无保证的物理打印尺寸，请打印矢量 PDF。旧 90 mm 打印文件保留为历史备选，120 mm 合成素材保持不变。

The current robot label fills the entire 130 mm cover without screw cutouts. Its black detection square is 104 mm, with a full 13 mm white margin on each side. Subtle dark-gray ID/FRONT marks sit inside the black ring. Align FRONT with chassis +X. Print the vector A4 PDFs at actual size and use 0.104 m as tag size. Digital checks cover both detection backends and rasterized PDFs; verify printed labels under the real arena camera.
