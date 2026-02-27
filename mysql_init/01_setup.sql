CREATE DATABASE IF NOT EXISTS meter_kafka_test;
USE meter_kafka_test;

CREATE TABLE IF NOT EXISTS readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meter_id VARCHAR(50),
    usage_kwh DECIMAL(10,2),
    reading_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE USER IF NOT EXISTS 'debezium'@'%' IDENTIFIED BY 'dbz_secure_2026';
GRANT SELECT, RELOAD, SHOW DATABASES, REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'debezium'@'%';
-- Ensure root can connect from the generator
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'mysecret8050';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';
FLUSH PRIVILEGES;