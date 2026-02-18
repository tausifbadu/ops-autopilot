import argparse
import random
import sys
from datetime import datetime, timedelta

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, TimestampType, IntegerType, DoubleType, DateType
)

TARGET_METERS = [
    ("cbb74f22-9059-4fec-ae2a-1c4defdebc1a", 15),
    ("16f7c12b-d97b-41e9-a04a-49b0c49b0fb6", 15),
    ("b0ec0b81-d0ab-4853-8b3f-6b8634b0203d", 15),
    ("9e1eadb5-c3df-4f5c-b1f2-cec2639a98e1", 15),
    ("6e5a5eef-128d-449c-bfa8-26a2c59acf1c", 15),
    ("8b49ebe1-e9d9-4601-a8c7-cc1b0ae3c76f", 30),
    ("0d8f38b7-8359-4002-b9aa-dc0ddfa20c6d", 30),
    ("8e0d1688-2121-4825-9fdc-ff532d61798d", 30),
    ("41e06ced-5852-4ac3-aa66-c8317522d834", 30),
    ("9713916f-9533-45fe-b554-8ff7897f06bc", 30),
]

TARGET_TABLE = "updated_meter_reading"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-prefix", default="raw/electric-raw-dev")
    parser.add_argument("--target-year", type=int, default=2026)
    parser.add_argument("--target-month", type=int, default=1)
    parser.add_argument("--target-day", type=int, default=20)
    args, _ = parser.parse_known_args()
    return args


def main():
    glue_args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    job_name = glue_args["JOB_NAME"]

    sc = SparkContext.getOrCreate()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session

    # ---- HARDEN SPARK PARQUET BEHAVIOR (compat across Spark/EMR versions) ----
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    # Ensure Parquet timestamps are written in MICROS (not NANOS)
    spark.conf.set("spark.sql.parquet.outputTimestampType", "TIMESTAMP_MICROS")
    # Avoid schema merge surprises later
    spark.conf.set("spark.sql.parquet.mergeSchema", "false")
    # Optional workaround for strict vectorized read issues in mixed-schema lakes
    # spark.conf.set("spark.sql.parquet.enableVectorizedReader", "false")

    job = Job(glue_context)
    job.init(job_name, glue_args)

    args = parse_args()
    random.seed(42)

    schema = StructType([
        StructField("meter_id", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("interval_minutes", IntegerType(), True),
        StructField("kwh", DoubleType(), True),
        StructField("load_date", DateType(), True),
        StructField("year", IntegerType(), True),
        StructField("month", IntegerType(), True),
        StructField("day", IntegerType(), True),
    ])

    rows = []
    day_start = datetime(args.target_year, args.target_month, args.target_day, 0, 0, 0)
    load_date = day_start.date()

    for meter_id, interval_minutes in TARGET_METERS:
        interval_minutes = int(interval_minutes)
        expected = 96 if interval_minutes == 15 else 48
        for i in range(expected):
            ts = day_start + timedelta(minutes=interval_minutes * i)
            rows.append((
                str(meter_id),
                ts,                      # Python datetime -> TimestampType
                interval_minutes,         # int
                float(round(random.uniform(0.1, 5.0), 3)),
                load_date,                # Python date -> DateType
                int(args.target_year),
                int(args.target_month),
                int(args.target_day),
            ))

    updated_meter_reading = spark.createDataFrame(rows, schema=schema)

    # Validate required count per interval: 15m -> 96, 30m -> 48, for each target meter.
    expected_by_interval = spark.createDataFrame(
        [(15, 96), (30, 48)],
        ["interval_minutes", "expected_count"]
    )

    actual_counts = (
        updated_meter_reading
        .groupBy("meter_id", "interval_minutes")
        .agg(F.count(F.lit(1)).alias("actual_count"))
        .join(expected_by_interval, on="interval_minutes", how="inner")
        .filter(F.col("actual_count") != F.col("expected_count"))
    )

    if actual_counts.limit(1).count() > 0:
        actual_counts.show(50, truncate=False)
        raise ValueError("Generated record count mismatch for one or more target meters.")

    output_path = (
        f"s3://{args.output_bucket}/"
        f"{args.output_prefix.strip('/')}/"
        f"{TARGET_TABLE}/"
    )

    (
        updated_meter_reading.write
        .mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(output_path)
    )

    job.commit()


if __name__ == "__main__":
    main()
