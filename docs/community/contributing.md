# 贡献与版本维护

ACField 欢迎中文和英文的问题、文档修正、复现报告与代码贡献。完整规则见 [CONTRIBUTING.md](https://github.com/yaoqih/acfield/blob/main/CONTRIBUTING.md)。

## 有价值的贡献 {#useful-contributions}

可复现的失败案例、其他系统上的安装修正、实车测量、坐标与标定解释、兼容性说明，都和代码功能一样重要。新功能请先说明它支持什么实验，以及如何检查其效果。

## 本地检查 {#local-checks}

```bash
# 仓库根目录
npm ci
npm run docs:build
npm --prefix robot_server/frontend ci
npm --prefix robot_server/frontend run build

# 后端
cd robot_server
uv sync --python 3.12 --extra test
uv run pytest -q
```

定位、固件和跨端依赖见[故障排查](../guide/troubleshooting)。CI 要求真实固件解析器测试实际执行。实车验证仍需物理测量，不能以绿色构建替代。

## 版本原则 {#version-principles}

开发预览阶段接口可能调整；兼容性变化应写入变更记录，修改协议时两端一起评审。使用者先固定提交，待形成发布节奏后再使用稳定标签。

建议每次发布保存：主控/固件版本、设备协议修订、参考硬件修订、配置与日志格式，以及已执行的软件和实物检查。当前未创建正式版本标签。

## 主仓与论文仓 {#platform-and-paper-repositories}

主仓维护公共平台及小型参考例子，论文仓维护方法、训练和冻结的实验。文档站源文件留在主仓，网站自动构建。用户不必跨多个仓库寻找一套匹配的基础系统。

## 维护连续性 {#maintenance-continuity}

当前 CODEOWNERS 指向仓库维护者。后续实验室接手时，应至少安排两位有权限的维护者，并按实际职责增加模块负责人。仓库可以转移到实验室组织，发布地址、网站配置和引用信息要一起更新。
