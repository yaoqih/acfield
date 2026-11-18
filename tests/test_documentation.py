"""Exercise published examples and compare reference material with implementation."""
import json
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import sys
import time

import httpx
import pytest

from acfield import State
from backend.models import Command, Settings
from tools.documentation_defaults import read_firmware, render_defaults
from tools.documentation_samples import samples

ROOT = Path(__file__).resolve().parents[1]
NEW_PAGES = ["reference/state.md", "reference/coordinates.md", "reference/defaults.md",
             "guide/first-experiment.md", "guide/recording.md", "guide/manual-control.md",
             "guide/upgrading.md", "guide/diagnostic-case.md", "hardware/compatibility.md"]


def marked_blocks(path):
    text = path.read_text(encoding="utf-8")
    return dict(re.findall(r"<!-- docs-test: ([\w-]+) -->\s*```\w+\n(.*?)```", text, re.S))


def test_generated_defaults_match_implementation():
    firmware = read_firmware()
    for locale in ("zh", "en"):
        path = ROOT / f"docs/.vitepress/generated/defaults.{locale}.md"
        assert path.read_text(encoding="utf-8") == render_defaults(firmware, locale == "en")


def test_embedded_operating_parameters_match_firmware():
    firmware = read_firmware()
    for locale in ("", "en/"):
        for page in ("guide/configuration.md", "hardware/bringup.md", "guide/troubleshooting.md"):
            text = (ROOT / f"docs/{locale}{page}").read_text(encoding="utf-8")
            assert f"{firmware['max_v']:.2f} m/s" in text
            assert f"{firmware['max_omega']:.2f} rad/s" in text
        for page in ("hardware/bringup.md", "guide/troubleshooting.md"):
            text = (ROOT / f"docs/{locale}{page}").read_text(encoding="utf-8")
            assert firmware["version"] in text
            assert f"feedForward={firmware['feed_forward']}" in text
            assert f"kp={firmware['kp']}" in text
            assert f"ki={firmware['ki']}" in text


def test_state_samples_match_serializer_and_sdk():
    illustrations = samples()
    for name, expected in illustrations.items():
        actual = json.loads((ROOT / f"docs/public/examples/state-{name}.json").read_text(encoding="utf-8"))
        assert actual == expected
        assert State.model_validate(actual).robot("car-01").id == "car-01"
        for locale in ("", "en/"):
            dictionary = (ROOT / f"docs/{locale}reference/state.md").read_text(encoding="utf-8")
            for field in actual["robots"][0]:
                assert re.search(rf"\b{field}\b", dictionary), field
    fresh, stale = (illustrations[name]["robots"][0] for name in ("fresh", "stale"))
    assert fresh["online"] and fresh["visible"]
    assert not stale["online"] and not stale["visible"]
    assert stale["x"] == fresh["x"]
    assert stale["measured_v"] is None


@pytest.mark.parametrize("page", NEW_PAGES)
def test_bilingual_executable_snippets_and_json(page):
    zh, en = (ROOT / "docs" / prefix / page for prefix in ("", "en"))
    assert marked_blocks(zh) == marked_blocks(en)
    objects = []
    for path in (zh, en):
        blocks = re.findall(r"```json\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
        parsed = [json.loads(block) for block in blocks]
        for obj in parsed:
            if page == "reference/coordinates.md":
                Settings.model_validate(obj)
            if obj.get("kind") == "control":
                for command in obj["data"]["requested"].values():
                    Command.model_validate(command)
                obj["data"].pop("reason", None)
        objects.append(parsed)
    assert objects[0] == objects[1]


@pytest.mark.parametrize("page", ["reference/state.md", "reference/coordinates.md",
                                 "hardware/compatibility.md", "hardware/bringup.md",
                                 "guide/localization.md"])
def test_bilingual_measurement_values(page):
    values = []
    for prefix in ("", "en"):
        text = (ROOT / "docs" / prefix / page).read_text(encoding="utf-8")
        text = re.sub(r"^\d+\. ", "", text, flags=re.M)
        values.append(set(re.findall(r"\d+(?:\.\d+)*", text)))
    assert values[0] == values[1]


@pytest.fixture
def demo_server(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "robot_server"),
           "ROBOT_MODE": "demo", "ROBOT_HOST": "127.0.0.1", "ROBOT_PORT": str(port),
           "ROBOT_DB": str(tmp_path / "config.sqlite3"), "ROBOT_LOG_DIR": str(tmp_path / "logs"),
           "ROBOT_NTP_SERVER": "", "ROBOT_DEFAULT_VISION_URL": "", "ROBOT_VISION_URL": "",
           "ROBOT_ALLOW_UNLOCALIZED_CONTROL": "0"}
    with (tmp_path / "server.txt").open("w") as output:
        process = subprocess.Popen([sys.executable, "-m", "backend.app"], cwd=ROOT,
                                   env=env, stdout=output, stderr=subprocess.STDOUT)
        url = f"http://127.0.0.1:{port}"
        try:
            with httpx.Client(base_url=url, timeout=1.) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        pytest.fail((tmp_path / "server.txt").read_text())
                    try:
                        if client.get("/api/health").json().get("ready"):
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(.05)
                else:
                    pytest.fail("Demo server did not become ready")
            yield url, tmp_path, process
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def test_documented_experiment_and_analysis(demo_server, tmp_path):
    url, server_path, process = demo_server
    snippets = marked_blocks(ROOT / "docs/guide/first-experiment.md")
    output = tmp_path / "experiment"
    command = shlex.split(snippets["experiment-command"].replace("\\\n", ""))[4:]
    command[command.index("--output") + 1] = str(output)
    result = subprocess.run([sys.executable, *command, "--url", url], cwd=ROOT,
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "Experiment completed" in result.stdout
    with httpx.Client(base_url=url) as client:
        state = client.get("/api/state").json()
        for robot in state["robots"][:2]:
            assert not robot["armed"] and robot["control_owner"] is None
            assert robot["target_v"] == robot["target_omega"] == 0
        snippet = marked_blocks(ROOT / "docs/reference/state.md")["state-reader"].replace(
            "http://127.0.0.1:8000", url)
        exec(compile(snippet, "reference/state.md", "exec"), {})
    process.send_signal(signal.SIGINT)
    assert process.wait(timeout=10) == 0
    analysis = shlex.split(snippets["analysis-command"])[4:]
    analysis[1] = str(output)
    result = subprocess.run([sys.executable, *analysis, "--logs", str(server_path / "logs")],
                            cwd=ROOT, text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "summary.json").read_text())
    assert summary["mode"] == "demo"
    assert summary["events"]["accepted_controls"] >= 10
    assert summary["events"]["rejected_controls"] == 0
    for metrics in summary["robots"].values():
        assert .07 < metrics["path_length_m"] < .13
        assert metrics["gaps_over_200ms"] == 0
    assert (output / "trajectories.png").stat().st_size > 1000


