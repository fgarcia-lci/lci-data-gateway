
CREATE DATABASE IF NOT EXISTS historian;
USE historian;

CREATE TABLE IF NOT EXISTS TagValue (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  tag VARCHAR(100),
  device_id VARCHAR(100),
  timestamp DATETIME,
  value DOUBLE,
  unit VARCHAR(10)
);

-- Auto-cleanup: delete TagValue records older than 7 days, runs daily at 3:00 AM
SET GLOBAL event_scheduler = ON;

DROP EVENT IF EXISTS cleanup_old_tag_values;
CREATE EVENT cleanup_old_tag_values
ON SCHEDULE EVERY 1 DAY STARTS CURRENT_DATE + INTERVAL 10 HOUR
DO
  DELETE FROM TagValue WHERE timestamp < NOW() - INTERVAL 7 DAY;
