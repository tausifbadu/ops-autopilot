from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("hello-emr").getOrCreate()

print("Hello from EMR!")

spark.stop()
