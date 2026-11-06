"""A process-wide UTC mapping. Never changes the host clock or steps control time."""
import asyncio
import math
import os
import socket
import struct
import time


class Clock:
    def __init__(self):
        self.origin = time.time() - time.monotonic()
        self.correction = self.target = 0.
        self.updated = time.monotonic()
        self.source = "local"
        self.last_ntp = None
        self.ntp_error = None

    def now_ms(self):
        now = time.monotonic()
        # At most 1ms/s correction: timestamps stay continuous and increasing.
        step = max(0., now-self.updated)*.001
        self.correction += max(-step, min(step, self.target-self.correction))
        self.updated = now
        return (self.origin+now+self.correction)*1000

    def status(self):
        return {"source": self.source, "ntp_at": self.last_ntp,
                "ntp_error": self.ntp_error, "pending_correction_ms": (self.target-self.correction)*1000}

    def probe(self, host):
        # Bounded UDP NTP exchange in a worker, never in the control event loop.
        samples = []
        for family, kind, proto, _, address in socket.getaddrinfo(host, 123, type=socket.SOCK_DGRAM):
            try:
                with socket.socket(family, kind, proto) as sock:
                    sock.settimeout(1.)
                    sock.connect(address)
                    request = bytearray(48)
                    request[0] = 0x23
                    t1 = time.time()
                    stamp = int((t1+2208988800)*2**32)
                    request[40:48] = struct.pack("!Q", stamp)
                    start = time.monotonic()
                    sock.send(request)
                    reply = sock.recv(512)
                    elapsed = time.monotonic()-start
                    if len(reply) < 48 or reply[0] >> 6 == 3 or reply[0] & 7 != 4 or not 1 <= reply[1] <= 15:
                        continue
                    if reply[24:32] != request[40:48]:
                        continue
                    t2, t3 = (struct.unpack("!Q", reply[i:i+8])[0]/2**32-2208988800 for i in (32, 40))
                    delay = elapsed-(t3-t2)
                    if not math.isfinite(delay) or delay < -.001 or delay > .5 or t3 < t2:
                        continue
                    utc_mid = (t2+t3)/2
                    local_mid = start+elapsed/2
                    samples.append((delay, utc_mid-local_mid-self.origin))
            except OSError:
                continue
        if not samples:
            raise OSError("NTP unavailable; using local time")
        return min(samples)[1]

    async def run(self):
        host = os.getenv("ROBOT_NTP_SERVER", "pool.ntp.org")
        while True:
            if host:
                try:
                    self.target = await asyncio.to_thread(self.probe, host)
                    self.source, self.last_ntp, self.ntp_error = "ntp", time.time(), None
                except OSError as exc:
                    self.ntp_error = str(exc)
            await asyncio.sleep(300)


clock = Clock()
