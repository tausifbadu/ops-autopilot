import sys
import re
import traceback
from pyspark.sql import SparkSession

def get_arg(flag: str):
    if flag not in sys.argv:
        raise ValueError(f"Missing arg {flag}")
    i = sys.argv.index(flag)
    if i + 1 >= len(sys.argv):
        raise ValueError(f"Missing value for {flag}")
    return sys.argv[i + 1]

def parse_s3_uri(uri: str):
    match = re.match(r"s3://([^/]+)/(.+)", uri)
    if not match:
        raise ValueError(f"Invalid s3 uri: {uri}")
    return match.group(1), match.group(2)

def main():
    # expected args:
    # --JOB_NAME name --INPUT_PATH s3://... --OUTPUT_PATH s3://...
    job_name = get_arg("--JOB_NAME")
    input_path = get_arg("--INPUT_PATH").rstrip("/") + "/"
    output_path = get_arg("--OUTPUT_PATH").rstrip("/") + "/"

    print(f"JOB_NAME={job_name}")
    print(f"INPUT_PATH={input_path}")
    print(f"OUTPUT_PATH={output_path}")

    spark = SparkSession.builder.appName(job_name).getOrCreate()

    hadoop_conf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    Path = spark._jvm.org.apache.hadoop.fs.Path

    in_bucket, in_prefix = parse_s3_uri(input_path)
    out_bucket, out_prefix = parse_s3_uri(output_path)

    def list_csv_keys(bucket, prefix):
        keys = []
        start = Path(f"s3://{bucket}/{prefix}")

        def walk(p):
            for status in fs.listStatus(p):
                spath = status.getPath().toString()
                if status.isDirectory():
                    walk(status.getPath())
                else:
                    if spath.lower().endswith(".csv"):
                        key = spath.replace(f"s3://{bucket}/", "")
                        keys.append(key)

        if fs.exists(start):
            walk(start)
        return keys

    def output_exists_for(stem: str) -> bool:
        prefix = f"{out_prefix}{stem}/"
        return fs.exists(Path(f"s3://{out_bucket}/{prefix}"))

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
            raise ValueError(f"No columns found: {file_input_path}")

        if df.rdd.isEmpty():
            raise ValueError(f"No data rows found: {file_input_path}")

        print(f"Writing Parquet to: {file_output_path}")
        df.write.mode("overwrite").parquet(file_output_path)

    print("Job completed successfully")
    spark.stop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
