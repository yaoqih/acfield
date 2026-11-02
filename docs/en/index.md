---
layout: home
title: An Open Multi-Robot Testbed
hero:
  name: ACField
  text: Bring collaborative control into real experiments.
  tagline: An open multi-robot platform for multi-agent control research. Connect localization, decisions and execution, with evidence at every step.
  image:
    src: /images/field.svg
    alt: Conceptual four-robot arena
  actions:
    - theme: brand
      text: Get started →
      link: /en/guide/quickstart
    - theme: alt
      text: Explore the design
      link: /en/design/philosophy
features:
  - title: Start with a working system
    details: A hardware-free demo, web console and shared state interface help you understand the control path before adding your own algorithms.
    link: /en/guide/quickstart
    linkText: Run your first example
  - title: Make experiment conditions explicit
    details: Describe observations, actions, data age, ownership and protective intervention so execution effects remain visible in your results.
    link: /en/design/research
    linkText: Understand research boundaries
  - title: Keep a practical path to hardware
    details: Open ESP32 firmware, editable mechanical designs, printable tags and calibration guides connect nominal designs to physical measurements.
    link: /en/hardware/overview
    linkText: Explore reference hardware
---

<div class="home-body">
  <div class="home-eyebrow">ONE FIELD · MANY AGENTS</div>
  <h2 class="home-heading">An experiment path you can inspect.</h2>
  <p class="home-lead">ACField organizes shared infrastructure into an understandable system. Researchers develop collaborative policies; the platform handles state, execution, fault stops and basic recording.</p>
  <div class="pipeline">
    <article><span>01 / OBSERVE</span><h3>Locate the robots</h3><p>A fixed camera and AprilTags establish shared world coordinates while preserving source information and data age.</p></article>
    <article><span>02 / DECIDE</span><h3>Connect a policy</h3><p>Read state and submit joint actions through a common interface. Choose the algorithms and training tools that fit your research.</p></article>
    <article><span>03 / EXECUTE</span><h3>Execute and report</h3><p>The server validates actions; each robot controls wheel speed with explicit arming and finite command lifetimes.</p></article>
    <article><span>04 / UNDERSTAND</span><h3>Explain each run</h3><p>Relate actions, telemetry and stop reasons to diagnose failures and support later evaluation.</p></article>
  </div>
  <section class="home-split">
    <div><div class="home-eyebrow">DESIGN WITH INTENT</div><h2 class="home-heading">Start small. Take the physical world seriously.</h2><p class="home-lead">Four differential-drive robots form the reference setup. External localization, lightweight transport and one state owner keep coordinates, timing and failures inspectable. Every choice has a cost and conditions for reconsideration.</p><a class="home-link" href="./design/decisions">Read the design decisions →</a></div>
    <img src="/images/assembly.png" alt="V11 CAD assembly preview, not a physical prototype photograph" loading="lazy" />
  </section>
  <section class="home-split">
    <img src="/images/console.png" alt="ACField local multi-robot control console" loading="lazy" />
    <div><div class="home-eyebrow">A SHARED STARTING POINT</div><h2 class="home-heading">Make the next laboratory's first steps easier.</h2><p class="home-lead">The guides follow the setup process from software demo to calibration and multi-robot control. Maintain the shared platform while paper-specific experiments pin a version, giving new work a clear starting point.</p><a class="home-link" href="./guide/overview">Discover the platform →</a></div>
  </section>
  <aside class="home-status"><strong>DEVELOPMENT PREVIEW</strong><p>Working software and a reference hardware design are available. Assembly fit, physical performance and stopping distance still require measurement. The demo is not a validated training environment or physical simulator. <a href="./guide/status">See capabilities and evidence</a>.</p></aside>
  <div class="home-lab"><div><b>AClab</b><p>Algorithms and Collaboration Lab<br />Open tools for studying how agents act together.</p></div><a href="https://github.com/yaoqih/acfield">Contribute on GitHub ↗</a></div>
</div>
