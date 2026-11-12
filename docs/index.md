---
layout: home
title: 开放式多机器人实验平台
hero:
  name: ACField
  text: 让协作算法，走进真实实验。
  tagline: 面向多智能体控制研究的开放式小型多机器人平台。连接定位、控制与执行，让每一步实验都有迹可循。
  image:
    src: /images/field.svg
    alt: ACField 四车协作场地示意图
  actions:
    - theme: brand
      text: 开始运行 →
      link: /guide/quickstart
    - theme: alt
      text: 理解设计理念
      link: /design/philosophy
features:
  - title: 从一个可运行的系统开始
    details: 无硬件演示、Web 控制台与统一状态接口，先理解控制链路，再接入自己的算法。
    link: /guide/quickstart
    linkText: 运行第一个例子
  - title: 把实验条件说清楚
    details: 明确观测、动作、数据龄、控制权和保护干预，区分算法表现与执行链路的影响。
    link: /design/research
    linkText: 阅读研究边界
  - title: 保留通向实物的细节
    details: 开放 ESP32 固件、参考机械源文件、标签与标定流程，记录从名义设计走向实测的过程。
    link: /hardware/overview
    linkText: 了解参考硬件
---

<div class="home-body">
  <div class="home-eyebrow">ONE FIELD · MANY AGENTS</div>
  <h2 class="home-heading">一套清楚、可检查的实验链路。</h2>
  <p class="home-lead">ACField 把公共基础设施组织成一个容易理解的系统。研究者专注于协作策略，平台负责状态汇聚、动作执行、失效停车与基本记录。</p>
  <div class="pipeline">
    <article><span>01 / OBSERVE</span><h3>看见场地</h3><p>固定相机与 AprilTag，建立共享世界坐标，保留定位来源和数据龄。</p></article>
    <article><span>02 / DECIDE</span><h3>接入策略</h3><p>通过统一接口获取状态、提交多车动作。算法与训练框架由研究者选择。</p></article>
    <article><span>03 / EXECUTE</span><h3>执行与反馈</h3><p>主控检查动作，车端执行电机输出并回传编码器数据，以有限有效期和自动控制握手管理运动。</p></article>
    <article><span>04 / UNDERSTAND</span><h3>解释每次运行</h3><p>关联动作、遥测和停车原因，为排查、复盘与后续评测保留依据。</p></article>
  </div>
  <section class="home-split">
    <div><div class="home-eyebrow">DESIGN WITH INTENT</div><h2 class="home-heading">小规模起步，认真对待真实世界。</h2><p class="home-lead">以四台差速小车作为参考配置。选择场外定位、轻量通信和单一状态管理者，让坐标、时序与故障行为更容易检查。每一个选择都有代价，也都有重新评估的条件。</p><a class="home-link" href="./design/decisions">查看设计取舍 →</a></div>
    <img src="/images/assembly.png" alt="V11 参考小车 CAD 装配预览，非实物照片" loading="lazy" />
  </section>
  <section class="home-split">
    <img src="/images/console.png" alt="ACField 本地多车控制台界面" loading="lazy" />
    <div><div class="home-eyebrow">A SHARED STARTING POINT</div><h2 class="home-heading">让下一个实验室，更容易开始。</h2><p class="home-lead">从软件演示到首车标定，再到多车控制，文档跟随真实搭建路径组织。基础平台持续维护，论文实验固定版本，让新的工作能够建立在清楚的共同起点上。</p><a class="home-link" href="./guide/overview">认识平台与使用路径 →</a></div>
  </section>
  <aside class="home-status"><strong>DEVELOPMENT PREVIEW</strong><p>当前提供可运行的软件链路与参考硬件设计。实车性能、装配适配和停止距离仍需测量；演示模式不承担训练环境或物理保真的承诺。<a href="./guide/status">查看能力与验证状态</a>。</p></aside>
  <div class="home-lab"><div><b>AClab</b><p>算法与协作实验室 · Algorithms and Collaboration Lab<br />Open tools for studying how agents act together.</p></div><a href="https://github.com/yaoqih/acfield">在 GitHub 上参与 ACField ↗</a></div>
</div>
