import os
import time
import random
import datetime
import mysql.connector as mysql_driver
from pymongo import MongoClient, UpdateOne
import math

# Configuración desde entorno
mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
mysql_config = {
    "host": os.getenv("MYSQL_HOST", "mysql"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "root"),
    "database": os.getenv("MYSQL_DB", "historian")
}

# Enhanced tags per device with base values for more realistic simulation
device_configs = {
    "S_PM_17 2": {
        "tags": ["Motor1_Temp", "Motor1_Speed"],
        "base_temp": 75,
        "base_speed": 1800,
        "temp_variation": 15,
        "speed_variation": 200
    },
    "S_PM_17:": {
        "tags": ["Motor2_Temp", "Motor2_Speed"],
        "base_temp": 82,
        "base_speed": 1950,
        "temp_variation": 12,
        "speed_variation": 150
    },
    "S_FN_6": {
        "tags": ["Motor3_Temp", "Motor3_Speed"],
        "base_temp": 68,
        "base_speed": 1650,
        "temp_variation": 18,
        "speed_variation": 250
    },
    "S_CM_8": {
        "tags": ["Sensor_Temp"],
        "base_temp": 45,
        "temp_variation": 8
    },
    "S_CM_STO1": {
        "tags": ["Sensor_Temp"],
        "base_temp": 52,
        "temp_variation": 10
    }
}

status_options = ["RUNNING", "STOPPED", "ERROR", "MAINTENANCE", "OFFLINE"]

# Time-based simulation state
simulation_time = 0

def simulate_realistic_value(tag, device_id, time_factor):
    """Generate more realistic, time-varying sensor values"""
    global simulation_time
    
    config = device_configs.get(device_id, {})
    
    # Create time-based variation using sine waves for smooth changes
    time_wave = math.sin(time_factor * 0.1) * 0.5  # Slow oscillation
    noise = random.uniform(-0.2, 0.2)  # Random noise
    
    if "Temp" in tag:
        base = config.get("base_temp", 70)
        variation = config.get("temp_variation", 15)
        
        # Temperature varies more realistically
        value = base + (time_wave * variation) + noise * 3
        
        # Add occasional spikes for interest
        if random.random() < 0.05:  # 5% chance of spike
            value += random.uniform(5, 15)
            
        return round(max(30, min(120, value)), 1)  # Clamp between 30-120°C
        
    elif "Speed" in tag:
        base = config.get("base_speed", 1800)
        variation = config.get("speed_variation", 200)
        
        # Speed varies with time and has more dramatic changes
        value = base + (time_wave * variation) + noise * 50
        
        # Occasional speed changes
        if random.random() < 0.08:  # 8% chance of speed change
            value += random.uniform(-300, 300)
            
        return round(max(500, min(3500, value)), 0)  # Clamp between 500-3500 RPM
        
    else:
        return round(random.uniform(0, 1), 2)

def simulate_status(current):
    # More frequent status changes for demo purposes
    if random.random() < 0.02:  # 2% probability of change (was 0.5%)
        options = [s for s in status_options if s != current]
        return random.choice(options)
    return current

def connect_with_retry(config, max_retries=10, wait_seconds=5):
    for attempt in range(max_retries):
        try:
            conn = mysql_driver.connect(**config)
            print("✅ Connected to MySQL")
            return conn
        except mysql_driver.Error as err:
            print(f"⏳ Attempt {attempt + 1}: MySQL not ready: {err}")
            time.sleep(wait_seconds)
    raise Exception("❌ Could not connect to MySQL after multiple attempts")

def run():
    global simulation_time
    
    mongo = MongoClient(mongo_uri)
    db = mongo["gateway"]
    devices = db["devices"]
    current_values = db["current_values"]
    hourly_agg = db["hourly_agg"]
    daily_agg = db["daily_agg"]
    status_history = db["device_status_history"]

    mysql_conn = connect_with_retry(mysql_config)
    cursor = mysql_conn.cursor()

    print("🚀 Enhanced simulator started - generating dynamic data every 5 seconds!")

    while True:
        simulation_time += 1
        now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
        hour = now.replace(minute=0)
        day = now.date()

        batch_updates = []

        for device in devices.find({}):
            device_id = device["device_id"]
            
            for tag in device["tags"]:
                # Generate realistic, time-varying values
                value = simulate_realistic_value(tag, device_id, simulation_time)

                # Insert in MySQL (historian) - every update
                cursor.execute(
                    "INSERT INTO TagValue (tag, device_id, timestamp, value, unit) VALUES (%s, %s, %s, %s, %s)",
                    (tag, device_id, now, value, "unit")
                )

                # Batch update for current values in MongoDB
                batch_updates.append(
                    UpdateOne(
                        {"tag": tag},
                        {"$set": {
                            "device_id": device_id,
                            "value": value,
                            "timestamp": now,
                            "unit": "unit"
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

                # Agregado por día
                daily_agg.update_one(
                    {"tag": tag, "day": str(day)},
                    {"$push": {"values": value}},
                    upsert=True
                )

            # Simular cambio de estado
            new_status = simulate_status(device.get("status", "RUNNING"))
            if new_status != device.get("status"):
                devices.update_one(
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
                print(f"🔄 Device {device_id} status changed to {new_status}")

        # Execute all current_values updates in batch
        if batch_updates:
            current_values.bulk_write(batch_updates)
        
        mysql_conn.commit()
        
        print(f"📊 Simulated dynamic data at {now.isoformat()} (cycle {simulation_time})")
        
        # Update every 5 seconds for more visible changes
        time.sleep(5)

if __name__ == "__main__":
    run()