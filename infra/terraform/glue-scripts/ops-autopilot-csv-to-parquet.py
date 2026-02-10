import sys
import re
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

# Args: --JOB_NAME --INPUT_PATH --OUTPUT_PATH
args = getResolvedOptions(sys.argv, ["JOB_NAME", "INPUT_PATH", "OUTPUT_PATH"])

input_path = args["INPUT_PATH"].rstrip("/") + "/"
output_path = args["OUTPUT_PATH"].rstrip("/") + "/"

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

s3 = boto3.client("s3")


def parse_s3_uri(uri: str):
    match = re.match(r"s3://([^/]+)/(.+)", uri)
    if not match:
        raise ValueError(f"Invalid s3 uri: {uri}")
    return match.group(1), match.group(2)


in_bucket, in_prefix = parse_s3_uri(input_path)
out_bucket, out_prefix = parse_s3_uri(output_path)


def list_csv_keys(bucket, prefix):
    keys = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith(".csv"):
                keys.append(key)
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return keys


def output_exists_for(stem: str) -> bool:
    # Output written as a folder: s3://bucket/prefix/<stem>/
    prefix = f"{out_prefix}{stem}/"
    resp = s3.list_objects_v2(Bucket=out_bucket, Prefix=prefix, MaxKeys=1)
    return resp.get("KeyCount", 0) > 0


csv_keys = list_csv_keys(in_bucket, in_prefix)
if not csv_keys:
    raise ValueError(f"No CSV files found at: {input_path}")

print(f"Found {len(csv_keys)} CSV files.")

for key in csv_keys:
    filename = key.split("/")[-1]
    stem = filename.rsplit(".", 1)[0]

    if output_exists_for(stem):
        print(f"Skipping {filename} (already processed).")
        continue

    file_input_path = f"s3://{in_bucket}/{key}"
    file_output_path = f"s3://{out_bucket}/{out_prefix}{stem}/"

    print(f"Reading CSV from: {file_input_path}")
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .csv(file_input_path)
    )

    if len(df.columns) == 0:
        raise ValueError(f"No columns found. Check input path or schema: {file_input_path}")

    if df.rdd.isEmpty():
        raise ValueError(f"No data rows found at: {file_input_path}")

    print(f"Writing Parquet to: {file_output_path}")
    df.write.mode("overwrite").parquet(file_output_path)

job.commit()
print("Job completed successfully")
