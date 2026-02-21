import sys
from pyspark.sql import SparkSession


def get_arg(flag: str) -> str:
    if flag not in sys.argv:
        raise ValueError(f"Missing arg {flag}")
    i = sys.argv.index(flag)
    if i + 1 >= len(sys.argv):
        raise ValueError(f"Missing value for {flag}")
    return sys.argv[i + 1]


def main():
    job_name = get_arg("--JOB_NAME")
    input_db = get_arg("--INPUT_DB")
    output_path = get_arg("--OUTPUT_PATH").rstrip("/") + "/"

    spark = (
        SparkSession.builder
        .appName(job_name)
        .enableHiveSupport()
        .getOrCreate()
    )

    query = f"""
    SELECT
        tmm.transformer_id,
        year(mu.`timestamp`) AS year,
        month(mu.`timestamp`) AS month,
        day(mu.`timestamp`) AS day,
        ROUND(SUM(mu.kwh), 2) AS daily_usage_kwh,
        date_trunc('day', mu.`timestamp`) AS usage_timestamp,
        current_date() AS load_date,
        current_timestamp() AS load_datetime
    FROM `{input_db}`.`meter_usage` AS mu
    JOIN `{input_db}`.`transformer_meter_mapping` AS tmm
      ON mu.meter_id = tmm.meter_id
    GROUP BY
        tmm.transformer_id,
        year(mu.`timestamp`),
        month(mu.`timestamp`),
        day(mu.`timestamp`),
        date_trunc('day', mu.`timestamp`)
    """

    df = spark.sql(query)
    (
        df.write
        .mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(output_path)
    )

    spark.stop()


if __name__ == "__main__":
    main()
