"""CAN J1939 simulator: TX + RX.

  python main.py                                  # virtual bus, dashboard mode
  python main.py --log                            # in từng frame TX/RX
  python main.py --interface socketcan --channel vcan0   # Linux vcan / BBB can0
  python main.py --role rx --interface socketcan --channel can0   # chỉ nhận
"""
import argparse
import time

import can

from receiver import CanReceiver, print_decoded
from transmitter import CanTransmitter, VehicleModel


def make_bus(args):
    kw = {"interface": args.interface, "channel": args.channel}
    if args.interface not in ("virtual", "socketcan"):
        kw["bitrate"] = args.bitrate   # PCAN/Vector/slcan... cần bitrate
    return can.Bus(**kw)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--interface", default="virtual")
    p.add_argument("--channel", default="sim0")
    p.add_argument("--bitrate", type=int, default=250000)  # J1939 chuẩn 250 kbit/s
    p.add_argument("--role", choices=["both", "tx", "rx"], default="both")
    p.add_argument("--duration", type=float, default=0, help="giây, 0 = chạy tới Ctrl+C")
    p.add_argument("--log", action="store_true")
    args = p.parse_args()

    # 2 bus riêng cho TX và RX (virtual bus không echo lại cho chính instance gửi)
    tx_bus = make_bus(args) if args.role in ("both", "tx") else None
    rx_bus = make_bus(args) if args.role in ("both", "rx") else None

    tx = CanTransmitter(tx_bus, VehicleModel(), verbose=args.log) if tx_bus else None
    rx = CanReceiver(rx_bus, print_decoded if args.log else None) if rx_bus else None
    if tx:
        tx.start()

    t_end = time.monotonic() + args.duration if args.duration else float("inf")
    try:
        while time.monotonic() < t_end:
            time.sleep(0.5)
            if rx and not args.log:
                latest, counts = rx.listener.snapshot()
                line = " | ".join(
                    f"{k}: {'N/A' if v is None else f'{v:.1f}'} {u}" for k, (v, u, _) in latest.items())
                print(f"\r{line}   ", end="", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        if tx:
            tx.stop()
        if rx:
            rx.stop()
            print("\nFrame count:", rx.listener.snapshot()[1])
        for b in (tx_bus, rx_bus):
            if b:
                b.shutdown()


if __name__ == "__main__":
    main()
