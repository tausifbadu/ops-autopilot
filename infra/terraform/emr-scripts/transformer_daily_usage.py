import sys
from pyspark.sql import SparkSession, functions as F


def get_arg(flag: str) -> str:
    if flag not in sys.argv:
        raise ValueError(f"Missing arg {flag}")
    i = sys.argv.index(flag)
    if i + 1 >= len(sys.argv):
        raise ValueError(f"Missing value for {flag}")
    return sys.argv[i + 1]


def main():
    job_name = get_arg("--JOB_NAME")
    input_path = get_arg("--INPUT_PATH").rstrip("/") + "/"
    output_path = get_arg("--OUTPUT_PATH").rstrip("/") + "/"

    spark = SparkSession.builder.appName(job_name).getOrCreate()

    meter_usage = spark.read.parquet(f"{input_path}meter_usage/")
    transformer_meter = spark.read.parquet(f"{input_path}transformer_meter_mapping/")

    usage = meter_usage.withColumn("usage_date", F.to_date(F.col("timestamp")))
    joined = usage.join(transformer_meter, on="meter_id", how="inner")

    daily = (
        joined.groupBy("transformer_id", "usage_date")
        .agg(
            F.sum("kwh").alias("total_kwh"),
            F.max("kwh").alias("peak_kwh"),
            F.avg("kwh").alias("avg_kwh"),
        )
    )

    daily = (
        daily.withColumn("year", F.year("usage_date"))
        .withColumn("month", F.month("usage_date"))
        .withColumn("day", F.dayofmonth("usage_date"))
    )

    daily.write.mode("overwrite").partitionBy("year", "month", "day").parquet(output_path)

    spark.stop()


if __name__ == "__main__":
    main()
