import json
import random
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from kafka import KafkaProducer

# ---------- SETTINGS ----------
TZ = ZoneInfo("America/Chicago")
BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP", "kafka:29092")
TOPIC = os.environ.get("TOPIC", "meter_voltage_live") # Updated Topic Name

METER_MIN = 1
METER_MAX = 500
VOLT_MIN = 114.0  # Typical residential low
VOLT_MAX = 126.0  # Typical residential high
RECORDS_PER_BATCH = 30  

producer = KafkaProducer(
    bootstrap_servers=BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def generate_batch():
    # Uses current time for the batch start
    start_time = datetime.now(TZ).replace(second=0, microsecond=0)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {RECORDS_PER_BATCH} voltage records...")
    
    for i in range(RECORDS_PER_BATCH):
        # Spreading records by 1 second intervals within the batch
        ts = start_time + timedelta(seconds=i)
        
        payload = {
            "meter_id": f"meter-{random.randint(METER_MIN, METER_MAX)}",
            "timestamp": ts.isoformat(),
            "voltage": round(random.uniform(VOLT_MIN, VOLT_MAX), 2), # Changed from kwh
            "interval_minutes": 15
        }

        producer.send(TOPIC, value=payload)
    
    producer.flush()
    print(f"Batch sent to topic: {TOPIC}")

if __name__ == "__main__":
    print("Generator started. Press Ctrl+C to stop.")
    try:
        while True:
            generate_batch()
            print("Sleeping for 60 seconds...")
            time.sleep(60) 
    except KeyboardInterrupt:
        print("Generator stopped by user.")
