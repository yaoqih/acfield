"""Bounded JSON datagrams; endpoints are learned from device telemetry."""
import asyncio
import json
import logging
from collections import Counter
from pydantic import ValidationError
from .models import Telemetry
from .clock import clock

log = logging.getLogger(__name__)


class DeviceProtocol(asyncio.DatagramProtocol):
    def __init__(self, fleet):
        self.fleet = fleet
        self.transport = None
        self.received = 0
        self.rejected = 0
        self.rejection_counts = Counter()

    def reject(self, addr, reason, fields=()):
        self.rejected += 1
        self.rejection_counts[reason] += 1
        self.fleet.record("udp_rejected", {"endpoint": list(addr), "reason": reason, "fields": list(fields)})

    def connection_made(self, transport):
        self.transport = transport
        self.fleet.send = self.send

    def datagram_received(self, data, addr):
        self.received += 1
        if len(data) > 4096:
            self.reject(addr, "datagram_too_large")
            return
        try:
            obj = json.loads(data)
            if obj.get("type") == "time_sync":
                if (not isinstance(obj.get("id"), int) or isinstance(obj["id"], bool)
                        or not isinstance(obj.get("t1"), (float, int))):
                    raise ValueError("Invalid time probe")
                self.send({"type": "time_sync", "id": obj["id"], "t1": obj["t1"],
                           "t2": clock.now_ms(), "t3": clock.now_ms()}, addr)
                return
            msg = Telemetry.model_validate(obj)
            self.fleet.telemetry(msg, addr)
        except ValidationError as exc:
            self.reject(addr, "telemetry_validation", [".".join(map(str, e["loc"])) for e in exc.errors()])
        except (ValueError, KeyError, TypeError, AttributeError):
            self.reject(addr, "invalid_message")

    def send(self, packet, endpoint):
        if endpoint and self.transport and not self.transport.is_closing():
            self.transport.sendto(json.dumps(packet, separators=(",", ":")).encode(), endpoint)

    def error_received(self, exc):
        log.warning("UDP socket error: %s", exc)
