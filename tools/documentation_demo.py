"""Capture the documented demo workflow for the downloadable example dataset."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

from acfield import Client, TransportError

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/public/examples/first-run")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Choose a new output directory or archive the previous sample first")
    with tempfile.TemporaryDirectory(prefix="acfield-docs-demo-") as directory:
        runtime = Path(directory)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "robot_server"),
               "ROBOT_MODE": "demo", "ROBOT_HOST": "127.0.0.1", "ROBOT_PORT": str(port),
               "ROBOT_DB": str(runtime / "config.sqlite3"), "ROBOT_LOG_DIR": str(runtime / "logs"),
               "ROBOT_DEFAULT_VISION_URL": "", "ROBOT_VISION_URL": "", "ROBOT_NTP_SERVER": "",
               "ROBOT_ALLOW_UNLOCALIZED_CONTROL": "0"}
        process = subprocess.Popen([sys.executable, "-m", "backend.app"], cwd=ROOT, env=env)
        try:
            with Client(url) as client:
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Demo server exited before readiness")
                    try:
                        if client.health().ready:
                            break
                    except TransportError:
                        pass
                    time.sleep(.1)
                else:
                    raise RuntimeError("Demo server did not become ready")
            subprocess.run([sys.executable, "examples/velocity_control.py", "--url", url,
                            "--robots", "car-01", "car-02", "--duration", "2",
                            "--v", "0.05", "--omega", "0.2", "--output", str(output)],
                           cwd=ROOT, check=True, timeout=20)
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        shutil.copytree(runtime / "logs", output / "logs")
    subprocess.run([sys.executable, "examples/analyze_run.py", str(output),
                    "--logs", str(output / "logs"), "--plot"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
