import httpx
import pytest
from pydantic import ValidationError

from acfield import (APIError, Client, ProtocolError, TransportError, Velocity)


def test_typed_snapshot_and_forward_compatible_fields(server, transport):
    with Client(transport=transport) as client:
        assert client.health().status == "ok"
        state = client.state()
        robot = state.robot("car-01")
        assert robot.id == "car-01"
        assert robot.config.max_v == .1
        assert robot.x is not None
        assert robot.model_dump()["voltage_v"] is None
        assert robot.trail  # Additional server fields are preserved.
        assert client.config()["robots"][0]["id"] == robot.id
        with pytest.raises(KeyError):
            state.robot("missing")


def test_explicit_arm_motion_receipts_release_and_global_stop(transport):
    with Client(transport=transport) as client:
        assert client.arm("car-01").armed
        receipt = client.command("car-01", v=.5, omega=0)
        assert receipt.v == .1  # Applied limit, not the requested velocity.
        assert receipt.robot_id == "car-01"
        assert client.release("car-01").released
        assert not client.release("car-01").released  # Idempotent cleanup.
        client.arm("car-02")
        assert not client.disarm("car-02").armed
        assert client.stop_all().estop
        assert not client.reset_stop().estop
        assert not client.state().robot("car-01").armed


def test_control_ids_are_unique_and_headers_stable(server):
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(200, json={"estop": True})

    with Client(transport=httpx.MockTransport(reply)) as first, Client() as second:
        assert first.control_id != second.control_id
        first.stop_all()
        first.stop_all()
        assert {r.headers["X-Control-ID"] for r in requests} == {first.control_id}


@pytest.mark.parametrize("values", [
    {"v": float("nan"), "omega": 0},
    {"v": 0, "omega": float("inf")},
    {"v": 1.01, "omega": 0},
    {"v": 0, "omega": 6.01},
    {"v": 0, "omega": 0, "ttl_ms": 99},
    {"v": 0, "omega": 0, "ttl_ms": 501},
    {"v": 0, "omega": 0, "ttl_ms": 300.5},
])
def test_velocity_rejects_invalid_values_before_network(values):
    def unexpected(request):
        pytest.fail("Invalid commands must not reach the network")

    with Client(transport=httpx.MockTransport(unexpected)) as client:
        with pytest.raises(ValidationError):
            client.command("car-01", **values)


@pytest.mark.parametrize("options", [
    {"timeout": 0}, {"timeout": float("nan")},
    {"url": "ftp://localhost"}, {"url": "http://localhost/?token=x"},
    {"control_id": ""}, {"control_id": "a\nb"}, {"control_id": "车"},
])
def test_client_options_validate(options):
    with pytest.raises(ValueError):
        Client(**options)


def test_joint_actions_and_ids_validate_locally(transport):
    with Client(transport=transport) as client:
        for actions in ({}, {str(i): Velocity(v=0, omega=0) for i in range(17)}):
            with pytest.raises(ValueError):
                client.commands(actions)
        with pytest.raises(ValueError):
            client.arm("../stop")
        with pytest.raises(TypeError):
            client.commands({"car-01": {"v": 0, "omega": 0}})


def test_api_errors_preserve_status_and_detail(transport):
    with Client(transport=transport) as client:
        with pytest.raises(APIError) as failure:
            client.command("car-01", v=.05, omega=0)
        assert failure.value.status_code == 409
        assert "解锁" in failure.value.detail
        with pytest.raises(APIError) as failure:
            client.arm("missing")
        assert failure.value.status_code == 404


def test_degraded_health_is_inspectable(server):
    health = server.get("/api/health").json()
    health.update(status="degraded", ready=False, fault="control: RuntimeError")
    with Client(transport=httpx.MockTransport(lambda r: httpx.Response(503, json=health))) as client:
        assert client.health().fault == "control: RuntimeError"


def test_transport_failure_is_not_retried():
    calls = []

    def timeout(request):
        calls.append(request)
        raise httpx.ReadTimeout("outcome unknown", request=request)

    with Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(TransportError):
            client.command("car-01", v=.05, omega=0)
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="not JSON"), httpx.Response(200, json={}),
])
def test_malformed_success_raises_protocol_error(response):
    with Client(transport=httpx.MockTransport(lambda r: response)) as client:
        with pytest.raises(ProtocolError):
            client.state()


def test_non_json_error_and_mismatched_joint_receipts(transport):
    with Client(transport=httpx.MockTransport(lambda r: httpx.Response(502, text="gateway down"))) as client:
        with pytest.raises(APIError) as failure:
            client.state()
        assert failure.value.status_code == 502
        assert failure.value.detail == "gateway down"
    with Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))) as client:
        with pytest.raises(ProtocolError):
            client.commands({"car-01": Velocity(v=0, omega=0)})


def test_client_close_does_not_implicitly_release_ownership(transport, server):
    with Client(transport=transport) as client:
        client.arm("car-01")
    assert server.get("/api/state").json()["robots"][0]["armed"]
