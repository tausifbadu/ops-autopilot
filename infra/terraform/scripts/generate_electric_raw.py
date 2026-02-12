import argparse
import os
import random
import string
import sys
import uuid
from datetime import date, datetime, timedelta

import pandas as pd


FIRST_NAMES = [
    "Aaron","Abigail","Adam","Adrian","Aiden","Alan","Albert","Alex","Alexa","Alexander","Alexandra","Alice","Alicia","Allison","Alyssa","Amanda",
    "Amelia","Amy","Andrea","Andrew","Angela","Anthony","Arthur","Ashley","Aubrey","Audrey","Austin","Ava","Barbara","Benjamin","Beverly","Blake",
    "Brandon","Brenda","Brian","Brianna","Brittany","Caleb","Cameron","Caroline","Carolyn","Carter","Catherine","Charles","Charlotte","Chloe","Christian","Christina",
    "Christopher","Claire","Clara","Cole","Connor","Courtney","Daniel","Danielle","David","Dawn","Deborah","Dennis","Derek","Diana","Dominic","Donna",
    "Dylan","Edward","Elaine","Elizabeth","Ella","Emily","Emma","Eric","Ethan","Eugene","Eva","Evelyn","Faith","Frank","Gabriel","Gavin",
    "George","Grace","Gregory","Hannah","Harper","Hazel","Henry","Holly","Hunter","Ian","Isabella","Isaac","Jack","Jacob","James","Jasmine",
    "Jason","Jenna","Jennifer","Jeremy","Jessica","Joan","Joe","John","Jonathan","Jordan","Joseph","Joshua","Joyce","Julia","Julian","Justin",
    "Karen","Katherine","Kathleen","Kayla","Keith","Kelly","Kevin","Kimberly","Kyle","Laura","Lauren","Layla","Leah","Leo","Liam","Lillian",
    "Logan","Lucas","Luke","Madeline","Madison","Maggie","Maria","Marie","Mark","Mason","Matthew","Megan","Melanie","Michael","Mia","Michelle",
    "Mila","Natalie","Nathan","Nicholas","Nicole","Noah","Nora","Olivia","Owen","Pamela","Patricia","Paul","Peter","Rachel","Rebecca","Richard",
    "Robert","Rose","Ryan","Samantha","Samuel","Sara","Sarah","Scott","Sean","Sebastian","Sharon","Sophia","Stella","Stephen","Steven","Susan",
    "Taylor","Teresa","Thomas","Timothy","Tracy","Tyler","Victoria","Vincent","William","Zachary","Zoe",
    "Aaliyah","Addison","Adeline","Adrianna","Ainsley","Alaina","Alana","Alani","Alayna","Alden","Alec","Alejandro","Alfred","Ali","Alison","Alonzo",
    "Amaya","Amber","Amir","Anastasia","Angel","Angelina","Anita","Ann","Annabelle","Antonia","April","Aria","Ariana","Arianna","Ariel","Asher",
    "Aspen","Athena","Avery","Bailey","Beatrice","Becky","Bella","Bernard","Beth","Bianca","Blair","Bradley","Brooke","Bryan","Caden","Calvin",
    "Camila","Camille","Cara","Carla","Carmen","Cassandra","Cecilia","Cedric","Chad","Chelsea","Cheryl","Colin","Constance","Cooper","Corey","Crystal",
    "Curtis","Daisy","Dakota","Damian","Damon","Dana","Devin","Diego","Dominique","Eleanor","Elena","Elijah","Elise","Elliot","Ellis","Elsa",
    "Emerson","Emilia","Emmett","Erin","Ernest","Esther","Evan","Everett","Felix","Fiona","Francis","Frederick","Gabriella","Gene","Gina","Gianna",
    "Giselle","Gordon","Grant","Hailey","Haley","Harley","Harrison","Heidi","Helen","Hugh","Irene","Ivy","Jade","Jamie","Jane","Jared",
    "Javier","Jean","Jocelyn","Jose","Josephine","Juan","Judith","Judy","June","Kaitlyn","Kara","Katelyn","Kathryn","Kelsey","Kenneth","Kerry",
    "Kurt","Landon","Lena","Leonard","Leslie","Lila","Lindsey","Loren","Louise","Lucia","Lucille","Maddox","Malcolm","Marissa","Marjorie","Maya",
    "Meredith","Molly","Monica","Naomi","Natalia","Neil","Nina","Oliver","Oscar","Paige","Parker","Penelope","Peyton","Phoebe","Preston","Quinn",
    "Ralph","Raven","Reese","Renee","Rita","Roger","Ruby","Russell","Sabrina","Sadie","Sage","Selena","Seth","Shelby","Sidney","Silas",
    "Simon","Skylar","Sonia","Spencer","Summer","Sydney","Tanner","Tiffany","Toby","Tristan","Valerie","Vanessa","Vera","Violet","Walter","Wendy",
    "Wesley","Willow","Xavier","Yasmine","Zane",
]

