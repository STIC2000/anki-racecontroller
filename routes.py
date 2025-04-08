import json
import asyncio
from flask import render_template, request, redirect, url_for, jsonify
from anki_drive.track.scanner import scan_track
from anki_drive.car.controller import AnkiCar
from anki_drive.car.messages import set_speed, stop_car
from anki_drive.track.race_manager import RaceManager

def configure_routes(app):
    with open("anki_drive/config/cars.json") as f:
        CAR_CONFIG = json.load(f)

    # In-memory opslag van actieve auto-instances
    active_cars = {}
    race_manager = RaceManager()

    @app.route("/")
    def index():
        return redirect(url_for("setup"))

    @app.route("/setup")
    def setup():
        return render_template("setup.html", cars=CAR_CONFIG)

    @app.route("/controller/<int:player_id>")
    def controller(player_id):
        car_mac = request.args.get("car_mac")
        mode = request.args.get("mode")
        laps = request.args.get("laps")
        return render_template("controller.html", player_id=player_id, car_mac=car_mac, mode=mode, laps=laps)

    @app.route('/api/scan_track', methods=['POST'])
    def scan():
        mac = request.form.get("car_mac") or request.args.get("car_mac")
        if not mac:
            return "Missing car_mac", 400
        try:
            result = asyncio.run(scan_track(mac))
            return jsonify(result)
        except Exception as e:
            return f"Scan failed: {e}", 500

    @app.route("/api/send/<int:player_id>/<command>", methods=["POST"])
    def send_command(player_id, command):
        mac = request.args.get("car_mac") or request.args.get("mac")
        if not mac:
            return "Missing car_mac", 400

        async def send():
            if mac not in active_cars:
                active_cars[mac] = AnkiCar(mac)
                await active_cars[mac].connect()

            car = active_cars[mac]
            if command == "start":
                await car.set_speed(500)
            elif command == "stop":
                await car.stop()
            elif command == "boost":
                await car.set_speed(800)
            elif command == "powerup":
                await car.set_speed(700)
            else:
                raise ValueError("Unknown command")

        try:
            asyncio.run(send())
            return "OK", 200
        except Exception as e:
            return f"Command failed: {e}", 500

    # RACE MANAGER ROUTES

    @app.route("/api/race/add_car", methods=["POST"])
    def add_car_to_race():
        data = request.json
        mac = data.get("mac")
        name = data.get("name")
        player_type = data.get("player_type", "human")

        if not mac or not name:
            return "Missing parameters", 400

        try:
            race_manager.add_car(mac, name, player_type)
            return "Car added", 200
        except Exception as e:
            return str(e), 500

    @app.route("/api/race/scan_track", methods=["POST"])
    def scan_with_car():
        mac = request.json.get("mac")
        if not mac:
            return "Missing car_mac", 400
        try:
            asyncio.run(race_manager.scan_track_with_car(mac))
            return "Scan complete", 200
        except Exception as e:
            return f"Scan failed: {e}", 500

    @app.route("/api/race/position_all", methods=["POST"])
    def position_all():
        try:
            asyncio.run(race_manager.position_all_cars())
            return "All cars positioned", 200
        except Exception as e:
            return f"Positioning failed: {e}", 500

    @app.route("/api/race/start", methods=["POST"])
    def start_race():
        try:
            asyncio.run(race_manager.start_race())
            return "Race started", 200
        except Exception as e:
            return f"Start failed: {e}", 500

    @app.route("/api/race/status", methods=["GET"])
    def get_race_status():
        return jsonify({
            "ready": race_manager.is_ready(),
            "cars": race_manager.get_status()
        })
