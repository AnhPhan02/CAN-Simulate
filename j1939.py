"""J1939 codec: 29-bit ID build/parse + signal (SPN) encode/decode.

Không phụ thuộc DBC, định nghĩa signal trực tiếp trong MESSAGES để dễ đọc/mở rộng.
"""
from dataclasses import dataclass, field


# ---------------------------------------------------------------- 29-bit ID
@dataclass
class J1939Id:
    priority: int
    pgn: int
    sa: int          # source address
    da: int = 0xFF   # destination (chỉ có nghĩa với PDU1)

    @property
    def pf(self) -> int:
        return (self.pgn >> 8) & 0xFF

    @property
    def is_pdu1(self) -> bool:
        return self.pf < 240


def build_id(priority: int, pgn: int, sa: int, da: int = 0xFF) -> int:
    dp_pf = (pgn >> 8) & 0x3FF          # EDP|DP|PF
    pf = dp_pf & 0xFF
    ps = da if pf < 240 else pgn & 0xFF  # PDU1: PS = DA, PDU2: PS = group extension
    return ((priority & 0x7) << 26) | (dp_pf << 16) | (ps << 8) | (sa & 0xFF)


def parse_id(can_id: int) -> J1939Id:
    priority = (can_id >> 26) & 0x7
    dp_pf = (can_id >> 16) & 0x3FF
    pf = dp_pf & 0xFF
    ps = (can_id >> 8) & 0xFF
    sa = can_id & 0xFF
    if pf < 240:
        return J1939Id(priority, dp_pf << 8, sa, da=ps)
    return J1939Id(priority, (dp_pf << 8) | ps, sa)


# ---------------------------------------------------------------- signals
@dataclass
class Signal:
    name: str
    spn: int
    start_byte: int   # 0-based
    length: int       # bytes (little-endian, theo J1939)
    scale: float
    offset: float
    unit: str

    def encode(self, value: float, data: bytearray) -> None:
        raw = round((value - self.offset) / self.scale)
        raw = max(0, min(raw, (1 << (8 * self.length)) - 1))
        data[self.start_byte:self.start_byte + self.length] = raw.to_bytes(self.length, "little")

    def decode(self, data: bytes):
        raw = int.from_bytes(data[self.start_byte:self.start_byte + self.length], "little")
        # J1939: toàn bit 1 = "not available", 0xFE.. = error
        if raw == (1 << (8 * self.length)) - 1:
            return None
        return raw * self.scale + self.offset


@dataclass
class Message:
    name: str
    pgn: int
    priority: int
    period_ms: int
    signals: list = field(default_factory=list)

    def encode(self, values: dict) -> bytes:
        data = bytearray(b"\xFF" * 8)  # byte không dùng = 0xFF (not available)
        for s in self.signals:
            if s.name in values:
                s.encode(values[s.name], data)
        return bytes(data)

    def decode(self, data: bytes) -> dict:
        return {s.name: s.decode(data) for s in self.signals}


# Nguồn: SAE J1939-71 (EEC1, CCVS1, ET1, ETC2)
MESSAGES = {
    m.pgn: m for m in [
        Message("EEC1", 61444, 3, 10, [
            Signal("EngineSpeed", 190, 3, 2, 0.125, 0, "rpm"),
        ]),
        Message("CCVS1", 65265, 6, 100, [
            Signal("WheelSpeed", 84, 1, 2, 1 / 256, 0, "km/h"),
        ]),
        Message("ET1", 65262, 6, 1000, [
            Signal("CoolantTemp", 110, 0, 1, 1, -40, "degC"),
        ]),
        Message("ETC2", 61445, 6, 100, [
            Signal("SelectedGear", 524, 0, 1, 1, -125, ""),
            Signal("CurrentGear", 523, 3, 1, 1, -125, ""),
        ]),
    ]
}
BY_NAME = {m.name: m for m in MESSAGES.values()}
