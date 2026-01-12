// mongodb/init.js
db = db.getSiblingDB('gateway');

// Load devices from JSON file mounted in /docker-entrypoint-initdb.d/devices.json
const devicesJson = cat('/docker-entrypoint-initdb.d/devices.json');
const devices = JSON.parse(devicesJson);

// Create devices collection and insert initial data
db.devices.insertMany(devices);

// Create indexes for better performance
db.devices.createIndex({ "device_id": 1 });
db.current_values.createIndex({ "tag": 1 });
db.current_values.createIndex({ "device_id": 1 });
db.hourly_agg.createIndex({ "tag": 1, "hour": 1 });
db.daily_agg.createIndex({ "tag": 1, "day": 1 });
db.device_status_history.createIndex({ "device_id": 1, "timestamp": -1 });

print("MongoDB initialization completed successfully!");
print("Inserted " + db.devices.count() + " devices");
print("Available tags:", db.devices.distinct("tags"));
