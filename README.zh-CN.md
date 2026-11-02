# ACField

**面向多智能体控制研究的开放式多机器人实验平台。** 由 **AClab 算法与协作实验室**开发和维护。

[文档网站](https://yaoqih.github.io/acfield/) · [English](README.md) · [设计理念](https://yaoqih.github.io/acfield/design/philosophy) · [能力与验证状态](https://yaoqih.github.io/acfield/guide/status)

ACField 把外部视觉定位、统一状态与速度接口、Web 控制台、车端轮速闭环和基本记录连接起来。以四台差速小车为参考配置，研究者可以接入自己的控制与协作策略。

> 当前是开发预览。软件检查、名义机械设计与实车测量分别标注；物理装配、标定、网络时延和停止距离仍需验证。演示模式用于接口调试，不是已验证的训练环境或 benchmark。

## 无硬件运行

需要 Python 3.11+（推荐 3.12）、Node.js 20.19+ 或 22.12+、Git；推荐使用 uv。

```bash
git clone https://github.com/yaoqih/acfield.git
cd acfield/robot_server
uv sync --extra test
npm --prefix frontend ci
npm --prefix frontend run build
./run.sh
```

打开 http://127.0.0.1:8000。点击小车、解锁并按住方向按钮。全局停止会锁定所有车，释放后需重新解锁。服务保持运行时，从仓库根目录执行：

```bash
uv pip install --python robot_server/.venv/bin/python -e ./sdk/python
robot_server/.venv/bin/python examples/velocity_control.py --duration 2
```

## 内容入口

| 内容 | 入口 |
| --- | --- |
| 开始使用、配置、算法接入 | [使用指南](https://yaoqih.github.io/acfield/guide/quickstart) |
| 独立安装的 Python 客户端、联合动作与控制会话 | [Python SDK](https://yaoqih.github.io/acfield/guide/python-sdk) |
| 设计理念、架构与选型取舍 | [设计文档](https://yaoqih.github.io/acfield/design/philosophy) |
| 观测、通信、保护干预与实验有效性 | [研究边界](https://yaoqih.github.io/acfield/design/research) |
| 固件与首车调试 | [固件说明](esp32_software/firmware/README.md) |
| V11 源文件、加工与名义检查 | [参考硬件](hardware_design/README.md) |
| 平台贡献、版本、引用与部署 | [共同维护](https://yaoqih.github.io/acfield/community/contributing) |

## 设计上的坚持

平台承担状态、动作校验、反馈、失效停车和基本记录；实验层定义策略、任务、观测与评价。保留请求动作、平台干预和实际执行的差别，让实验结果有依据。

主仓统一维护配套软硬件，论文仓固定依赖某个提交。单进程主控和轻量协议用于当前小规模低速参考场景；需要扩展时，根据测量与实际研究流程调整。

## 文档站

```bash
npm ci
npm run docs:dev
npm run docs:build
```

VitePress 提供搜索、深浅色和移动端导航。GitHub Actions 在 main 更新后自动部署到 GitHub Pages，PR 只构建检查。网站仅托管静态文档，不运行控制服务。

原创软件、文档和参考设计采用 [Apache-2.0](LICENSE)，第三方材料保留原许可。引用请记录实际使用的提交或版本，见 [CITATION.cff](CITATION.cff)。
