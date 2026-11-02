# Design philosophy

ACField starts with a practical question: when a researcher wants to try a multi-agent control idea on a few physical robots, which repeated engineering tasks can shared infrastructure handle, and which experimental conditions must the researcher define?

The goal is an inspectable path connecting pose, action, execution feedback and failure behavior. The platform is useful when others can understand it, build it and judge what its experiments demonstrate.

## Make the experiment path understandable {#make-the-experiment-path-understandable}

An action passes through observation, computation, validation, communication and motor execution. Delay, coordinate mistakes or protective intervention at any stage can change the outcome. Preserve action sources, data freshness, execution acknowledgments and stop reasons wherever possible.

An HTTP success, a device acknowledgment and measured physical motion are different facts. Observing each helps distinguish policy problems, tracking errors and infrastructure failures. That distinction supports more useful conclusions than a success rate alone.

## Establish a small working control loop {#establish-a-small-working-control-loop}

The reference system uses external vision, one state service and device-side wheel-speed control. Four low-speed differential-drive robots keep localization, communication and geometry understandable and allow maintainers to inspect a complete path.

Before adding middleware, distributed computation or elaborate simulation, identify the experimental bottleneck. New capabilities should have measurements, an expected improvement and a verification method. Simplicity is a choice for the current problem; evidence should guide architectural change.

## Separate platform mechanisms from research variables {#separate-platform-mechanisms-from-research-variables}

Explicit arming, command expiry and disconnect stops are platform mechanisms. Visible neighbors, message budgets and pursuit termination are research variables. Mixing them makes results harder to interpret and the platform harder to reuse.

Protection may use global state while a constrained agent must receive only the information permitted by the experiment. Record when protection modifies policy actions before discussing the method's own collaboration or collision avoidance.

## Respect differential-drive constraints {#respect-differential-drive-constraints}

An ideal planar agent may change direction instantly. A robot must turn and accelerate, with backlash, rolling resistance, slip and localization error. The interface uses linear and angular velocity with explicit metres, seconds, radians and a defined control point.

Algorithms producing planar vectors or goal points need an explicit differential-drive tracker and reported tracking error. If simulation omits important dynamics, measure them or narrow the claims before moving to hardware.

## Treat failures as normal experiment conditions {#treat-failures-as-normal-experiment-conditions}

Tags become occluded, Wi-Fi drops packets, policies time out and devices reboot. The system should converge to understandable states: stop, disarm, record the reason, and wait for explicit arming after recovery. Restoring a link does not restore motion.

Protection thresholds depend on measured stopping distances and errors. Conservative initial values support integration; their adequacy still depends on the actual arena and hardware.

## Maintain the platform beyond one project {#maintain-the-platform-beyond-one-project}

The platform maintains common interfaces, reference hardware and small examples. Paper repositories preserve methods, models and frozen experiment settings. One main repository supports cross-component protocol review and a single issue entry point.

Documentation, measurements and reproduction reports are valuable contributions. A setup problem from another laboratory can expose assumptions hidden in the maintainer's environment. Writing them down makes reuse easier over time.

## Grow commitments with evidence {#grow-commitments-with-evidence}

Distinguish implemented code, passing software checks and completed physical measurements. Releases should state supported combinations and compatibility; citations should identify a revision. Credibility comes from clear boundaries, accessible evidence and traceable changes.
