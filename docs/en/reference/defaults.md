# Current Defaults

This table is generated from normal firmware `config.h` and server configuration. Check the saved database and installed firmware separately when using an existing setup.

## Parameters {#parameters}

<!--@include: ../../.vitepress/generated/defaults.en.md-->

Firmware wheel-speed and linear-speed limits match. Wheel targets scale together when either exceeds its limit. See the [protocol](./protocol) for execution rules and [encoder diagnostics](../guide/troubleshooting#encoder-diagnostics) for the independent PWM mapping.

## Update and check {#update-and-check}

Run from the repository root with a host C++ compiler and the shared Python environment.

```bash
uv run --frozen --python 3.12 python tools/documentation_defaults.py
uv run --frozen --python 3.12 python tools/documentation_defaults.py --check
```

After configuration changes, regenerate the table and update supported combinations in [compatibility and upgrades](../guide/upgrading).
