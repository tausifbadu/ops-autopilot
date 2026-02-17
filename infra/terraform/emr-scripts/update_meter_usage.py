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
    output_path = get_arg("--OUTPUT_PATH").rstrip("/") + "/"

    spark = (
        SparkSession.builder
        .appName(job_name)
        .enableHiveSupport()
        .getOrCreate()
    )
    spark.conf.set("spark.sql.parquet.enableVectorizedReader", "false")

    total_kwh_before_update = spark.sql(""" select sum(mu.kwh) 
                                        from `electric-raw-dev`.`meter_usage` as mu
                                        left anti join `electric-raw-dev`.`updated_meter_reading` as u
                                            on mu.meter_id = u.meter_id and mu.timestamp = u.timestamp
                                        where day = 20""").first()[0]

    updated_df = spark.sql(""" SELECT mu.meter_id, mu.timestamp, mu.interval_minutes, COALESCE(u.kwh, mu.kwh) AS kwh, mu.load_date, mu.year, mu.month, mu.day
                            FROM `electric-raw-dev`.`meter_usage` as mu
                            LEFT JOIN `electric-raw-dev`.`updated_meter_reading` as u
                              ON mu.meter_id = u.meter_id AND mu.timestamp = u.timestamp
                            WHERE mu.day = 20""")

    updated_df.createOrReplaceTempView("updated_meter_view")

    total_kwh_after_update = spark.sql(""" select sum(uu.kwh) 
                                        from updated_meter_view as uu
                                        left anti join `electric-raw-dev`.`updated_meter_reading` as u
                                            on uu.meter_id = u.meter_id and uu.timestamp = u.timestamp
                                        where day = 20""").first()[0]

    if total_kwh_before_update != total_kwh_after_update:
        raise ValueError("Validation failed: total_kwh mismatch before vs after update.")

    (
        updated_df.write
        .mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(f"{output_path}meter_usage/")
    )

    spark.stop()


if __name__ == "__main__":
    main()