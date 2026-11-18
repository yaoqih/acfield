# 当前默认参数

本表从普通固件 `config.h` 和主控配置生成。它描述当前仓库，已保存的数据库与板上固件需分别核对。

## 参数表 {#parameters}

<!--@include: ../.vitepress/generated/defaults.zh.md-->

固件轮速上限与线速度上限相同；左右轮超限时等比例缩放。完整执行规则见[设备协议](./protocol)。诊断固件使用独立的 PWM 映射，见[编码器排查](../guide/troubleshooting#encoder-diagnostics)。

## 更新与检查 {#update-and-check}

在仓库根目录运行，需要主机 C++ 编译器和共享 Python 环境。

```bash
uv run --frozen --python 3.12 python tools/documentation_defaults.py
uv run --frozen --python 3.12 python tools/documentation_defaults.py --check
```

修改配置后重建表格，同时更新[兼容与升级](../guide/upgrading)中的适用组合。
