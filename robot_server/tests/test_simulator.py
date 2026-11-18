import math

import pytest

from backend.models import default_settings
from backend.simulator import Simulator
from backend.state import Fleet


@pytest.mark.parametrize("v, omega", [(.5, 0), (-.5, 0), (0, 6), (.5, 6), (-.5, -6), (.5, 1e-8)])
def test_demo_integrates_constant_velocity_arcs(v, omega):
    fleet = Fleet(default_settings(), "demo")
    simulator = Simulator(fleet)
    robot = fleet.robot("car-01")
    x, y, theta = robot.x, robot.y, robot.theta
    robot.target_v, robot.target_omega = v, omega
    began = simulator.previous
    for step in range(1, 41):
        simulator.step(began+step*.025)
    if abs(omega) < 1e-6:
        expected_x, expected_y = x+v*math.cos(theta), y+v*math.sin(theta)
    else:
        expected_x = x+v/omega*(math.sin(theta+omega)-math.sin(theta))
        expected_y = y-v/omega*(math.cos(theta+omega)-math.cos(theta))
    assert robot.x == pytest.approx(expected_x, abs=1e-8)
    assert robot.y == pytest.approx(expected_y, abs=1e-8)
    assert robot.theta == pytest.approx(math.atan2(math.sin(theta+omega), math.cos(theta+omega)))
    assert (robot.measured_v, robot.measured_omega) == (v, omega)


def test_demo_boundary_uses_body_offset_and_reports_stopped_feedback():
    fleet = Fleet(default_settings(), "demo")
    simulator = Simulator(fleet)
    robot = fleet.robot("car-01")
    robot.config.body_offset_x = .2
    robot.x, robot.y, robot.theta = .35, 1, math.pi
    robot.target_v, robot.target_omega = .5, 1
    simulator.step(simulator.previous+.1)
    assert (robot.x, robot.y, robot.theta) == (.35, 1, math.pi)
    assert (robot.measured_v, robot.measured_omega) == (0, 0)
    assert not robot.armed and "边界" in robot.reason


def test_demo_caps_integration_after_a_long_pause():
    fleet = Fleet(default_settings(), "demo")
    simulator = Simulator(fleet)
    robot = fleet.robot("car-01")
    x = robot.x
    robot.target_v = .5
    simulator.step(simulator.previous+2)
    assert robot.x == pytest.approx(x+.05)
