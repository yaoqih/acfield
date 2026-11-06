"""Bounded JSON datagrams; endpoints are learned from device telemetry."""
import asyncio
import json
import logging
from pydantic import ValidationError
from .models import Telemetry
from .clock import clock

log = logging.getLogger(__name__)


class DeviceProtocol(asyncio.DatagramProtocol):
    def __init__(self, fleet):
        self.fleet = fleet
        self.transport = None
        self.rejected = 0

    def connection_made(self, transport):
        self.transport = transport
        self.fleet.send = self.send

    def datagram_received(self, data, addr):
        if len(data) > 4096:
            self.rejected += 1
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
        except (ValidationError, ValueError, KeyError, TypeError, AttributeError):
            self.rejected += 1

    def send(self, packet, endpoint):
        if endpoint and self.transport and not self.transport.is_closing():
            self.transport.sendto(json.dumps(packet, separators=(",", ":")).encode(), endpoint)

    def error_received(self, exc):
        log.warning("UDP socket error: %s", exc)
