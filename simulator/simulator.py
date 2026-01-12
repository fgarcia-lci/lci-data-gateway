import os
import time
import random
import datetime
import json
import math
import mysql.connector as mysql_driver
from pymongo import MongoClient, UpdateOne

# Simple simulator that reads device/tag definitions from a shared JSON file,
# keeps MongoDB in sync, and writes both real-time values (Mongo) and historian
# data (MySQL) for all configured tags.

# Configuracion desde entorno
mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
mysql_config = {
    "host": os.getenv("MYSQL_HOST", "mysql"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DB", "historian")
}

# Ruta al fichero JSON de devices (compartido con MongoDB)
CONFIG_PATH = os.getenv("DEVICES_CONFIG_PATH", "/app/devices.json")

# Valores por defecto para cada tipo de tag (si no se especifica en el JSON).
# Se utilizan para magnitudes conocidas; para tipos nuevos se puede ampliar este diccionario.
DEFAULT_TYPE_CONFIG = {
    "Temp": {"base": 70, "variation": 15, "min": 30, "max": 120, "unit": "C", "precision": 1},
    "Speed": {"base": 1800, "variation": 200, "min": 500, "max": 3500, "unit": "RPM", "precision": 0},
    "PV": {"base": 50, "variation": 20, "min": 0, "max": 100, "unit": "%", "precision": 1},
    "Power": {"base": 10, "variation": 3, "min": 0, "max": 1000, "unit": "kW", "precision": 1},
}

status_options = ["RUNNING", "STOPPED", "ERROR", "MAINTENANCE", "OFFLINE"]

# Time-based simulation state
simulation_time = 0


def load_devices_config(path=CONFIG_PATH):
    """Load device definitions from JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                print(f"[warn] Expected a list of devices in {path}, got {type(data)}")
                return []
            return data
    except FileNotFoundError:
        print(f"[warn] Devices config not found at {path}, using empty list")
        return []
    except json.JSONDecodeError as err:
        print(f"[warn] Invalid JSON in {path}: {err}")
        return []


def build_sim_lookup(devices_def):
    """Build a lookup table: device_id -> sim config per type (Temp, Speed, etc.)."""
    lookup = {}
    for dev in devices_def:
        device_id = dev.get("device_id")
        if device_id:
            lookup[device_id] = dev.get("sim", {})
    return lookup


def parse_timestamp(ts):
    """Parse ISO date strings to datetime; fallback to now."""
    if isinstance(ts, datetime.datetime):
        return ts.replace(tzinfo=None)
    if isinstance(ts, str):
        try:
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.datetime.utcnow()


def upsert_devices_from_config(devices_collection, devices_def):
    """Ensure MongoDB devices collection contains the devices defined in JSON."""
    ops = []
    for dev in devices_def:
        device_id = dev.get("device_id")
        if not device_id:
            continue
        doc = {
            "device_id": device_id,
            "name": dev.get("name", device_id),
            "xeokit_id": dev.get("xeokit_id"),
            "tags": dev.get("tags", []),
            "hist_tags": dev.get("hist_tags", []),
            "status": dev.get("status", "RUNNING"),
            "status_timestamp": parse_timestamp(dev.get("status_timestamp")),
        }
        ops.append(UpdateOne({"device_id": device_id}, {"$set": doc}, upsert=True))
    if ops:
        devices_collection.bulk_write(ops)
        print(f"[info] Synced {len(ops)} devices from config into MongoDB")


def get_type_from_tag(tag):
    """Infer the type name from the tag. Reemplaza puntos y toma el ultimo segmento.
    Aplica mapeos sencillos para abreviaturas comunes (TE -> Temp, PV -> PV)."""
    clean = tag.replace(".", "_")
    parts = clean.split("_")
    last = parts[-1] if parts else clean

    # Mapeo simple por prefijo de instrumento
    if any(p.upper().startswith("TE") for p in parts):
        return "Temp"
    if last.upper() == "PV":
        return "PV"
    return last


def get_type_config(device_id, tag, sim_lookup):
    """Get config for a tag type for a device, falling back to defaults."""
    tag_type = get_type_from_tag(tag)
    device_config = sim_lookup.get(device_id, {}) if sim_lookup else {}
    type_config = device_config.get(tag_type) or DEFAULT_TYPE_CONFIG.get(tag_type) or {}
    return tag_type, type_config


def simulate_realistic_value(tag, device_id, time_factor, sim_lookup):
    """Generate time-varying values based on tag type and device config."""
    global simulation_time
    tag_type, type_config = get_type_config(device_id, tag, sim_lookup)

    base = type_config.get("base", 0)
    variation = type_config.get("variation", 0)
    min_val = type_config.get("min")
    max_val = type_config.get("max")
    precision = type_config.get("precision", 2)
    unit = type_config.get("unit", "unit")

    # Time-based variation using sine waves
    time_wave = math.sin(time_factor * 0.1) * 0.5
    noise = random.uniform(-0.2, 0.2)

    if tag_type == "Temp":
        value = base + (time_wave * variation) + noise * 3
        if random.random() < 0.05:
            value += random.uniform(5, 15)
    elif tag_type == "Speed":
        value = base + (time_wave * variation) + noise * 50
        if random.random() < 0.08:
            value += random.uniform(-300, 300)
    else:
        value = base + (time_wave * variation) + noise * max(1, variation or 1)

    if min_val is not None:
        value = max(min_val, value)
    if max_val is not None:
        value = min(max_val, value)

    return round(value, precision), unit


def simulate_status(current):
    # More frequent status changes for demo purposes
    if random.random() < 0.02:
        options = [s for s in status_options if s != current]
        return random.choice(options)
    return current


def connect_with_retry(config, max_retries=10, wait_seconds=5):
    for attempt in range(max_retries):
        try:
            conn = mysql_driver.connect(**config)
            print("Connected to MySQL")
            return conn
        except mysql_driver.Error as err:
            print(f"Attempt {attempt + 1}: MySQL not ready: {err}")
            time.sleep(wait_seconds)
    raise Exception("Could not connect to MySQL after multiple attempts")


def run():
    global simulation_time

    devices_from_file = load_devices_config()
    sim_lookup = build_sim_lookup(devices_from_file)

    mongo = MongoClient(mongo_uri)
    db = mongo["gateway"]
    devices_collection = db["devices"]
    current_values = db["current_values"]
    hourly_agg = db["hourly_agg"]
    daily_agg = db["daily_agg"]
    status_history = db["device_status_history"]

    # Keep MongoDB devices in sync with the JSON file (acts as source of truth)
    upsert_devices_from_config(devices_collection, devices_from_file)

    mysql_conn = connect_with_retry(mysql_config)
    cursor = mysql_conn.cursor()

    print(f"Simulator started - using device config: {CONFIG_PATH}")

    while True:
        simulation_time += 1
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        hour = now.replace(minute=0)
        day = now.date()

        batch_updates = []

        for device in devices_collection.find({}):
            device_id = device["device_id"]

            for tag in device.get("tags", []):
                # Compute simulated value and unit based on tag type and config
                value, unit = simulate_realistic_value(tag, device_id, simulation_time, sim_lookup)

                # Insert in MySQL (historian) - every update
                cursor.execute(
                    "INSERT INTO TagValue (tag, device_id, timestamp, value, unit) VALUES (%s, %s, %s, %s, %s)",
                    (tag, device_id, now, value, unit)
                )

                # Batch update for current values in MongoDB
                batch_updates.append(
                    UpdateOne(
                        {"tag": tag},
                        {"$set": {
                            "device_id": device_id,
                            "value": value,
                            "timestamp": now,
                            "unit": unit
                        }},
                        upsert=True
                    )
                )

                # Agregado por hora
                hourly_agg.update_one(
                    {"tag": tag, "hour": hour},
                    {"$push": {"values": value}},
                    upsert=True
                )

                # Agregado por dia
                daily_agg.update_one(
                    {"tag": tag, "day": str(day)},
                    {"$push": {"values": value}},
                    upsert=True
                )

            # Simular cambio de estado
            new_status = simulate_status(device.get("status", "RUNNING"))
            if new_status != device.get("status"):
                devices_collection.update_one(
                    {"device_id": device_id},
                    {"$set": {
                        "status": new_status,
                        "status_timestamp": now
                    }}
                )
                status_history.insert_one({
                    "device_id": device_id,
                    "status": new_status,
                    "timestamp": now
                })
                print(f"Device {device_id} status changed to {new_status}")

        # Execute all current_values updates in batch
        if batch_updates:
            current_values.bulk_write(batch_updates)

        mysql_conn.commit()

        print(f"Simulated dynamic data at {now.isoformat()} (cycle {simulation_time})")

        # Update every 5 seconds for more visible changes
        time.sleep(5)


if __name__ == "__main__":
    run()
