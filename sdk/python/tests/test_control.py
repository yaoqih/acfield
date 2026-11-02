import time

import httpx
import pytest

from acfield import (APIError, CleanupError, Client, ControlError, TransportError,
                     Velocity)
from conftest import forward


def test_joint_session_acquires_and_releases_only_selected_robots(server, transport):
    server.post("/api/robots/car-03/arm", json={"enabled": True},
                headers={"X-Control-ID": "other"})
    with Client(transport=transport) as client:
        with client.control("car-01", "car-02") as control:
            assert control.state().robot("car-01").control_owner == client.control_id
            receipt = control.commands({ident: Velocity(v=.05, omega=0) for ident in control.robots})
            assert set(receipt) == {"car-01", "car-02"}
            assert all(r.v == .05 for r in receipt.values())
            with pytest.raises(ValueError):
                control.command("car-03", v=0, omega=0)
        state = client.state()
        assert all(not state.robot(i).armed for i in control.robots)
        assert all(state.robot(i).control_owner is None for i in control.robots)
        assert state.robot("car-03").control_owner == "other"
        assert state.robot("car-03").armed
        with pytest.raises(ControlError):
            control.state()
        with pytest.raises(ControlError):
            with control:
                pass


def test_exception_and_keyboard_interrupt_release(server, transport):
    with Client(transport=transport) as client:
        for exception in (RuntimeError("policy failed"), KeyboardInterrupt()):
            with pytest.raises(type(exception)):
                with client.control("car-01") as control:
                    control.command("car-01", v=.05, omega=0)
                    raise exception
            robot = client.state().robot("car-01")
            assert not robot.armed and robot.target_v == 0


def test_overlapping_sessions_do_not_release_an_existing_session(transport):
    with Client(transport=transport) as client:
        with client.control("car-01") as outer:
            with pytest.raises(ControlError, match="separate Client"):
                with client.control("car-02"):
                    pass
            assert outer.state().robot("car-01").armed
        with client.control("car-02"):
            assert not client.state().robot("car-01").armed


def test_closed_client_cleanup_reports_failure_without_masking_exception(transport):
    client = Client(transport=transport)
    with pytest.warns(RuntimeWarning, match="Client is closed"):
        with pytest.raises(RuntimeError, match="policy"):
            with client.control("car-01"):
                client.close()
                raise RuntimeError("policy")


def test_session_does_not_reset_stop_or_take_existing_owner(server, transport):
    with Client(transport=transport) as client:
        client.stop_all()
        with pytest.raises(ControlError, match="Global stop"):
            with client.control("car-01"):
                pytest.fail("Global stop must remain active")
        assert client.state().estop
        client.reset_stop()
        server.post("/api/robots/car-01/arm", json={"enabled": True},
                    headers={"X-Control-ID": "rival"})
        with pytest.raises(ControlError, match="already"):
            with client.control("car-01"):
                pass
        assert client.state().robot("car-01").control_owner == "rival"


def test_partial_acquisition_rolls_back_without_stopping_rival(server):
    def handler(request):
        if request.url.path == "/api/robots/car-02/arm":
            server.post(request.url.path, json={"enabled": True},
                        headers={"X-Control-ID": "rival"})
        return forward(server, request)

    with Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(APIError):
            with client.control("car-01", "car-02"):
                pass
        assert not client.state().robot("car-01").armed
        assert client.state().robot("car-02").control_owner == "rival"


def test_timed_out_arm_is_conditionally_released_without_retry(server):
    arms = []

    def handler(request):
        response = forward(server, request)
        if request.url.path.endswith("/arm"):
            arms.append(request)
            raise httpx.ReadTimeout("response lost after acquisition", request=request)
        return response

    with Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(TransportError):
            with client.control("car-01"):
                pass
        assert not client.state().robot("car-01").armed
        assert len(arms) == 1


def test_exit_does_not_stop_new_owner(server, transport):
    with Client(transport=transport) as client:
        with client.control("car-01"):
            server.post("/api/robots/car-01/arm", json={"enabled": False})
            server.post("/api/robots/car-01/arm", json={"enabled": True},
                        headers={"X-Control-ID": "new-owner"})
        assert client.state().robot("car-01").control_owner == "new-owner"
        assert client.state().robot("car-01").armed


def test_server_restart_is_not_silently_resumed(server):
    changed = False

    def handler(request):
        response = forward(server, request)
        if changed and request.url.path == "/api/state":
            data = response.json()
            data["session"] = "new-session"
            return httpx.Response(200, json=data)
        return response

    with Client(transport=httpx.MockTransport(handler)) as client:
        with client.control("car-01") as control:
            changed = True
            with pytest.raises(ControlError, match="session changed"):
                control.command("car-01", v=.05, omega=0)


def test_slow_policy_does_not_receive_automatic_command_renewal(transport):
    with Client(transport=transport) as client:
        with client.control("car-01") as control:
            control.command("car-01", v=.05, omega=0, ttl_ms=100)
            time.sleep(.16)
            with pytest.raises(ControlError, match="lost arming"):
                control.command("car-01", v=.05, omega=0)
            assert not client.state().robot("car-01").armed


def pending_transport(server, *, finish_after=None):
    polls = []

    def handler(request):
        response = forward(server, request)
        if request.url.path == "/api/health":
            data = response.json()
            data["mode"] = "hardware"
            return httpx.Response(200, json=data)
        if request.url.path == "/api/state":
            data = response.json()
            data["mode"] = "hardware"
            robot = data["robots"][0]
            if robot["armed"]:
                polls.append(True)
                if finish_after is None or len(polls) < finish_after:
                    robot.update(armed=False, arm_pending=True)
            return httpx.Response(200, json=data)
        return response

    return httpx.MockTransport(handler), polls


def test_hardware_requires_explicit_opt_in(server):
    transport, polls = pending_transport(server)
    with Client(transport=transport) as client:
        with pytest.raises(ControlError, match="allow_hardware"):
            with client.control("car-01"):
                pass
        assert not polls


def test_hardware_session_waits_for_confirmation(server):
    transport, polls = pending_transport(server, finish_after=2)
    with Client(transport=transport) as client:
        with client.control("car-01", allow_hardware=True):
            assert len(polls) == 2


def test_arm_confirmation_timeout_cleans_up(server):
    transport, polls = pending_transport(server)
    with Client(transport=transport) as client:
        with pytest.raises(ControlError, match="Timed out"):
            with client.control("car-01", allow_hardware=True, arm_timeout=.01):
                pass
    assert polls
    assert not server.get("/api/state").json()["robots"][0]["armed"]


def test_cleanup_failure_is_visible_and_does_not_mask_policy_error(server):
    def handler(request):
        if request.url.path.endswith("/release"):
            raise httpx.ConnectError("server unreachable", request=request)
        return forward(server, request)

    with Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CleanupError):
            with client.control("car-01"):
                pass
        server.post("/api/robots/car-01/arm", json={"enabled": False})
        with pytest.warns(RuntimeWarning, match="release failed"):
            with pytest.raises(RuntimeError, match="policy") as failure:
                with client.control("car-01"):
                    raise RuntimeError("policy")
        assert "release failed" in failure.value.__notes__[0]


@pytest.mark.parametrize("robots,options", [
    ((), {}), (("car-01", "car-01"), {}),
    (("../stop",), {}), (("car-01",), {"arm_timeout": 0}),
])
def test_invalid_session_arguments(robots, options):
    with Client() as client:
        with pytest.raises(ValueError):
            client.control(*robots, **options)