LAST_NAMES = [
    "Adams","Allen","Anderson","Armstrong","Bailey","Baker","Barnes","Bell","Bennett","Brooks","Brown","Bryant","Butler","Campbell","Carter","Chavez",
    "Clark","Coleman","Collins","Cook","Cooper","Cox","Cruz","Davis","Diaz","Edwards","Evans","Flores","Foster","Garcia","Gonzales","Gonzalez",
    "Gray","Green","Griffin","Hall","Harris","Hayes","Henderson","Hernandez","Hill","Howard","Hughes","Jackson","James","Jenkins","Johnson","Jones",
    "Kelly","King","Lee","Lewis","Long","Lopez","Martin","Martinez","Miller","Mitchell","Moore","Morgan","Morris","Murphy","Nelson","Ortiz",
    "Parker","Patterson","Perez","Perry","Peterson","Phillips","Powell","Price","Ramirez","Reed","Richardson","Rivera","Roberts","Robinson","Rodriguez","Rogers",
    "Ross","Russell","Sanchez","Sanders","Scott","Simmons","Smith","Stewart","Sullivan","Taylor","Thomas","Thompson","Torres","Turner","Walker","Ward",
    "Washington","Watson","White","Williams","Wilson","Wood","Wright","Young",
    "Abbott","Acosta","Aguilar","Ali","Alvarado","Andrews","Arnold","Atkins","Austin","Baldwin","Barber","Barker","Barnett","Barton","Bates","Beck",
    "Becker","Benjamin","Bishop","Black","Blackburn","Blair","Boone","Bowen","Boyd","Bradley","Bradshaw","Brewer","Briggs","Brock","Burke","Burns",
    "Bush","Byrd","Caldwell","Cameron","Cannon","Carlson","Carpenter","Carr","Carroll","Carson","Castillo","Chandler","Chapman","Chen","Christian","Clayton",
    "Clements","Cole","Conner","Conway","Cortez","Craig","Crawford","Cunningham","Daniels","Davidson","Dean","Delgado","Dennis","Dixon","Douglas","Drake",
    "Duncan","Dunn","Ellis","Erickson","Estrada","Ferguson","Fisher","Fleming","Fowler","Franklin","Freeman","Fuller","Garner","Gibson","Gilbert","Gomez",
    "Goodman","Grant","Greene","Gross","Guerrero","Guzman","Hale","Hamilton","Hansen","Hanson","Harper","Hawkins","Haynes","Hicks","Hoffman","Holt",
    "Hopkins","Horton","Howell","Hubbard","Hudson","Hunt","Hunter","Ingram","Jensen","Jordan","Kane","Kelley","Kim","Klein","Lamb","Lambert",
    "Larson","Lawrence","Leach","Leonard","Little","Lowe","Lucas","Mack","Malone","Mann","Marsh","Mason","Matthews","Mendez","Miles","Montgomery",
    "Murray","Nash","Navarro","Nguyen","Norris","Obrien","Oliver","Olson","Ortega","Owens","Page","Palmer","Patel","Payne","Peters","Pierce",
    "Porter","Pruitt","Quinn","Ramos","Riley","Robertson","Romero","Rose","Rowe","Salazar","Schmidt","Schneider","Schultz","Sharp","Shaw","Silva",
    "Snyder","Spencer","Stanley","Stephens","Stone","Sutton","Swanson","Tate","Todd","Tucker","Vasquez","Vaughn","Wagner","Walters","Weaver","Webb",
    "Wells","West","Wheeler","Whitaker","Wolfe","Yates","Zimmerman",
]

