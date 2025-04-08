import asyncio
import json
import os
from anki_drive.car.controller import AnkiCar
from anki_drive.car.messages import set_speed, stop_car
from anki_drive.car.constants import WRITE_UUID, TRANSITION_FINISH_LINE

INVALID_PIECES = [0, 244, 255]

with open("anki_drive/config/settings.json") as f:
    CONFIG = json.load(f)
    SCAN_SPEED = CONFIG["anki"]["default_speed"]
    SLOW_SPEED = CONFIG["anki"]["slow_speed"]
    STOP_THRESHOLD_MM = CONFIG["anki"]["stop_threshold_mm"]
    START_POSITION = CONFIG["anki"]["start_position"]

async def scan_track(mac):
    car = AnkiCar(mac)
    track = []
    finish_count = 0
    scanning_started = False
    finished = asyncio.Event()
    stop_after_countdown = None
    slow_down_at = None
    slowed_down = False

    async def stop_and_finalize():
        try:
            await car.client.write_gatt_char(WRITE_UUID, stop_car())
            print("[INFO] Auto gestopt.")
        except Exception as e:
            print(f"[WAARSCHUWING] Stop commando faalde: {e}")
        finally:
            finished.set()

    def notification_handler(sender, data):
        nonlocal track, finish_count, scanning_started, stop_after_countdown, slow_down_at, slowed_down

        print(f"[RAW] Data ontvangen: {list(data)}")

        if len(data) > 10:
            piece_id = data[-1]

            if piece_id in INVALID_PIECES or piece_id > 100:
                print(f"[IGNORED] Ongeldig stuk genegeerd: {piece_id}")
                return

            print(f"[TRACK] Gedetecteerd stuk: {piece_id}")

            if piece_id == TRANSITION_FINISH_LINE:
                finish_count += 1
                print(f"[TRACK] Finishlijn gezien ({finish_count}x)")

                if finish_count == 1:
                    print("[SCAN] Start track scanning.")
                    scanning_started = True

                elif finish_count == 2:
                    print("[SCAN] Track compleet.")
                    
                    stop_after_countdown = len(track) + START_POSITION
                    slow_down_at = stop_after_countdown - 2  # laatste bocht
                    
            if scanning_started:
                if not track or piece_id != track[-1]:
                    track.append(piece_id)

            if stop_after_countdown is not None:
                if stop_after_countdown == slow_down_at and not slowed_down:
                    print("[ACTIE] Afremmen voor positionering...")
                    asyncio.create_task(car.client.write_gatt_char(WRITE_UUID, set_speed(SLOW_SPEED)))
                    slowed_down = True

                elif stop_after_countdown == 0:
                    print("[ACTIE] Stoppen net vóór finishlijn #3.")
                    asyncio.create_task(stop_and_finalize())

                if stop_after_countdown > 0:
                    stop_after_countdown -=1

    try:
        print("[BLE] Verbinden met de auto...")
        await car.connect()
        await car.start_notify(notification_handler)
        print("[AUTO] Auto start met rijden...")
        await car.client.write_gatt_char(WRITE_UUID, set_speed(SCAN_SPEED))

        await asyncio.wait_for(finished.wait(), timeout=60)

    except Exception as e:
        print(f"[FOUT] Tijdens scannen: {e}")
    finally:
        if car.client.is_connected:
            await car.disconnect()
        print("[BLE] Verbinding verbroken.")
        print("[SCAN] Scan voltooid.")
        print(f"[RESULTAAT] Gescande track: {track}")

        track_dir = "anki_drive/data"
        os.makedirs(track_dir, exist_ok=True)
        filename = f"{track_dir}/track_{mac.replace(':', '')}.json"
        with open(filename, "w") as f:
            json.dump(track, f)
            print(f"[BESTAND] Track opgeslagen naar: {filename}")

        return {
            "track": track,
            "ready": True,
            "length": len(track),
            "positioned_at": TRANSITION_FINISH_LINE
        }
