import os
import boto3


def lambda_handler(event, context):
    glue = boto3.client("glue")

    job_name = os.environ["GLUE_JOB_NAME"]
    input_path = os.environ["INPUT_PATH"]
    output_path = os.environ["OUTPUT_PATH"]
    temp_dir = os.environ["TEMP_DIR"]

    glue.start_job_run(
        JobName=job_name,
        Arguments={
            "--INPUT_PATH": input_path,
            "--OUTPUT_PATH": output_path,
            "--TempDir": temp_dir,
        },
    )

    return {"status": "started", "job_name": job_name}
