#!/usr/bin/env python3
"""Start the local control and vision services on Windows."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def stop_process(process, graceful=False):
    if process is None or process.poll() is not None:
        return
    try:
        if graceful:
            process.send_signal(signal.CTRL_BREAK_EVENT if os.name == 'nt' else signal.SIGINT)
        else:
            process.terminate()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait()


def main():
    os.chdir(HERE)
    if not (HERE / 'frontend/dist/index.html').is_file():
        npm = 'npm.cmd' if os.name == 'nt' else 'npm'
        subprocess.run([npm, '--prefix', 'frontend', 'ci'], check=True)
        subprocess.run([npm, '--prefix', 'frontend', 'run', 'build'], check=True)

    vision = backend = None
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    try:
        if os.environ.get('ROBOT_START_VISION', '1') != '0':
            port = int(os.environ.get('ROBOT_VISION_PORT', '8765'))
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', port))
            os.environ.setdefault('ROBOT_DEFAULT_VISION_URL', f'http://127.0.0.1:{port}')
            args = [sys.executable, str(ROOT / 'apriltag_live.py'), '--port', str(port), '--initial-source', 'disconnected']
            if os.environ.get('ROBOT_VISION_RUNTIME_CONFIG'):
                args += ['--runtime-config', os.environ['ROBOT_VISION_RUNTIME_CONFIG']]
            vision = subprocess.Popen(args, creationflags=flags)
            deadline = time.monotonic() + 10
            while True:
                if vision.poll() is not None:
                    raise RuntimeError('Vision service exited during startup')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/config', timeout=1):
                        break
                except (OSError, URLError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Vision service startup timed out')
                    time.sleep(.1)
        backend = subprocess.Popen([sys.executable, '-m', 'backend.app'], creationflags=flags)
        while backend.poll() is None:
            if vision is not None and vision.poll() is not None:
                raise RuntimeError('Vision service exited unexpectedly')
            time.sleep(.2)
        return backend.returncode
    finally:
        stop_process(backend, graceful=True)
        stop_process(vision)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Startup failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
