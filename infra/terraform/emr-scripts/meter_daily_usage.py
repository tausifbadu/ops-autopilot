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
    output_db = get_arg("--OUTPUT_DB")
    output_table = get_arg("--OUTPUT_TABLE")
    output_path = get_arg("--OUTPUT_PATH").rstrip("/") + "/"

    spark = (
        SparkSession.builder
        .appName(job_name)
        .enableHiveSupport()
        .getOrCreate()
    )

    query = f"""
    WITH meter_hourly AS (
        SELECT
            meter_id,
            date_trunc('hour', `timestamp`) AS hour_timestamp,
            year(`timestamp`) AS year,
            month(`timestamp`) AS month,
            day(`timestamp`) AS day,
            hour(`timestamp`) AS hour,
            ROUND(SUM(kwh), 2) AS sum_hourly
        FROM `{input_db}`.`meter_usage`
        GROUP BY
            meter_id,
            date_trunc('hour', `timestamp`),
            year(`timestamp`),
            month(`timestamp`),
            day(`timestamp`),
            hour(`timestamp`)
    ),
    daily_pivot AS (
        SELECT *
        FROM (
            SELECT
                meter_id,
                date_trunc('day', hour_timestamp) AS usage_date,
                year,
                month,
                day,
                hour,
                sum_hourly
            FROM meter_hourly
        ) src
        PIVOT (
            SUM(sum_hourly) FOR hour IN (
                0,1,2,3,4,5,6,7,8,9,10,11,
                12,13,14,15,16,17,18,19,20,21,22,23
            )
        )
    )
    SELECT
        meter_id,
        usage_date,
        year,
        month,
        day,
        `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`,
        `12`, `13`, `14`, `15`, `16`, `17`, `18`, `19`, `20`, `21`, `22`, `23`,
        ROUND(
            COALESCE(`0`, 0) + COALESCE(`1`, 0) + COALESCE(`2`, 0) + COALESCE(`3`, 0) +
            COALESCE(`4`, 0) + COALESCE(`5`, 0) + COALESCE(`6`, 0) + COALESCE(`7`, 0) +
            COALESCE(`8`, 0) + COALESCE(`9`, 0) + COALESCE(`10`, 0) + COALESCE(`11`, 0) +
            COALESCE(`12`, 0) + COALESCE(`13`, 0) + COALESCE(`14`, 0) + COALESCE(`15`, 0) +
            COALESCE(`16`, 0) + COALESCE(`17`, 0) + COALESCE(`18`, 0) + COALESCE(`19`, 0) +
            COALESCE(`20`, 0) + COALESCE(`21`, 0) + COALESCE(`22`, 0) + COALESCE(`23`, 0),
            2
        ) AS daily_usage_sum,
        current_date() AS load_date,
        current_timestamp() AS load_datetime
    FROM daily_pivot
    """

    df = spark.sql(query)

    target_table = f"`{output_db}`.`{output_table}`"

    (
        df.write
        .mode("overwrite")
        .format("parquet")
        .option("path", output_path)
        .partitionBy("year", "month", "day")
        .saveAsTable(target_table)
    )

    spark.sql(f"MSCK REPAIR TABLE {target_table}")
    spark.stop()


if __name__ == "__main__":
    main()
