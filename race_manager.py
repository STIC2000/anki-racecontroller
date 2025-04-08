import asyncio
import os
import json

from anki_drive.car.controller import AnkiCar
from anki_drive.track.scanner import scan_track
from anki_drive.car.messages import set_speed, stop_car
from anki_drive.car.constants import WRITE_UUID

class RaceManager:
    def __init__(self, max_players=4):
        self.max_players = max_players
        self.cars = []
        self.track = None

    def add_car(self, mac, name, player_type="human"):
        if len(self.cars) >= self.max_players:
            raise Exception("Max aantal spelers bereikt.")
        car = {
            "mac": mac,
            "name": name,
            "player_type": player_type,
            "instance": AnkiCar(mac),
            "status": "connected"
        }
        self.cars.append(car)

    async def scan_track_with_car(self, mac):
        """Laat een specifieke auto de baan scannen."""
        print(f"📡 Start scan met auto {mac}")
        self.track = await scan_track(mac)

    def load_track_from_disk(self, mac):
        """Laadt eerder opgeslagen track van disk"""
        filename = f"anki_drive/data/track_{mac.replace(':', '')}.json"
        if not os.path.exists(filename):
            raise FileNotFoundError("Geen bestaande trackscan gevonden.")
        with open(filename, "r") as f:
            self.track = json.load(f)

    async def position_all_cars(self):
        if not self.track:
            raise Exception("Track nog niet gescand of geladen.")
        
        finish_index = len(self.track) - 1 - self.track[::-1].index(34)  # 34 = TRANSITION_FINISH_LINE
        pieces_to_drive = len(self.track) - finish_index - 1

        async def align_car(car):
            driven_pieces = 0
            done = asyncio.Event()

            def handler(sender, data):
                nonlocal driven_pieces
                if len(data) > 10:
                    piece_id = data[-2]
                    if piece_id != 34:
                        driven_pieces += 1
                        print(f"[{car['name']}] Rijdt stuk {driven_pieces}/{pieces_to_drive}")
                        if driven_pieces >= pieces_to_drive:
                            done.set()

            await car["instance"].connect()
            await car["instance"].start_notify(handler)
            await car["instance"].client.write_gatt_char(WRITE_UUID, set_speed(300))
            try:
                await asyncio.wait_for(done.wait(), timeout=15)
            finally:
                await car["instance"].client.write_gatt_char(WRITE_UUID, stop_car())
                await car["instance"].stop_notify()
                car["status"] = "ready"
                print(f"[{car['name']}] ✅ Gepositioneerd voor start.")

        await asyncio.gather(*(align_car(c) for c in self.cars))

    def is_ready(self):
        return all(c["status"] == "ready" for c in self.cars)

    async def start_race(self):
        async def launch(car):
            await car["instance"].client.write_gatt_char(WRITE_UUID, set_speed(500))

        await asyncio.gather(*(launch(c) for c in self.cars))

    def get_status(self):
        return [
            {
                "name": c["name"],
                "mac": c["mac"],
                "player_type": c["player_type"],
                "status": c["status"]
            }
            for c in self.cars
        ]
