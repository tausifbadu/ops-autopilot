import mysql.connector
import time
import random

config = {
    'host': 'mysql',
    'user': 'root',
    'password': 'mysecret8050',
    'database': 'meter_kafka_test',
    'autocommit': True
}

def connect_to_mysql():
    while True:
        try:
            print("Attempting to connect to MySQL...")
            conn = mysql.connector.connect(**config)
            print("Connected to MySQL successfully!")
            return conn
        except mysql.connector.Error as err:
            print(f"Connection failed: {err}. Retrying in 5 seconds...")
            time.sleep(5)

db = connect_to_mysql()
cursor = db.cursor()

# Continuous loop for batch generation
try:
    while True:
        print(f"Starting batch of 100 readings...")
        
        data_batch = []
        for _ in range(100):
            meter_id = f"METER-{random.randint(1000, 9999)}"
            usage = round(random.uniform(0.1, 10.0), 2)
            data_batch.append((meter_id, usage))
        
        # Batch insert for efficiency
        insert_query = "INSERT INTO readings (meter_id, usage_kwh) VALUES (%s, %s)"
        cursor.executemany(insert_query, data_batch)
        
        print(f"Batch complete. 100 rows inserted. Sleeping for 60 seconds...")
        time.sleep(60)
        
except KeyboardInterrupt:
    print("Stopping generator...")
finally:
    cursor.close()
    db.close()