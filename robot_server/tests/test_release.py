from fastapi.testclient import TestClient

from backend.app import create_app


def test_release_checks_owner_and_is_idempotent(tmp_path):
    with TestClient(create_app(mode="demo", db_path=tmp_path / "config.db")) as client:
        path = "/api/robots/car-01"
        assert client.post(path + "/release").status_code == 422
        client.post(path + "/arm", json={"enabled": True}, headers={"X-Control-ID": "new"})
        before = client.app.state.fleet.robot("car-01").seq
        response = client.post(path + "/release", headers={"X-Control-ID": "old"})
        assert response.json() == {"released": False}
        robot = client.app.state.fleet.robot("car-01")
        assert robot.armed and robot.owner == "new" and robot.seq == before
        assert client.post(path + "/release", headers={"X-Control-ID": "new"}).json() == {"released": True}
        assert not robot.armed and robot.owner is None and robot.target_v == 0
        assert client.post(path + "/release", headers={"X-Control-ID": "new"}).json() == {"released": False}
        assert client.post("/api/robots/missing/release", headers={"X-Control-ID": "new"}).status_code == 404
