// mongodb/init.js
db = db.getSiblingDB('gateway');

// Create devices collection and insert initial data
db.devices.insertMany([
  {
    "device_id": "S_PM_17 2",
    "name": "Motor Principal 1",
    "xeokit_id": 4312,
    "tags": ["Motor1_Temp", "Motor1_Speed"],
    "status": "RUNNING",
    "status_timestamp": new Date("2025-07-16T08:00:00Z")
  },
  {
    "device_id": "S_PM_17:",
    "name": "Motor Principal 2",
    "xeokit_id": 4313,
    "tags": ["Motor2_Temp", "Motor2_Speed"],
    "status": "RUNNING",
    "status_timestamp": new Date("2025-07-16T08:00:00Z")
  },
  {
    "device_id": "S_FN_6",
    "name": "Motor Cinta cubierta 3",
    "xeokit_id": 4314,
    "tags": ["Motor3_Temp", "Motor3_Speed"],
    "status": "RUNNING",
    "status_timestamp": new Date("2025-07-16T08:00:00Z")
  },
  {
    "device_id": "S_CM_8",
    "name": "Sensor de Temperatura",
    "xeokit_id": 5002,
    "tags": ["Sensor_Temp"],
    "status": "RUNNING",
    "status_timestamp": new Date("2025-07-16T08:00:00Z")
  },
  {
    "device_id": "S_CM_STO1",
    "name": "Sensor de Temperatura",
    "xeokit_id": 5003,
    "tags": ["Sensor_Temp"],
    "status": "RUNNING",
    "status_timestamp": new Date("2025-07-16T08:00:00Z")
  }
]);

// Create indexes for better performance
db.devices.createIndex({ "device_id": 1 });
db.current_values.createIndex({ "tag": 1 });
db.current_values.createIndex({ "device_id": 1 });
db.hourly_agg.createIndex({ "tag": 1, "hour": 1 });
db.daily_agg.createIndex({ "tag": 1, "day": 1 });
db.device_status_history.createIndex({ "device_id": 1, "timestamp": -1 });

print("✅ MongoDB initialization completed successfully!");
print("📊 Inserted " + db.devices.count() + " devices");
print("🏷️  Available tags:", db.devices.distinct("tags"));