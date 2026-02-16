import argparse
import os
import random
import uuid
from datetime import date, datetime, timedelta

import pandas as pd
import s3fs


METER_TYPES = ["smart", "analog", "digital"]
PLAN_TYPES = ["standard", "time_of_use", "green", "fixed"]
STATUS_TYPES = ["active", "expired", "terminated"]
QUALITY_FLAGS = ["ok", "estimated", "missing"]
FIRST_NAMES = [
    "James","Mary","John","Patricia","Robert","Jennifer","Michael","Linda","William","Elizabeth",
    "David","Barbara","Richard","Susan","Joseph","Jessica","Thomas","Sarah","Charles","Karen",
    "Christopher","Nancy","Daniel","Lisa","Matthew","Betty","Anthony","Margaret","Mark","Sandra",
    "Donald","Ashley","Steven","Kimberly","Paul","Emily","Andrew","Donna","Joshua","Michelle",
    "Kenneth","Carol","Kevin","Amanda","Brian","Dorothy","George","Melissa","Edward","Deborah"
]
LAST_NAMES = [
    "Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
    "Hernandez","Lopez","Gonzalez","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
    "Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
    "Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
    "Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts"
]


def rand_phone():
    return f"+1{random.randint(2000000000, 9999999999)}"


def generate_customers(n: int):
    rows = []
    for _ in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first}{last}@mail.com".lower()
        rows.append({
            "customer_id": str(uuid.uuid4()),
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": rand_phone(),
            "address": f"{random.randint(100, 9999)} Main St",
            "city": "Chicago",
            "state": "IL",
            "postal_code": f"{random.randint(60000, 62999)}",
            "country": "US",
            "signup_date": date(2020, 1, 1) + timedelta(days=random.randint(0, 2000)),
        })
    return pd.DataFrame(rows)


def generate_customer_agreements(customers: pd.DataFrame, n: int):
    rows = []
    for _ in range(n):
        customer_id = customers.sample(1).iloc[0]["customer_id"]
        start = date(2022, 1, 1) + timedelta(days=random.randint(0, 700))
        end = start + timedelta(days=random.randint(180, 730))
        status = random.choice(STATUS_TYPES)
        rows.append({
            "agreement_id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "contract_start_date": start,
            "contract_end_date": None if status == "active" else end,
            "plan_type": random.choice(PLAN_TYPES),
            "status": status,
            "monthly_fee_usd": round(random.uniform(30, 250), 2),
        })
    return pd.DataFrame(rows)


def generate_meters(n: int):
    rows = []
    for _ in range(n):
        rows.append({
            "meter_id": str(uuid.uuid4()),
            "meter_type": random.choice(METER_TYPES),
            "interval_minutes": random.choice([15, 30]),
            "install_date": date(2019, 1, 1) + timedelta(days=random.randint(0, 2000)),
            "status": random.choice(["active", "inactive"]),
            "manufacturer": random.choice(["GE", "Siemens", "ABB", "Schneider"]),
        })
    return pd.DataFrame(rows)


def generate_meter_geo(meters: pd.DataFrame):
    rows = []
    for _, row in meters.iterrows():
        rows.append({
            "meter_id": row["meter_id"],
            "latitude": round(random.uniform(25.0, 49.5), 6),
            "longitude": round(random.uniform(-124.7, -66.9), 6),
            "timezone": "America/Chicago",
            "updated_at": datetime(2026, 1, 1) + timedelta(days=random.randint(0, 30)),
        })
    return pd.DataFrame(rows)


def generate_transformers(n: int):
    rows = []
    for _ in range(n):
        rows.append({
            "transformer_id": str(uuid.uuid4()),
            "transformer_type": random.choice(["pad_mount", "pole_mount", "substation"]),
            "capacity_kva": random.choice([25, 50, 100, 250, 500]),
            "install_date": date(2018, 1, 1) + timedelta(days=random.randint(0, 2000)),
            "status": random.choice(["active", "inactive"]),
        })
    return pd.DataFrame(rows)


