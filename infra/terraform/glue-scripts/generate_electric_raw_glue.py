import argparse
import random
import sys
import uuid
from datetime import date, datetime, timedelta

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    DateType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


METER_TYPES = ["smart", "analog", "digital"]
PLAN_TYPES = ["standard", "time_of_use", "green", "fixed"]
STATUS_TYPES = ["active", "expired", "terminated"]
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa", "Edward", "Deborah",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
]


def rand_phone():
    return f"+1{random.randint(2000000000, 9999999999)}"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-prefix", default="raw/electric-raw-dev")
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--tables", default="all", help="Comma-separated table names or 'all'")
    args, _ = parser.parse_known_args()
    return args


def as_df(spark: SparkSession, rows, schema: StructType):
    return spark.createDataFrame(rows, schema=schema)


def write_parquet(df, path: str, partition_cols=None):
    if partition_cols:
        (
            df.write
            .mode("overwrite")
            .partitionBy(*partition_cols)
            .parquet(path)
        )
    else:
        (
            df.coalesce(1).write
            .mode("overwrite")
            .parquet(path)
        )


def main():
    glue_args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    job_name = glue_args["JOB_NAME"]

    sc = SparkContext.getOrCreate()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(job_name, glue_args)

    args = parse_args()
    random.seed(42)

    base = f"s3://{args.output_bucket}/{args.output_prefix.strip('/')}"
    row_cap = min(10000, int(args.max_rows))
    selected = {t.strip() for t in args.tables.split(",")} if args.tables != "all" else "all"

    def want(table_name: str) -> bool:
        return selected == "all" or table_name in selected

    # customer
    customer_rows = []
    for _ in range(row_cap):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        customer_rows.append((
            str(uuid.uuid4()),
            first,
            last,
            f"{first}{last}@mail.com".lower(),
            rand_phone(),
            f"{random.randint(100, 9999)} Main St",
            "Chicago",
            "IL",
            f"{random.randint(60000, 62999)}",
            "US",
            date(2020, 1, 1) + timedelta(days=random.randint(0, 2000)),
        ))
    customer_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("address", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("postal_code", StringType(), True),
        StructField("country", StringType(), True),
        StructField("signup_date", DateType(), True),
    ])
    customers_df = as_df(spark, customer_rows, customer_schema)
    customer_ids = [r[0] for r in customer_rows]

    # agreements
    agreement_rows = []
    for _ in range(row_cap):
        customer_id = random.choice(customer_ids)
        start = date(2022, 1, 1) + timedelta(days=random.randint(0, 700))
        end = start + timedelta(days=random.randint(180, 730))
        status = random.choice(STATUS_TYPES)
        agreement_rows.append((
            str(uuid.uuid4()),
            customer_id,
            start,
            None if status == "active" else end,
            random.choice(PLAN_TYPES),
            status,
            float(round(random.uniform(30, 250), 2)),
        ))
    agreement_schema = StructType([
        StructField("agreement_id", StringType(), False),
        StructField("customer_id", StringType(), False),
        StructField("contract_start_date", DateType(), True),
        StructField("contract_end_date", DateType(), True),
        StructField("plan_type", StringType(), True),
        StructField("status", StringType(), True),
        StructField("monthly_fee_usd", DoubleType(), True),
    ])
    agreements_df = as_df(spark, agreement_rows, agreement_schema)

    # meters
    meter_rows = []
    for _ in range(row_cap):
        meter_rows.append((
            str(uuid.uuid4()),
            random.choice([15, 30]),
            random.choice(METER_TYPES),
            date(2019, 1, 1) + timedelta(days=random.randint(0, 2000)),
            random.choice(["active", "inactive"]),
            random.choice(["GE", "Siemens", "ABB", "Schneider"]),
        ))
    meter_schema = StructType([
        StructField("meter_id", StringType(), False),
        StructField("interval_minutes", IntegerType(), True),
        StructField("meter_type", StringType(), True),
        StructField("install_date", DateType(), True),
        StructField("status", StringType(), True),
        StructField("manufacturer", StringType(), True),
    ])
    meters_df = as_df(spark, meter_rows, meter_schema)
    meter_ids = [r[0] for r in meter_rows]
    meter_interval = {r[0]: r[1] for r in meter_rows}

    # meter geo
    meter_geo_rows = []
    for meter_id in meter_ids:
        meter_geo_rows.append((
            meter_id,
            float(round(random.uniform(25.0, 49.5), 6)),
            float(round(random.uniform(-124.7, -66.9), 6)),
            "America/Chicago",
            datetime(2026, 1, 1) + timedelta(days=random.randint(0, 30)),
        ))
    meter_geo_schema = StructType([
        StructField("meter_id", StringType(), False),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("timezone", StringType(), True),
        StructField("updated_at", TimestampType(), True),
    ])
    meter_geo_df = as_df(spark, meter_geo_rows, meter_geo_schema)

    # transformers
    transformer_rows = []
    for _ in range(row_cap):
        transformer_rows.append((
            str(uuid.uuid4()),
            f"sub-{uuid.uuid4().hex[:6]}",
            float(random.choice([25, 50, 100, 250, 500])),
            random.choice(["active", "inactive"]),
            date(2018, 1, 1) + timedelta(days=random.randint(0, 2000)),
        ))
    transformer_schema = StructType([
        StructField("transformer_id", StringType(), False),
        StructField("substation_id", StringType(), True),
        StructField("capacity_kva", DoubleType(), True),
        StructField("status", StringType(), True),
        StructField("install_date", DateType(), True),
    ])
    transformers_df = as_df(spark, transformer_rows, transformer_schema)
    transformer_ids = [r[0] for r in transformer_rows]

    # transformer geo
    transformer_geo_rows = []
    for transformer_id in transformer_ids:
        transformer_geo_rows.append((
            transformer_id,
            float(round(random.uniform(25.0, 49.5), 6)),
            float(round(random.uniform(-124.7, -66.9), 6)),
            datetime(2026, 1, 1) + timedelta(days=random.randint(0, 30)),
        ))
    transformer_geo_schema = StructType([
        StructField("transformer_id", StringType(), False),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("updated_at", TimestampType(), True),
    ])
    transformer_geo_df = as_df(spark, transformer_geo_rows, transformer_geo_schema)

    # customer-meter mapping (1:1 randomized)
    shuffled_meter_ids = meter_ids[:]
    random.shuffle(shuffled_meter_ids)
    customer_meter_rows = []
    for i, customer_id in enumerate(customer_ids):
        customer_meter_rows.append((
            customer_id,
            shuffled_meter_ids[i],
            date(2025, 6, 1) + timedelta(days=random.randint(0, 30)),
            None,
        ))
    customer_meter_schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("meter_id", StringType(), False),
        StructField("effective_start", DateType(), True),
        StructField("effective_end", DateType(), True),
    ])
    customer_meter_df = as_df(spark, customer_meter_rows, customer_meter_schema)
    customer_to_meter = {r[0]: r[1] for r in customer_meter_rows}

    # transformer-meter mapping
    transformer_meter_rows = []
    for meter_id in meter_ids:
        transformer_meter_rows.append((
            random.choice(transformer_ids),
            meter_id,
            date(2025, 1, 1) + timedelta(days=random.randint(0, 30)),
            None,
        ))
    transformer_meter_schema = StructType([
        StructField("transformer_id", StringType(), False),
        StructField("meter_id", StringType(), False),
        StructField("effective_start", DateType(), True),
        StructField("effective_end", DateType(), True),
    ])
    transformer_meter_df = as_df(spark, transformer_meter_rows, transformer_meter_schema)

    # writes for non-partitioned tables
    if want("customer"):
        write_parquet(customers_df, f"{base}/customer")
    if want("customer_agreement_table"):
        write_parquet(agreements_df, f"{base}/customer_agreement_table")
    if want("meter"):
        write_parquet(meters_df, f"{base}/meter")
    if want("meter_geo_location"):
        write_parquet(meter_geo_df, f"{base}/meter_geo_location")
    if want("transformer_table"):
        write_parquet(transformers_df, f"{base}/transformer_table")
    if want("transformer_geo_location"):
        write_parquet(transformer_geo_df, f"{base}/transformer_geo_location")
    if want("transformer_meter_mapping"):
        write_parquet(transformer_meter_df, f"{base}/transformer_meter_mapping")
    if want("customer_meter_mapping"):
        write_parquet(customer_meter_df, f"{base}/customer_meter_mapping")

    if want("meter_usage"):
        contract_date = date(2026, 1, 1)
        active_customers = set()
        for row in agreement_rows:
            _, customer_id, start, end, _, status, _ = row
            if status == "active" and start <= contract_date and (end is None or end >= contract_date):
                active_customers.add(customer_id)

        eligible_meter_ids = [customer_to_meter[cid] for cid in active_customers if cid in customer_to_meter]
        usage_rows = []
        for meter_id in eligible_meter_ids:
            interval = int(meter_interval.get(meter_id, 15))
            if interval not in (15, 30):
                continue
            per_day = 96 if interval == 15 else 48
            for d in range(1, 32):
                day = date(2026, 1, d)
                start_dt = datetime(day.year, day.month, day.day, 0, 0, 0)
                for i in range(per_day):
                    usage_rows.append((
                        meter_id,
                        start_dt + timedelta(minutes=interval * i),
                        interval,
                        float(round(random.uniform(0.1, 5.0), 3)),
                        datetime.utcnow().date(),
                        day.year,
                        day.month,
                        day.day,
                    ))

        usage_schema = StructType([
            StructField("meter_id", StringType(), False),
            StructField("timestamp", TimestampType(), True),
            StructField("interval_minutes", IntegerType(), True),
            StructField("kwh", DoubleType(), True),
            StructField("load_date", DateType(), True),
            StructField("year", IntegerType(), True),
            StructField("month", IntegerType(), True),
            StructField("day", IntegerType(), True),
        ])
        usage_df = as_df(spark, usage_rows, usage_schema)
        write_parquet(usage_df, f"{base}/meter_usage", partition_cols=["year", "month", "day"])

    job.commit()


if __name__ == "__main__":
    main()
