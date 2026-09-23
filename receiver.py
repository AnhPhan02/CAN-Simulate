"""RX module: nhận frame, parse J1939 ID + decode signal, lưu state mới nhất."""
import threading
import time

import can

from j1939 import MESSAGES, parse_id


class J1939Listener(can.Listener):
    def __init__(self, on_decoded=None):
        self.latest = {}          # signal -> (value, unit, timestamp)
        self.counts = {}          # msg name -> số frame
        self.unknown = 0
        self._lock = threading.Lock()
        self.on_decoded = on_decoded

    def on_message_received(self, frame: can.Message):
        if not frame.is_extended_id:
            return
        jid = parse_id(frame.arbitration_id)
        msg = MESSAGES.get(jid.pgn)
        if msg is None:
            self.unknown += 1
            return
        values = msg.decode(frame.data)
        with self._lock:
            self.counts[msg.name] = self.counts.get(msg.name, 0) + 1
            for s in msg.signals:
                self.latest[s.name] = (values[s.name], s.unit, frame.timestamp)
        if self.on_decoded:
            self.on_decoded(jid, msg, values)

    def snapshot(self):
        with self._lock:
            return dict(self.latest), dict(self.counts)


class CanReceiver:
    def __init__(self, bus: can.BusABC, on_decoded=None):
        self.listener = J1939Listener(on_decoded)
        self.notifier = can.Notifier(bus, [self.listener], timeout=0.1)

    def stop(self):
        self.notifier.stop()


def print_decoded(jid, msg, values):
    vals = ", ".join(f"{k}={'N/A' if v is None else round(v, 2)}" for k, v in values.items())
    print(f"RX PGN={jid.pgn:5d} ({msg.name:5s}) SA=0x{jid.sa:02X} P={jid.priority} | {vals}")
