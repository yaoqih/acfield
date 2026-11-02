"""Bounded JSON datagrams; endpoints are learned from device telemetry."""
import asyncio
import json
import logging
from pydantic import ValidationError
from .models import Telemetry

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
            msg = Telemetry.model_validate_json(data)
            self.fleet.telemetry(msg, addr)
        except (ValidationError, ValueError, KeyError):
            self.rejected += 1

    def send(self, packet, endpoint):
        if endpoint and self.transport and not self.transport.is_closing():
            self.transport.sendto(json.dumps(packet, separators=(",", ":")).encode(), endpoint)

    def error_received(self, exc):
        log.warning("UDP socket error: %s", exc)
