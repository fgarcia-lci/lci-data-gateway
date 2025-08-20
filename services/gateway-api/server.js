// services/gateway-api/server.js
const express = require('express');
const cors = require('cors');
const { MongoClient } = require('mongodb');
const mysql = require('mysql2/promise');

const app = express();
const PORT = 3001;

// Enable CORS for XeoKit frontend
app.use(cors());
app.use(express.json());

// Database connections
let mongoClient, mysqlConnection;

// Initialize database connections
async function initDatabases() {
  try {
    // MongoDB connection
    mongoClient = new MongoClient('mongodb://mongodb:27017');
    await mongoClient.connect();
    console.log('✅ Connected to MongoDB');

    // MySQL connection
    mysqlConnection = await mysql.createConnection({
      host: 'mysql',
      port: 3306,
      user: 'root',
      password: 'root',
      database: 'historian'
    });
    console.log('✅ Connected to MySQL');
  } catch (error) {
    console.error('❌ Database connection error:', error);
    process.exit(1);
  }
}

// API Routes

// Get all devices with current status and latest values
app.get('/api/devices', async (req, res) => {
  try {
    const db = mongoClient.db('gateway');
    
    // Get devices with their current status
    const devices = await db.collection('devices').find({}).toArray();
    
    // Get current values for all tags
    const currentValues = await db.collection('current_values').find({}).toArray();
    
    // Combine device info with current values
    const devicesWithData = devices.map(device => {
      const deviceValues = currentValues.filter(val => val.device_id === device.device_id);
      
      // Calculate derived metrics
      let efficiency = 0;
      let rpm = 0;
      let temperature = 0;
      
      deviceValues.forEach(val => {
        if (val.tag.includes('Speed')) rpm = val.value;
        if (val.tag.includes('Temp')) temperature = val.value;
      });
      
      // Simple efficiency calculation based on temperature and speed
      if (rpm > 0 && temperature > 0) {
        efficiency = Math.max(0, Math.min(100, 100 - (temperature - 70) * 2 - (Math.abs(rpm - 2000) / 50)));
      }
      
      return {
        ...device,
        currentValues: deviceValues,
        metrics: {
          rpm: Math.round(rpm),
          efficiency: Math.round(efficiency * 10) / 10,
          temperature: Math.round(temperature * 10) / 10,
          voltage: device.device_id.includes('PM') ? '400V' : '220V',
          current: device.device_id.includes('PM') ? '10A' : '5A'
        }
      };
    });
    
    res.json(devicesWithData);
  } catch (error) {
    console.error('Error fetching devices:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get historical data for a specific device and tag
app.get('/api/history/:deviceId/:tag', async (req, res) => {
  try {
    const { deviceId, tag } = req.params;
    const { hours = 24 } = req.query;
    
    const hoursAgo = new Date(Date.now() - hours * 60 * 60 * 1000);
    
    const [rows] = await mysqlConnection.execute(
      'SELECT timestamp, value FROM TagValue WHERE device_id = ? AND tag = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT 1000',
      [deviceId, tag, hoursAgo]
    );
    
    res.json(rows);
  } catch (error) {
    console.error('Error fetching history:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get device status history
app.get('/api/status-history/:deviceId', async (req, res) => {
  try {
    const { deviceId } = req.params;
    const { hours = 24 } = req.query;
    
    const db = mongoClient.db('gateway');
    const hoursAgo = new Date(Date.now() - hours * 60 * 60 * 1000);
    
    const statusHistory = await db.collection('device_status_history')
      .find({ 
        device_id: deviceId, 
        timestamp: { $gte: hoursAgo } 
      })
      .sort({ timestamp: -1 })
      .limit(100)
      .toArray();
    
    res.json(statusHistory);
  } catch (error) {
    console.error('Error fetching status history:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Start server
async function startServer() {
  await initDatabases();
  
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 Gateway API server running on port ${PORT}`);
    console.log(`📡 Available endpoints:`);
    console.log(`   GET /api/devices - Get all devices with current data`);
    console.log(`   GET /api/history/:deviceId/:tag - Get historical data`);
    console.log(`   GET /api/status-history/:deviceId - Get status history`);
  });
}

startServer().catch(console.error);