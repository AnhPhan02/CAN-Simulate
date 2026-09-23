"""TX module: sinh pattern xe (RPM, speed, temp, gear) và gửi J1939 frame theo chu kỳ."""
import math
import threading
import time

import can

from j1939 import BY_NAME, build_id

ECU_SA = 0x00       # Engine #1
TCU_SA = 0x03       # Transmission #1

SOURCE = {"EEC1": ECU_SA, "ET1": ECU_SA, "CCVS1": ECU_SA, "ETC2": TCU_SA}


class VehicleModel:
    """Pattern đơn giản: tăng tốc/giảm tốc dạng sin, gear theo speed."""

    def __init__(self):
        self.t0 = time.monotonic()

    def state(self) -> dict:
        t = time.monotonic() - self.t0
        speed = 60 + 50 * math.sin(t / 5)              # 10..110 km/h
        gear = min(6, 1 + int(speed // 20))
        rpm = 800 + (speed / gear) * 90                # rpm giảm khi lên số
        temp = min(90, 40 + t * 2)                     # warm-up rồi giữ 90°C
        return {"EngineSpeed": rpm, "WheelSpeed": speed, "CoolantTemp": temp,
                "CurrentGear": gear, "SelectedGear": gear}


class CanTransmitter:
    def __init__(self, bus: can.BusABC, model: VehicleModel, verbose=False):
        self.bus, self.model, self.verbose = bus, model, verbose
        self._stop = threading.Event()
        self._threads = []

    def send(self, msg_name: str, values: dict):
        m = BY_NAME[msg_name]
        frame = can.Message(
            arbitration_id=build_id(m.priority, m.pgn, SOURCE[msg_name]),
            data=m.encode(values), is_extended_id=True)
        self.bus.send(frame)
        if self.verbose:
            print(f"TX {frame.arbitration_id:08X} {frame.data.hex(' ').upper()}  {msg_name}")

    def _loop(self, msg_name: str):
        period = BY_NAME[msg_name].period_ms / 1000
        nxt = time.monotonic()
        while not self._stop.is_set():
            self.send(msg_name, self.model.state())
            nxt += period
            self._stop.wait(max(0, nxt - time.monotonic()))  # chống drift

    def start(self, msg_names=("EEC1", "CCVS1", "ET1", "ETC2")):
        for n in msg_names:
            th = threading.Thread(target=self._loop, args=(n,), daemon=True)
            th.start()
            self._threads.append(th)

    def stop(self):
        self._stop.set()
        for th in self._threads:
            th.join()