def test_aborted_experiment_and_output_collision(demo_server, tmp_path):
    url, _, _ = demo_server
    output = tmp_path / "aborted"
    with httpx.Client(base_url=url) as client:
        client.post("/api/stop").raise_for_status()
    command = [sys.executable, "examples/velocity_control.py", "--url", url,
               "--output", str(output)]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=15)
    assert result.returncode == 1
    manifest = json.loads((output / "experiment.json").read_text())
    assert manifest["result"] == "aborted" and manifest["error"]
    before = (output / "experiment.json").read_bytes()
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=15)
    assert result.returncode == 1
    assert "Choose a new output directory" in result.stderr
    assert before == (output / "experiment.json").read_bytes()


def test_interruption_stops_robots_and_saves_aborted_manifest(demo_server, tmp_path):
    url, _, _ = demo_server
    output = tmp_path / "interrupted"
    command = [sys.executable, "examples/velocity_control.py", "--url", url,
               "--duration", "10", "--output", str(output)]
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        with httpx.Client(base_url=url) as client:
            for _ in range(100):
                robot = client.get("/api/state").json()["robots"][0]
                if robot["target_v"] > 0:
                    break
                time.sleep(.05)
            else:
                pytest.fail("Example did not start moving")
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 130, (stdout, stderr)
            robot = client.get("/api/state").json()["robots"][0]
            assert not robot["armed"] and robot["control_owner"] is None
            assert robot["target_v"] == robot["target_omega"] == 0
        manifest = json.loads((output / "experiment.json").read_text())
        assert manifest["result"] == "aborted"
        assert manifest["error"] == "KeyboardInterrupt"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def test_published_dataset_reproduces_summary(tmp_path):
    from examples.analyze_run import analyze

    source = ROOT / "docs/public/examples/first-run"
    (tmp_path / "experiment.json").write_bytes((source / "experiment.json").read_bytes())
    summary, _ = analyze(tmp_path, source / "logs")
    assert summary == json.loads((source / "summary.json").read_text())


def test_analyzer_rejects_aborted_and_session_changes(tmp_path):
    from examples.analyze_run import analyze

    folder = tmp_path / "run"
    folder.mkdir()
    manifest = {"run_id": "sample", "result": "aborted", "end_time": None}
    path = folder / "experiment.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="aborted"):
        analyze(folder, tmp_path)
    manifest.update(result="completed", start_time=10., end_time=12., session="one",
                    robots=["car-01"], mode="demo")
    path.write_text(json.dumps(manifest))
    logs = tmp_path / "sample"
    logs.mkdir()
    event = {"time": 11., "kind": "configuration", "data": {"session": "two"}}
    (logs / "events.jsonl").write_text(json.dumps(event) + "\n")
    with pytest.raises(ValueError, match="session changed"):
        analyze(folder, tmp_path)
    assert not (folder / "trajectories.csv").exists()