CITY_ZIPS = [
    {"city": "Newark", "state": "NJ", "postal": "07102"},
    {"city": "Jersey City", "state": "NJ", "postal": "07302"},
    {"city": "Paterson", "state": "NJ", "postal": "07501"},
    {"city": "Elizabeth", "state": "NJ", "postal": "07201"},
    {"city": "Edison", "state": "NJ", "postal": "08817"},
    {"city": "New York", "state": "NY", "postal": "10001"},
    {"city": "Buffalo", "state": "NY", "postal": "14202"},
    {"city": "Rochester", "state": "NY", "postal": "14604"},
    {"city": "Syracuse", "state": "NY", "postal": "13202"},
    {"city": "Albany", "state": "NY", "postal": "12207"},
    {"city": "Cleveland", "state": "OH", "postal": "44114"},
    {"city": "Columbus", "state": "OH", "postal": "43215"},
    {"city": "Cincinnati", "state": "OH", "postal": "45202"},
    {"city": "Toledo", "state": "OH", "postal": "43604"},
    {"city": "Akron", "state": "OH", "postal": "44308"},
    {"city": "Hartford", "state": "CT", "postal": "06103"},
    {"city": "New Haven", "state": "CT", "postal": "06510"},
    {"city": "Stamford", "state": "CT", "postal": "06901"},
    {"city": "Bridgeport", "state": "CT", "postal": "06604"},
    {"city": "Norwalk", "state": "CT", "postal": "06854"},
]

STREET_NAMES = [
    "Maple","Oak","Pine","Cedar","Elm","Main","Washington","Lake","Hill","Sunset","Ridge","Park",
]

PLAN_TYPES = ["fixed", "variable", "time_of_use"]
STATUS_TYPES = ["active", "expired", "cancelled"]
METER_TYPES = ["residential", "commercial"]
QUALITY_FLAGS = ["ok", "estimated"]


def rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


def rand_phone() -> str:
    return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"


def rand_postal(country: str) -> str:
    if country == "US":
        return f"{random.randint(10000,99999)}"
    return f"{random.choice(string.ascii_uppercase)}{random.randint(0,9)}{random.choice(string.ascii_uppercase)} {random.randint(0,9)}{random.choice(string.ascii_uppercase)}{random.randint(0,9)}"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_parquet(df: pd.DataFrame, out_dir: str) -> None:
    ensure_dir(out_dir)
    out_path = os.path.join(out_dir, "part-00000.parquet")
    df.to_parquet(out_path, index=False)


def generate_customers(n: int):
    rows = []
    for _ in range(n):
        city_info = random.choice(CITY_ZIPS)
        customer_id = str(uuid.uuid4())
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        email = f"{first.lower()}{last.lower()}@mail.com"
        street = f"{random.randint(100,9999)} {random.choice(STREET_NAMES)} St"
        rows.append({
            "customer_id": customer_id,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": rand_phone(),
            "address": street,
            "city": city_info["city"],
            "state": city_info["state"],
            "postal_code": city_info["postal"],
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
            "timezone": random.choice(["America/Los_Angeles", "America/Denver", "America/Chicago", "America/New_York"]),
            "updated_at": datetime(2026, 1, 1) + timedelta(days=random.randint(0, 30)),
        })
    return pd.DataFrame(rows)


