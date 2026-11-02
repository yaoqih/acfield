# Research validity

ACField provides shared infrastructure for physical systems. Multi-robot actions provide a research integration point; comparable multi-agent experiments also need a defined task and evidence chain.

## Research directions to explore {#research-directions-to-explore}

Low-speed formation, pursuit/evasion, cooperative arrival, coverage and assignment are possible future tasks. Pretrained policies can use the velocity API after adaptation to differential-drive motion, frequency, latency and stop rules. Actual performance requires measurement.

The external camera currently provides shared localization. Raw-image sharing, BEV fusion, collaborative SLAM and onboard autonomous perception need additional equipment or data paths; a four-robot motion demo does not establish these capabilities.

## Central infrastructure and decentralized policies {#central-infrastructure-and-decentralized-policies}

Agents may run on one computer or receive local observations from an adapter. Whether a policy is decentralized depends on available information and message rules, not whether processes are separate.

`/api/state` currently exposes global platform state with no observation isolation. Limited-communication experiments need observation/message adapters to prevent access to information outside the rules. Evaluation and stopping protection may retain global state, with explicit isolation from the policy.

Simulated logical message delay, loss and byte budgets are algorithm communication conditions. Computer-to-ESP32 UDP execution traffic is a separate link. Report them separately; logical communication experiments do not directly establish real V2V radio performance.

## Action and timing contract {#action-and-timing-contract}

The reference interface uses `v` and `omega` under differential-drive constraints:

```text
v_left  = v − omega × wheel_track / 2
v_right = v + omega × wheel_track / 2
```

Planar velocity vectors, goals and trajectories require an explicit tracker. Record inference time, observation age and action lifetime, reject stale results, and avoid continuously renewing old commands to hide blocked inference.

## Report protective intervention {#report-protective-intervention}

Distinguish policy requests, clamped/rejected actions, device acknowledgments and physical motion. If protection repeatedly prevents collisions, report both task performance and the protection layer's contribution.

Record success, failure and aborted runs separately. Device faults, localization loss or incomplete logs need predefined inclusion rules; do not simply delete unsuccessful runs.

## Minimum specification for a reproducible task {#minimum-specification-for-a-reproducible-task}

| Element | What to state |
| --- | --- |
| Task | Objective, participating robots, termination, maximum duration |
| Observations | Coordinates, local/global scope, age and noise |
| Actions | Units, frequency, limits, expiry and tracker |
| Initial conditions | Simulation seed or physical placement/tolerance |
| Versions | Platform revision, firmware, weights, calibration |
| Metrics | Success, time/error, intervention, communication and inference costs |
| Results | Every run, invalid/aborted reasons, statistical method |

Server logs cover part of the engineering path. The experiment layer must add episode IDs, agent observations, messages and task evaluation. Physical robots cannot reset as precisely as seeded simulation: record initial error and environmental variation, and estimate variability through repeated trials.
