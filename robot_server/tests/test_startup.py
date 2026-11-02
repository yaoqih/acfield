from backend import startup


def test_startup_distinguishes_detected_ip_from_a_lan_listener(monkeypatch):
    monkeypatch.setattr(startup, "host_ipv4s", lambda: ["192.168.1.42", "10.0.0.2"])
    local = startup.startup_summary("127.0.0.1", 8017, "demo")
    assert "http://127.0.0.1:8017/docs" in local
    assert "192.168.1.42" in local and "Local access only" in local
    assert "http://192.168.1.42" not in local
    lan = startup.startup_summary("0.0.0.0", 8017, "hardware")
    assert "http://192.168.1.42:8017" in lan
    assert "http://10.0.0.2:8017" in lan
    assert "http://0.0.0.0" not in lan


def test_startup_still_works_without_ipv4_route(monkeypatch):
    monkeypatch.setattr(startup, "host_ipv4s", lambda: [])
    output = startup.startup_summary("::1", 8000, "demo")
    assert "http://[::1]:8000/docs" in output
    assert "not detected" in output
