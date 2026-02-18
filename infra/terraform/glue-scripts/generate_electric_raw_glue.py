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

STATE_CITY_ZIP = {
    "NY": [
        ("New York", "10001"),
        ("Buffalo", "14201"),
        ("Rochester", "14604"),
        ("Albany", "12207"),
        ("Syracuse", "13202"),
        ("Yonkers", "10701"),
        ("White Plains", "10601"),
        ("Ithaca", "14850"),
    ],
    "NJ": [
        ("Newark", "07102"),
        ("Jersey City", "07302"),
        ("Paterson", "07501"),
        ("Elizabeth", "07201"),
        ("Edison", "08817"),
        ("Trenton", "08608"),
        ("Princeton", "08540"),
        ("Hoboken", "07030"),
    ],
    "DE": [
        ("Wilmington", "19801"),
        ("Dover", "19901"),
        ("Newark", "19711"),
        ("Middletown", "19709"),
        ("Smyrna", "19977"),
        ("Milford", "19963"),
    ],
    "CT": [
        ("Bridgeport", "06604"),
        ("New Haven", "06510"),
        ("Hartford", "06103"),
        ("Stamford", "06901"),
        ("Norwalk", "06850"),
        ("Waterbury", "06702"),
        ("Danbury", "06810"),
        ("New Britain", "06051"),
    ],
}

STREET_NAMES = [
    "Main", "Maple", "Oak", "Pine", "Cedar", "Walnut", "Chestnut", "Park",
    "Washington", "Lincoln", "Jefferson", "Franklin", "Madison", "Broad",
    "Highland", "River", "Lake", "Hill", "Prospect", "Church",
]

STREET_TYPES = ["St", "Ave", "Blvd", "Rd", "Ln", "Dr", "Ct", "Pl", "Way", "Terrace"]

CITY_COORDS = {
    ("NY", "New York"): (40.7128, -74.0060),
    ("NY", "Buffalo"): (42.8864, -78.8784),
    ("NY", "Rochester"): (43.1566, -77.6088),
    ("NY", "Albany"): (42.6526, -73.7562),
    ("NY", "Syracuse"): (43.0481, -76.1474),
    ("NY", "Yonkers"): (40.9312, -73.8988),
    ("NY", "White Plains"): (41.0330, -73.7629),
    ("NY", "Ithaca"): (42.4430, -76.5019),
    ("NJ", "Newark"): (40.7357, -74.1724),
    ("NJ", "Jersey City"): (40.7178, -74.0431),
    ("NJ", "Paterson"): (40.9168, -74.1718),
    ("NJ", "Elizabeth"): (40.6639, -74.2107),
    ("NJ", "Edison"): (40.5187, -74.4121),
    ("NJ", "Trenton"): (40.2171, -74.7429),
    ("NJ", "Princeton"): (40.3573, -74.6672),
    ("NJ", "Hoboken"): (40.7439, -74.0324),
    ("DE", "Wilmington"): (39.7447, -75.5484),
    ("DE", "Dover"): (39.1582, -75.5244),
    ("DE", "Newark"): (39.6837, -75.7497),
    ("DE", "Middletown"): (39.4496, -75.7163),
    ("DE", "Smyrna"): (39.2998, -75.6046),
    ("DE", "Milford"): (38.9126, -75.4277),
    ("CT", "Bridgeport"): (41.1865, -73.1952),
    ("CT", "New Haven"): (41.3083, -72.9279),
    ("CT", "Hartford"): (41.7658, -72.6734),
    ("CT", "Stamford"): (41.0534, -73.5387),
    ("CT", "Norwalk"): (41.1177, -73.4082),
    ("CT", "Waterbury"): (41.5582, -73.0515),
    ("CT", "Danbury"): (41.3948, -73.4540),
    ("CT", "New Britain"): (41.6612, -72.7795),
}

MONTH_TO_SEASON = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "fall", 10: "fall", 11: "fall",
}

SEASON_MULTIPLIER_BY_STATE = {
    "NY": {"winter": 1.28, "spring": 0.95, "summer": 1.12, "fall": 0.98},
    "NJ": {"winter": 1.22, "spring": 0.96, "summer": 1.16, "fall": 0.99},
    "DE": {"winter": 1.18, "spring": 0.97, "summer": 1.14, "fall": 1.00},
    "CT": {"winter": 1.25, "spring": 0.95, "summer": 1.10, "fall": 0.99},
}


def rand_phone():
    return f"+1{random.randint(2000000000, 9999999999)}"


