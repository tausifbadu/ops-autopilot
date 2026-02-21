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
    WITH hourly_usage AS (
        SELECT
            date_trunc('hour', mu.`timestamp`) AS hour_timestamp,
            SUM(mu.kwh) AS sum_hourly,
            tmm.transformer_id,
            year(mu.`timestamp`) AS year,
            month(mu.`timestamp`) AS month,
            day(mu.`timestamp`) AS day
        FROM `{input_db}`.`meter_usage` AS mu
        JOIN `{input_db}`.`transformer_meter_mapping` AS tmm
          ON mu.meter_id = tmm.meter_id
        GROUP BY
            tmm.transformer_id,
            date_trunc('hour', mu.`timestamp`),
            year(mu.`timestamp`),
            month(mu.`timestamp`),
            day(mu.`timestamp`)
    ),
    season_tagged AS (
        SELECT
            *,
            CASE
                WHEN month IN (6, 7, 8, 9) THEN 'summer'
                WHEN month IN (12, 1, 2) THEN 'winter'
            END AS season
        FROM hourly_usage
    ),
    ranked AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY transformer_id, season
                ORDER BY sum_hourly DESC
            ) AS rn
        FROM season_tagged
        WHERE season IS NOT NULL
    ),
    season_max AS (
        SELECT
            transformer_id,
            season,
            sum_hourly AS season_max,
            hour_timestamp AS season_max_timestamp
        FROM ranked
        WHERE rn = 1
    )
    SELECT
        h.hour_timestamp,
        h.sum_hourly,
        h.transformer_id,
        h.year,
        h.month,
        h.day,
        w.season_max AS winter_max,
        w.season_max_timestamp AS winter_max_timestamp,
        s.season_max AS summer_max,
        s.season_max_timestamp AS summer_max_timestamp
    FROM hourly_usage h
    LEFT JOIN season_max w
      ON h.transformer_id = w.transformer_id
     AND w.season = 'winter'
    LEFT JOIN season_max s
      ON h.transformer_id = s.transformer_id
     AND s.season = 'summer'
    """

    peak_df = spark.sql(query)

    (
        peak_df.write
        .mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(output_path)
    )

    spark.stop()


if __name__ == "__main__":
    main()
