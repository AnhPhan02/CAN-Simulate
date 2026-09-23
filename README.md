# CAN J1939 Simulator (Python)

TX module sinh pattern xe → encode J1939 → gửi lên bus. RX module nhận → parse 29-bit ID (Priority/PGN/SA) → decode SPN.

| File | Vai trò |
|---|---|
| j1939.py | Build/parse ID, định nghĩa Message/Signal, encode/decode |
| transmitter.py | VehicleModel (pattern) + CanTransmitter (gửi theo chu kỳ từng PGN) |
| receiver.py | J1939Listener + Notifier, lưu giá trị mới nhất |
| main.py | CLI chạy TX, RX hoặc cả hai |

## Chạy
```bash
pip install -r requirements.txt
python main.py                 # virtual bus, không cần phần cứng
python main.py --log           # in từng frame TX/RX
pytest -q
```

## Bus thật (Linux / BeagleBone)
```bash
sudo modprobe vcan && sudo ip link add dev vcan0 type vcan && sudo ip link set up vcan0
python main.py --interface socketcan --channel vcan0
candump vcan0                  # xem song song bằng can-utils

# BBB can0, 250 kbit/s
sudo ip link set can0 type can bitrate 250000 && sudo ip link set up can0
python main.py --role tx --interface socketcan --channel can0
```

## Thêm message mới
Thêm `Message(...)` vào `MESSAGES` trong j1939.py với start_byte/length/scale/offset theo SAE J1939-71, rồi thêm signal tương ứng vào `VehicleModel.state()` và `SOURCE` trong transmitter.py.
