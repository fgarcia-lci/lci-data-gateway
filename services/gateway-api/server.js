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

// Basic pagination helpers
const PAGE_DEFAULT = 1;
const PAGE_SIZE_DEFAULT = 50;
const PAGE_SIZE_MAX = 200;

function parsePagination(req) {
  const page = Math.max(PAGE_DEFAULT, parseInt(req.query.page || PAGE_DEFAULT, 10) || PAGE_DEFAULT);
  const pageSizeRaw = parseInt(req.query.pageSize || PAGE_SIZE_DEFAULT, 10) || PAGE_SIZE_DEFAULT;
  const pageSize = Math.min(PAGE_SIZE_MAX, Math.max(1, pageSizeRaw));
  const skip = (page - 1) * pageSize;
  return { page, pageSize, skip };
}

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
    const { page, pageSize, skip } = parsePagination(req);
    const db = mongoClient.db('gateway');

    // Fetch paginated devices with a light projection
    const devicesCollection = db.collection('devices');
    const total = await devicesCollection.estimatedDocumentCount();
    const devices = await devicesCollection
      .find(
        {},
        {
          projection: {
            device_id: 1,
            name: 1,
            xeokit_id: 1,
            tags: 1,
            status: 1,
            status_timestamp: 1
          }
        }
      )
      .sort({ device_id: 1 })
      .skip(skip)
      .limit(pageSize)
      .toArray();

    // Fetch current values only for tags in this page to reduce load
    const tagList = devices.flatMap(d => d.tags || []);
    let currentValues = [];
    if (tagList.length > 0) {
      currentValues = await db.collection('current_values')
        .find(
          { tag: { $in: tagList } },
          { projection: { tag: 1, device_id: 1, value: 1, unit: 1, timestamp: 1 } }
        )
        .toArray();
    }

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
    
    res.json({
      page,
      pageSize,
      total,
      items: devicesWithData
    });
  } catch (error) {
    console.error('Error fetching devices:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Get historical data for a specific device and tag
app.get('/api/history/:deviceId/:tag', async (req, res) => {
  try {
    const { deviceId, tag } = req.params;
    const { hours = 24, limit = 500 } = req.query;
    
    const hoursAgo = new Date(Date.now() - hours * 60 * 60 * 1000);
    const safeLimit = Math.min(2000, Math.max(1, parseInt(limit, 10) || 500));
    
    const [rows] = await mysqlConnection.execute(
      'SELECT timestamp, value, unit FROM TagValue WHERE device_id = ? AND tag = ? AND timestamp >= ? ORDER BY timestamp DESC LIMIT ?',
      [deviceId, tag, hoursAgo, safeLimit]
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