def rand_customer_location():
    state = random.choice(list(STATE_CITY_ZIP.keys()))
    city, postal_code = random.choice(STATE_CITY_ZIP[state])
    address = f"{random.randint(100, 9999)} {random.choice(STREET_NAMES)} {random.choice(STREET_TYPES)}"
    return address, city, state, postal_code


def jitter_coord(lat: float, lon: float, delta: float = 0.03):
    return (
        float(round(lat + random.uniform(-delta, delta), 6)),
        float(round(lon + random.uniform(-delta, delta), 6)),
    )


def hour_multiplier(hour: int) -> float:
    if 6 <= hour <= 9:
        return 1.15
    if 17 <= hour <= 21:
        return 1.25
    if 0 <= hour <= 5:
        return 0.8
    return 1.0


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
        address, city, state_code, postal_code = rand_customer_location()
        customer_rows.append((
            str(uuid.uuid4()),
            first,
            last,
            f"{first}.{last}{random.randint(1,99)}@mail.com".lower(),
            rand_phone(),
            address,
            city,
            state_code,
            postal_code,
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

    # transformers
    transformer_count = max(1, len(meter_ids) // 15)
    transformer_rows = []
    transformer_home_city = []
    for _ in range(transformer_count):
        state = random.choice(list(STATE_CITY_ZIP.keys()))
        city, _ = random.choice(STATE_CITY_ZIP[state])
        transformer_rows.append((
            str(uuid.uuid4()),
            f"sub-{uuid.uuid4().hex[:6]}",
            float(random.choice([25, 50, 100, 250, 500])),
            random.choice(["active", "inactive"]),
            date(2018, 1, 1) + timedelta(days=random.randint(0, 2000)),
        ))
        transformer_home_city.append((state, city))
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
    for idx, transformer_id in enumerate(transformer_ids):
        state, city = transformer_home_city[idx]
        base_lat, base_lon = CITY_COORDS[(state, city)]
        lat, lon = jitter_coord(base_lat, base_lon, delta=0.02)
        transformer_geo_rows.append((
            transformer_id,
            lat,
            lon,
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
    meter_to_customer = {r[1]: r[0] for r in customer_meter_rows}
    customer_loc = {r[0]: (r[7], r[6]) for r in customer_rows}  # customer_id -> (state, city)
    meter_state = {
        meter_id: customer_loc[meter_to_customer[meter_id]][0]
        for meter_id in meter_ids
        if meter_id in meter_to_customer and meter_to_customer[meter_id] in customer_loc
    }

    # meter geo aligned to mapped customer city/state
    meter_geo_rows = []
    for meter_id in meter_ids:
        customer_id = meter_to_customer.get(meter_id)
        if customer_id in customer_loc:
            state, city = customer_loc[customer_id]
            base_lat, base_lon = CITY_COORDS[(state, city)]
        else:
            state = random.choice(list(STATE_CITY_ZIP.keys()))
            city, _ = random.choice(STATE_CITY_ZIP[state])
            base_lat, base_lon = CITY_COORDS[(state, city)]
        lat, lon = jitter_coord(base_lat, base_lon, delta=0.01)
        meter_geo_rows.append((
            meter_id,
            lat,
            lon,
            "America/New_York",
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

    # transformer-meter mapping
    transformer_meter_rows = []
    shuffled_meter_ids = meter_ids[:]
    random.shuffle(shuffled_meter_ids)
    for idx, meter_id in enumerate(shuffled_meter_ids):
        transformer_meter_rows.append((
            transformer_ids[idx % len(transformer_ids)],
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
        target_year = 2026
        contract_date = date(target_year, 1, 1)
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
            current_day = date(target_year, 1, 1)
            end_day = date(target_year, 12, 31)
            state = meter_state.get(meter_id, "NY")
            while current_day <= end_day:
                season = MONTH_TO_SEASON[current_day.month]
                seasonal_mult = SEASON_MULTIPLIER_BY_STATE.get(state, SEASON_MULTIPLIER_BY_STATE["NY"])[season]
                start_dt = datetime(current_day.year, current_day.month, current_day.day, 0, 0, 0)
                for i in range(per_day):
                    ts = start_dt + timedelta(minutes=interval * i)
                    kwh_base = random.uniform(0.15, 4.5)
                    kwh = float(round(kwh_base * seasonal_mult * hour_multiplier(ts.hour), 3))
                    usage_rows.append((
                        meter_id,
                        ts,
                        interval,
                        kwh,
                        datetime.utcnow().date(),
                        current_day.year,
                        current_day.month,
                        current_day.day,
                    ))
                current_day = current_day + timedelta(days=1)

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
