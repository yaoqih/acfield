"""Bounded, non-blocking JSONL recording; file I/O stays off the control loop."""
import json
import queue
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path


class Recorder:
    def __init__(self, folder: Path, metadata):
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S_")+uuid.uuid4().hex[:8]
        self.folder = folder/self.run_id
        self.folder.mkdir(parents=True)
        (self.folder/"config.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        self.queue = queue.Queue(maxsize=2048)
        self.dropped = 0
        self.error = None
        self.closing = threading.Event()
        self.thread = threading.Thread(target=self._write, name="robot-recorder", daemon=True)
        self.thread.start()

    def record(self, kind, data):
        row = {"time": time.time(), "monotonic": time.monotonic(), "kind": kind, "data": data}
        try:
            self.queue.put_nowait(row)
        except queue.Full:
            self.dropped += 1

    def _write(self):
        try:
            with (self.folder/"events.jsonl").open("w", encoding="utf-8") as stream:
                while not self.closing.is_set() or not self.queue.empty():
                    try:
                        row = self.queue.get(timeout=.1)
                    except queue.Empty:
                        stream.flush()
                        continue
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+"\n")
        except (OSError, ValueError, TypeError) as exc:
            self.error = str(exc)

    def close(self):
        self.closing.set()
        self.thread.join(timeout=3)
