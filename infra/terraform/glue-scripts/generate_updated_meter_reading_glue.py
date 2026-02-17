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
    ("51925845-d616-4481-88ce-832e1ed00863", 15),
    ("fe635107-a078-4f05-a45b-a13d761f82fa", 15),
    ("f241eb7e-6fc8-44c4-b816-d3b39d29edd8", 15),
    ("7f386d71-f0be-45e4-af12-5bd79ee2fb3d", 15),
    ("0a3c1c31-b01e-49fa-a09c-7236f9658ed1", 30),
    ("05468681-18b0-4b66-8249-fd4c2d9f96d8", 30),
    ("2f17129e-74b5-447d-9a7d-69a7afb9cb6d", 15),
    ("1d86bb07-fced-4e8c-8d61-ac9d6fe728ea", 30),
    ("9c967b58-4172-4066-b016-27c6fa516e31", 15),
    ("35505444-9000-4dcc-965d-2ff85de60d4b", 30),
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
