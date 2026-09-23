"""pytest: kiểm tra encode/decode round-trip và ID build/parse."""
from j1939 import BY_NAME, build_id, parse_id


def test_id_pdu2_roundtrip():
    cid = build_id(3, 61444, 0x00)
    assert cid == 0x0CF00400          # EEC1 từ Engine #1: ID quen thuộc trong log thật
    j = parse_id(cid)
    assert (j.priority, j.pgn, j.sa) == (3, 61444, 0x00)


def test_id_pdu1_has_da():
    cid = build_id(6, 0xEA00, 0xF9, da=0x00)   # Request PGN tới ECU 0x00
    j = parse_id(cid)
    assert j.pgn == 0xEA00 and j.da == 0x00 and j.sa == 0xF9


def test_signal_roundtrip():
    vals = {"EngineSpeed": 1500.0}
    data = BY_NAME["EEC1"].encode(vals)
    assert data[3:5] == (12000).to_bytes(2, "little")   # 1500 / 0.125
    assert BY_NAME["EEC1"].decode(data)["EngineSpeed"] == 1500.0
    d = BY_NAME["ET1"].decode(BY_NAME["ET1"].encode({"CoolantTemp": 85}))
    assert d["CoolantTemp"] == 85


def test_not_available():
    assert BY_NAME["CCVS1"].decode(b"\xFF" * 8)["WheelSpeed"] is None
