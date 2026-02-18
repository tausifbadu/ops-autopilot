import argparse
import calendar

from pyspark.sql import SparkSession, functions as F


def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "fall"


def _state_multiplier_expr(season: str):
    mult = {
        "winter": {"NY": 1.28, "NJ": 1.22, "DE": 1.18, "CT": 1.25},
        "spring": {"NY": 0.95, "NJ": 0.96, "DE": 0.97, "CT": 0.95},
        "summer": {"NY": 1.12, "NJ": 1.16, "DE": 1.14, "CT": 1.10},
        "fall": {"NY": 0.98, "NJ": 0.99, "DE": 1.00, "CT": 0.99},
    }[season]
    return (
        F.when(F.col("state") == "NY", F.lit(mult["NY"]))
        .when(F.col("state") == "NJ", F.lit(mult["NJ"]))
        .when(F.col("state") == "DE", F.lit(mult["DE"]))
        .when(F.col("state") == "CT", F.lit(mult["CT"]))
        .otherwise(F.lit(mult["NY"]))
    )


def build_meter_usage_month(
    spark: SparkSession,
    source_db: str,
    target_year: int,
    target_month: int,
    random_seed: int = 42,
):
    month_start = f"{target_year}-{target_month:02d}-01"
    month_end_day = calendar.monthrange(target_year, target_month)[1]
    month_end = f"{target_year}-{target_month:02d}-{month_end_day:02d}"
    season = _season_for_month(target_month)

    meter_df = spark.table(f"`{source_db}`.`meter`").select(
        "meter_id", F.col("interval_minutes").cast("int").alias("interval_minutes")
    )
    customer_meter_df = spark.table(f"`{source_db}`.`customer_meter_mapping`").select("customer_id", "meter_id")
    customer_df = spark.table(f"`{source_db}`.`customer`").select("customer_id", "state")
    agreement_df = spark.table(f"`{source_db}`.`customer_agreement_table`").select(
        "customer_id", "contract_start_date", "contract_end_date", "status"
    )

    active_customers = (
        agreement_df.filter(
            (F.col("status") == "active")
            & (F.col("contract_start_date") <= F.to_date(F.lit(month_end)))
            & (
                F.col("contract_end_date").isNull()
                | (F.col("contract_end_date") >= F.to_date(F.lit(month_start)))
            )
        )
        .select("customer_id")
        .distinct()
    )

    eligible = (
        customer_meter_df.join(active_customers, on="customer_id", how="inner")
        .join(meter_df, on="meter_id", how="inner")
        .join(customer_df, on="customer_id", how="left")
        .select("meter_id", "interval_minutes", "state")
    )

    days_df = spark.range(month_end_day).select(
        F.date_add(F.to_date(F.lit(month_start)), F.col("id").cast("int")).alias("day_date")
    )

    expanded = (
        eligible.crossJoin(days_df)
        .withColumn(
            "slots",
            F.when(F.col("interval_minutes") == 15, F.lit(96))
            .when(F.col("interval_minutes") == 30, F.lit(48))
            .otherwise(F.lit(0)),
        )
        .filter(F.col("slots") > 0)
        .withColumn("slot", F.explode(F.sequence(F.lit(0), F.col("slots") - 1)))
    )

    ts_seconds = (
        F.unix_timestamp(F.col("day_date").cast("timestamp"))
        + F.col("slot") * F.col("interval_minutes") * F.lit(60)
    )
    timestamp_col = F.to_timestamp(F.from_unixtime(ts_seconds))

    hour_mult = (
        F.when((F.hour(timestamp_col) >= 6) & (F.hour(timestamp_col) <= 9), F.lit(1.15))
        .when((F.hour(timestamp_col) >= 17) & (F.hour(timestamp_col) <= 21), F.lit(1.25))
        .when((F.hour(timestamp_col) >= 0) & (F.hour(timestamp_col) <= 5), F.lit(0.8))
        .otherwise(F.lit(1.0))
    )
    state_mult = _state_multiplier_expr(season)

    kwh_base = F.rand(random_seed) * F.lit(4.35) + F.lit(0.15)
    kwh = F.round(kwh_base * state_mult * hour_mult, 3)

    usage_df = (
        expanded.withColumn("timestamp", timestamp_col)
        .withColumn("kwh", kwh.cast("double"))
        .withColumn("load_date", F.current_date())
        .withColumn("year", F.year("timestamp").cast("int"))
        .withColumn("month", F.month("timestamp").cast("int"))
        .withColumn("day", F.dayofmonth("timestamp").cast("int"))
        .select(
            "meter_id",
            "timestamp",
            F.col("interval_minutes").cast("int").alias("interval_minutes"),
            "kwh",
            "load_date",
            "year",
            "month",
            "day",
        )
    )
    return usage_df


def write_meter_usage_month(
    spark: SparkSession,
    usage_df,
    output_bucket: str,
    output_prefix: str,
):
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    output_path = f"s3://{output_bucket}/{output_prefix.strip('/')}/meter_usage/"
    (
        usage_df.write.mode("overwrite")
        .partitionBy("year", "month", "day")
        .parquet(output_path)
    )
    return output_path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-bucket", default="ops-autopilot-data")
    parser.add_argument("--output-prefix", default="raw/electric-raw-dev")
    parser.add_argument("--source-db", default="electric-raw-dev")
    parser.add_argument("--target-year", type=int, default=2026)
    parser.add_argument("--target-month", type=int, default=1)
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()
    spark = (
        SparkSession.builder.appName("generate_meter_usage_monthly_notebook")
        .enableHiveSupport()
        .getOrCreate()
    )
    usage_df = build_meter_usage_month(
        spark=spark,
        source_db=args.source_db,
        target_year=args.target_year,
        target_month=args.target_month,
        random_seed=args.random_seed,
    )
    path = write_meter_usage_month(
        spark=spark,
        usage_df=usage_df,
        output_bucket=args.output_bucket,
        output_prefix=args.output_prefix,
    )
    print(f"Wrote meter_usage month to: {path}")


if __name__ == "__main__":
    main()