def generate_transformers(n: int):
    rows = []
    for _ in range(n):
        rows.append({
            "transformer_id": str(uuid.uuid4()),
            "substation_id": f"sub-{rand_str(6)}",
            "capacity_kva": round(random.uniform(100, 1000), 1),
            "status": random.choice(["active", "maintenance"]),
            "install_date": date(2015, 1, 1) + timedelta(days=random.randint(0, 3500)),
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


def generate_meter_usage(eligible_meter_ids, max_rows: int):
    rows = []
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 31, 23, 59, 59)
    meters_list = list(eligible_meter_ids)
    if not meters_list:
        raise ValueError("No eligible meters for usage generation.")

    while len(rows) < max_rows:
        meter_id = random.choice(meters_list)
        interval = random.choice([15, 30])
        ts = start + timedelta(minutes=random.randint(0, int((end - start).total_seconds() / 60)))
        rows.append({
            "meter_id": meter_id,
            "timestamp": ts,
            "interval_minutes": interval,
            "kwh": round(random.uniform(0.1, 5.0), 3),
            "quality_flag": random.choice(QUALITY_FLAGS),
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--max-mb", type=int, default=100)
    parser.add_argument("--tables", default="all", help="Comma-separated table names or 'all'")
    args = parser.parse_args()

    random.seed(42)

    base = args.out
    ensure_dir(base)

    row_cap = args.max_rows

    customers = generate_customers(min(10000, row_cap))
    agreements = generate_customer_agreements(customers, min(10000, row_cap))
    meters = generate_meters(min(10000, row_cap))
    meter_geo = generate_meter_geo(meters)

    transformers = generate_transformers(min(10000, row_cap))
    transformer_geo = generate_transformer_geo(transformers)

    transformer_meter = generate_mapping(
        transformers["transformer_id"].tolist(),
        meters["meter_id"].tolist(),
        date(2025, 1, 1),
    ).rename(columns={"left_id": "transformer_id", "right_id": "meter_id"})

    customer_meter = generate_mapping(
        customers["customer_id"].tolist(),
        meters["meter_id"].tolist(),
        date(2025, 6, 1),
    ).rename(columns={"left_id": "customer_id", "right_id": "meter_id"})

    selected = {t.strip() for t in args.tables.split(",")} if args.tables != "all" else "all"

    def want(table_name: str) -> bool:
        return selected == "all" or table_name in selected

    # Non-partitioned tables
    if want("customer_agreement_table"):
        write_parquet(agreements, os.path.join(base, "customer_agreement_table"))
    if want("customer"):
        write_parquet(customers, os.path.join(base, "customer"))
    if want("meter"):
        write_parquet(meters, os.path.join(base, "meter"))
    if want("meter_geo_location"):
        write_parquet(meter_geo, os.path.join(base, "meter_geo_location"))
    if want("transformer_table"):
        write_parquet(transformers, os.path.join(base, "transformer_table"))
    if want("transformer_meter_mapping"):
        write_parquet(transformer_meter, os.path.join(base, "transformer_meter_mapping"))
    if want("transformer_geo_location"):
        write_parquet(transformer_geo, os.path.join(base, "transformer_geo_location"))
    if want("customer_meter_mapping"):
        write_parquet(customer_meter, os.path.join(base, "customer_meter_mapping"))

    # Partitioned meter_usage
    if want("meter_usage"):
        # Customers with active contracts on 2026-01-01
        contract_date = date(2026, 1, 1)
        active_contracts = agreements[
            (agreements["status"] == "active") &
            (agreements["contract_start_date"] <= contract_date) &
            (
                agreements["contract_end_date"].isna() |
                (agreements["contract_end_date"] >= contract_date)
            )
        ]
        active_customer_ids = set(active_contracts["customer_id"].tolist())

        # Meters mapped to active customers
        eligible_meters = customer_meter[customer_meter["customer_id"].isin(active_customer_ids)]
        eligible_meter_ids = set(eligible_meters["meter_id"].tolist())

        usage = generate_meter_usage(eligible_meter_ids, row_cap)
        usage["year"] = usage["timestamp"].dt.year
        usage["month"] = usage["timestamp"].dt.month
        usage["day"] = usage["timestamp"].dt.day

        for (y, m, d), df_part in usage.groupby(["year", "month", "day"]):
            part_dir = os.path.join(
                base,
                "meter_usage",
                f"year={y}",
                f"month={m:02d}",
                f"day={d:02d}",
            )
            write_parquet(df_part.drop(columns=["year", "month", "day"]), part_dir)

    # Size cap: warn if any file exceeds max-mb
    max_bytes = args.max_mb * 1024 * 1024
    oversized = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".parquet"):
                fp = os.path.join(root, f)
                if os.path.getsize(fp) > max_bytes:
                    oversized.append(fp)

    if oversized:
        print("WARNING: Some files exceed size limit:")
        for fp in oversized:
            print(fp)
        sys.exit(2)

    print("Generation completed.")


if __name__ == "__main__":
    main()
