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
    WITH summer_hourly AS (
      SELECT
        meter_id,
        date_trunc('hour', `timestamp`) AS hour_timestamp,
        round(SUM(kwh), 2) AS sum_hourly
      FROM `{input_db}`.`meter_usage`
      WHERE month(`timestamp`) IN (6, 7, 8)
      GROUP BY meter_id, date_trunc('hour', `timestamp`)
    ),
    summer_ranked AS (
      SELECT
        meter_id,
        hour_timestamp AS summer_time,
        sum_hourly AS summer_max,
        row_number() OVER (PARTITION BY meter_id ORDER BY sum_hourly DESC) AS rn
      FROM summer_hourly
    ),
    winter_hourly AS (
      SELECT
        meter_id,
        date_trunc('hour', `timestamp`) AS hour_timestamp,
        round(SUM(kwh), 2) AS sum_hourly
      FROM `{input_db}`.`meter_usage`
      WHERE month(`timestamp`) IN (12, 1, 2)
      GROUP BY meter_id, date_trunc('hour', `timestamp`)
    ),
    winter_ranked AS (
      SELECT
        meter_id,
        hour_timestamp AS winter_time,
        sum_hourly AS winter_max,
        row_number() OVER (PARTITION BY meter_id ORDER BY sum_hourly DESC) AS rn
      FROM winter_hourly
    )
    SELECT
      w.meter_id,
      w.winter_time,
      w.winter_max,
      s.summer_time,
      s.summer_max
    FROM winter_ranked w
    INNER JOIN summer_ranked s
      ON w.meter_id = s.meter_id
    WHERE w.rn = 1 AND s.rn = 1
    """

    peak_hour_df = spark.sql(query)

    (
        peak_hour_df.write
        .mode("overwrite")
        .parquet(output_path)
    )

    spark.stop()


if __name__ == "__main__":
    main()