def generate_transformer_geo(transformers: pd.DataFrame):
    rows = []
    for _, row in transformers.iterrows():
        rows.append({
            "transformer_id": row["transformer_id"],
            "latitude": round(random.uniform(25.0, 49.5), 6),
            "longitude": round(random.uniform(-124.7, -66.9), 6),
            "updated_at": datetime(2026, 1, 1) + timedelta(days=random.randint(0, 30)),
        })
    return pd.DataFrame(rows)


def generate_mapping(left_ids, right_ids, start_date):
    rows = []
    for lid in left_ids:
        rid = random.choice(right_ids)
        rows.append({
            "left_id": lid,
            "right_id": rid,
            "effective_start": start_date + timedelta(days=random.randint(0, 30)),
            "effective_end": None,
        })
    return pd.DataFrame(rows)


def generate_customer_meter_mapping(customers: pd.DataFrame, meters: pd.DataFrame, start_date: date):
    rows = []
    meter_ids = meters["meter_id"].tolist()
    random.shuffle(meter_ids)
    if len(meter_ids) < len(customers):
        raise ValueError("Not enough meters to assign one per customer.")
    for i, row in customers.iterrows():
        rows.append({
            "customer_id": row["customer_id"],
            "meter_id": meter_ids[i],
            "effective_start": start_date + timedelta(days=random.randint(0, 30)),
            "effective_end": None,
        })
    return pd.DataFrame(rows)


def generate_transformer_meter_mapping(customers: pd.DataFrame, customer_meter: pd.DataFrame, transformers: pd.DataFrame, start_date: date):
    # One transformer per ZIP: all meters in same ZIP map to the same transformer.
    zip_codes = customers["postal_code"].unique().tolist()
    transformer_ids = transformers["transformer_id"].tolist()
    if len(transformer_ids) < len(zip_codes):
        raise ValueError("Not enough transformers to assign one per ZIP code.")

    random.shuffle(transformer_ids)
    zip_to_transformer = {z: transformer_ids[i] for i, z in enumerate(zip_codes)}

    cm = customer_meter.merge(customers[["customer_id", "postal_code"]], on="customer_id", how="left")
    meter_zip = cm.drop_duplicates(subset=["meter_id"])[["meter_id", "postal_code"]]

    rows = []
    for _, row in meter_zip.iterrows():
        rows.append({
            "transformer_id": zip_to_transformer[row["postal_code"]],
            "meter_id": row["meter_id"],
            "effective_start": start_date + timedelta(days=random.randint(0, 30)),
            "effective_end": None,
        })
    return pd.DataFrame(rows)


def generate_meter_usage(meters: pd.DataFrame, eligible_meter_ids):
    rows = []
    meters_list = list(eligible_meter_ids)
    if not meters_list:
        raise ValueError("No eligible meters for usage generation.")

    meter_intervals = {
        row["meter_id"]: int(row["interval_minutes"])
        for _, row in meters.iterrows()
        if row["meter_id"] in meters_list
    }

    days = [date(2026, 1, d) for d in range(1, 32)]
    load_date = datetime.utcnow().date()

    for meter_id in meters_list:
        interval = meter_intervals.get(meter_id)
        if interval not in (15, 30):
            continue

        per_day = 96 if interval == 15 else 48
        for day in days:
            start_dt = datetime(day.year, day.month, day.day, 0, 0, 0)
            for i in range(per_day):
                ts = start_dt + timedelta(minutes=interval * i)
                rows.append({
                    "meter_id": meter_id,
                    "timestamp": ts,
                    "interval_minutes": interval,
                    "kwh": round(random.uniform(0.1, 5.0), 3),
                    "load_date": load_date,
                    "year": day.year,
                    "month": day.month,
                    "day": day.day,
                })

    return pd.DataFrame(rows)


