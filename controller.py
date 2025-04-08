import asyncio
from bleak import BleakClient
from anki_drive.car.constants import WRITE_UUID, NOTIFY_UUID, TRANSITION_FINISH_LINE


class AnkiCar:
    def __init__(self, mac):
        self.mac = mac
        self.client = BleakClient(mac)
        self.connected = False
        self.track = []
        self._last_piece = None
        self._start_count = 0

    async def connect(self):
        print(f"🔌 Verbinden met {self.mac}...")
        await self.client.connect()
        self.connected = True
        print("✅ Verbonden.")
        await self.enable_sdk_mode()
        await asyncio.sleep(0.2)

    async def enable_sdk_mode(self):
        print("🎮 SDK-modus geactiveerd")
        await self.client.write_gatt_char(WRITE_UUID, b"\x01\x90\x01\x01")

    async def start_notify(self, handler=None):
        def default_handler(_, data: bytearray):
            if len(data) >= 7 and data[0] == 0x27:
                piece_id = data[6]
                if piece_id != self._last_piece:
                    self.track.append(piece_id)
                    print(f"📍 Nieuw stuk gedetecteerd: {piece_id}")
                    self._last_piece = piece_id
                    if piece_id == TRANSITION_FINISH_LINE:
                        self._start_count += 1

        notify_handler = handler if handler else default_handler
        await self.client.start_notify(NOTIFY_UUID, notify_handler)
        print("📡 Notificaties gestart.")

    async def set_speed(self, speed: int, accel: int = 800):
        speed = max(0, min(speed, 1000))
        speed_val = speed.to_bytes(2, byteorder="little", signed=True)
        accel_val = accel.to_bytes(2, byteorder="little", signed=True)
        command = b"\x06\x24" + speed_val + accel_val + b"\x01"
        print(f"⚡ Zet snelheid: {speed}")
        await self.client.write_gatt_char(WRITE_UUID, command)

    async def stop(self):
        print("🛑 Stop")
        await self.set_speed(0)

    async def disconnect(self):
        if self.client.is_connected:
            await self.client.disconnect()
            print("🔌 Verbinding verbroken.")

    def is_track_scanned(self, laps=2):
        return self._start_count >= laps

    def get_track(self):
        return self.track