def write_parquet(df: pd.DataFrame, s3_path: str, partition_cols=None):
    fs = s3fs.S3FileSystem(anon=False)
    if partition_cols:
        target_dir = s3_path.rstrip("/") + "/"
        if fs.exists(target_dir):
            fs.rm(target_dir, recursive=True)
        df.to_parquet(target_dir, index=False, engine="pyarrow", partition_cols=partition_cols, filesystem=fs)
        return

    # Non-partitioned: write a real parquet file under a folder
    if s3_path.endswith(".parquet"):
        file_path = s3_path
    else:
        file_path = s3_path.rstrip("/") + "/part-00000.parquet"
    parent_dir = file_path.rsplit("/", 1)[0] + "/"
    if fs.exists(parent_dir):
        fs.rm(parent_dir, recursive=True)
    df.to_parquet(file_path, index=False, engine="pyarrow", filesystem=fs)


def main():
    parser = argparse.ArgumentParser()
    # Glue injects JOB_* args; accept/ignore via parse_known_args.
    parser.add_argument("--output-bucket", required=True)
    parser.add_argument("--output-prefix", default="raw/electric-raw-dev")
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--tables", default="all", help="Comma-separated table names or 'all'")
    args, _ = parser.parse_known_args()

    random.seed(42)

    base_prefix = args.output_prefix.strip("/")
    base = f"s3://{args.output_bucket}/{base_prefix}"

    row_cap = args.max_rows

    customers = generate_customers(min(10000, row_cap))
    agreements = generate_customer_agreements(customers, min(10000, row_cap))
    meters = generate_meters(min(10000, row_cap))
    meter_geo = generate_meter_geo(meters)

    zip_count = customers["postal_code"].nunique()
    transformers = generate_transformers(max(min(10000, row_cap), zip_count))
    transformer_geo = generate_transformer_geo(transformers)

    customer_meter = generate_customer_meter_mapping(
        customers,
        meters,
        date(2025, 6, 1),
    )

    transformer_meter = generate_transformer_meter_mapping(
        customers,
        customer_meter,
        transformers,
        date(2025, 1, 1),
    )

    selected = {t.strip() for t in args.tables.split(",")} if args.tables != "all" else "all"

    def want(table_name: str) -> bool:
        return selected == "all" or table_name in selected

    if want("customer"):
        write_parquet(customers, f"{base}/customer")
    if want("customer_agreement_table"):
        write_parquet(agreements, f"{base}/customer_agreement_table")
    if want("meter"):
        write_parquet(meters, f"{base}/meter")
    if want("meter_geo_location"):
        write_parquet(meter_geo, f"{base}/meter_geo_location")
    if want("transformer_table"):
        write_parquet(transformers, f"{base}/transformer_table")
    if want("transformer_geo_location"):
        write_parquet(transformer_geo, f"{base}/transformer_geo_location")
    if want("transformer_meter_mapping"):
        write_parquet(transformer_meter, f"{base}/transformer_meter_mapping")
    if want("customer_meter_mapping"):
        write_parquet(customer_meter, f"{base}/customer_meter_mapping")

    # Meter usage (partitioned)
    if want("meter_usage"):
        contract_date = date(2026, 1, 1)
        active_contracts = agreements[
            (agreements["status"] == "active") &
            (agreements["contract_start_date"] <= contract_date) &
            (
                agreements["contract_end_date"].isna() |
                (agreements["contract_end_date"] >= contract_date)
            )
        ]
        eligible_customers = set(active_contracts["customer_id"].tolist())
        eligible_meter_ids = customer_meter[
            customer_meter["customer_id"].isin(eligible_customers)
        ]["meter_id"].tolist()

        usage = generate_meter_usage(meters, eligible_meter_ids)
        write_parquet(usage, f"{base}/meter_usage", partition_cols=["year", "month", "day"])


if __name__ == "__main__":
    main()
