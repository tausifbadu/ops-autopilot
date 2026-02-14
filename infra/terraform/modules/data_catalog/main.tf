resource "aws_athena_workgroup" "ops_autopilot" {
  name = "ops-autopilot"

  configuration {
    enforce_workgroup_configuration = true

    result_configuration {
      output_location = "s3://${var.data_bucket_name}/athena-results/"
    }
  }
}

resource "aws_glue_catalog_database" "electric_raw_dev" {
  name = var.database_name
}

resource "aws_glue_catalog_database" "electric_curated_dev" {
  name = var.curated_database_name
}

resource "aws_glue_catalog_table" "customer" {
  name          = "customer"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/customer/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "first_name"
      type = "string"
    }
    columns {
      name = "last_name"
      type = "string"
    }
    columns {
      name = "email"
      type = "string"
    }
    columns {
      name = "phone"
      type = "string"
    }
    columns {
      name = "address"
      type = "string"
    }
    columns {
      name = "city"
      type = "string"
    }
    columns {
      name = "state"
      type = "string"
    }
    columns {
      name = "postal_code"
      type = "string"
    }
    columns {
      name = "country"
      type = "string"
    }
    columns {
      name = "signup_date"
      type = "date"
    }
  }
}

resource "aws_glue_catalog_table" "customer_agreement_table" {
  name          = "customer_agreement_table"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/customer_agreement_table/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "agreement_id"
      type = "string"
    }
    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "contract_start_date"
      type = "date"
    }
    columns {
      name = "contract_end_date"
      type = "date"
    }
    columns {
      name = "plan_type"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "monthly_fee_usd"
      type = "double"
    }
  }
}

resource "aws_glue_catalog_table" "meter" {
  name          = "meter"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/meter/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "interval_minutes"
      type = "int"
    }
    columns {
      name = "meter_type"
      type = "string"
    }
    columns {
      name = "install_date"
      type = "date"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "manufacturer"
      type = "string"
    }
  }
}

resource "aws_glue_catalog_table" "meter_geo_location" {
  name          = "meter_geo_location"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/meter_geo_location/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "timezone"
      type = "string"
    }
    columns {
      name = "updated_at"
      type = "timestamp"
    }
  }
}

resource "aws_glue_catalog_table" "transformer_table" {
  name          = "transformer_table"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/transformer_table/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "transformer_id"
      type = "string"
    }
    columns {
      name = "substation_id"
      type = "string"
    }
    columns {
      name = "capacity_kva"
      type = "double"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "install_date"
      type = "date"
    }
  }
}

resource "aws_glue_catalog_table" "transformer_meter_mapping" {
  name          = "transformer_meter_mapping"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/transformer_meter_mapping/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "transformer_id"
      type = "string"
    }
    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "effective_start"
      type = "date"
    }
    columns {
      name = "effective_end"
      type = "date"
    }
  }
}

resource "aws_glue_catalog_table" "transformer_geo_location" {
  name          = "transformer_geo_location"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/transformer_geo_location/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "transformer_id"
      type = "string"
    }
    columns {
      name = "latitude"
      type = "double"
    }
    columns {
      name = "longitude"
      type = "double"
    }
    columns {
      name = "updated_at"
      type = "timestamp"
    }
  }
}

resource "aws_glue_catalog_table" "customer_meter_mapping" {
  name          = "customer_meter_mapping"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/customer_meter_mapping/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "effective_start"
      type = "date"
    }
    columns {
      name = "effective_end"
      type = "date"
    }
  }
}

resource "aws_glue_catalog_table" "meter_usage" {
  name          = "meter_usage"
  database_name = aws_glue_catalog_database.electric_raw_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/raw/electric-raw-dev/meter_usage/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "timestamp"
      type = "timestamp"
    }
    columns {
      name = "interval_minutes"
      type = "int"
    }
    columns {
      name = "kwh"
      type = "double"
    }
    columns {
      name = "load_date"
      type = "date"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }
  partition_keys {
    name = "month"
    type = "int"
  }
  partition_keys {
    name = "day"
    type = "int"
  }
}

resource "aws_glue_catalog_table" "customer_usage_curated" {
  name          = "customer_usage_curated"
  database_name = aws_glue_catalog_database.electric_curated_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/curated/customer_usage_curated/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "first_name"
      type = "string"
    }
    columns {
      name = "last_name"
      type = "string"
    }
    columns {
      name = "email"
      type = "string"
    }
    columns {
      name = "city"
      type = "string"
    }
    columns {
      name = "state"
      type = "string"
    }
    columns {
      name = "postal_code"
      type = "string"
    }
    columns {
      name = "meter_id"
      type = "string"
    }
    columns {
      name = "usage_ts"
      type = "timestamp"
    }
    columns {
      name = "usage_date"
      type = "date"
    }
    columns {
      name = "interval_minutes"
      type = "int"
    }
    columns {
      name = "kwh"
      type = "double"
    }
    columns {
      name = "agreement_id"
      type = "string"
    }
    columns {
      name = "plan_type"
      type = "string"
    }
    columns {
      name = "contract_status"
      type = "string"
    }
    columns {
      name = "contract_start_date"
      type = "date"
    }
    columns {
      name = "contract_end_date"
      type = "date"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }
  partition_keys {
    name = "month"
    type = "int"
  }
  partition_keys {
    name = "day"
    type = "int"
  }
}

resource "aws_glue_catalog_table" "customer_daily_usage" {
  name          = "customer_daily_usage"
  database_name = aws_glue_catalog_database.electric_curated_dev.name
  table_type    = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${var.data_bucket_name}/curated/customer_daily_usage/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "usage_date"
      type = "date"
    }
    columns {
      name = "total_kwh"
      type = "double"
    }
    columns {
      name = "peak_kwh"
      type = "double"
    }
    columns {
      name = "avg_kwh"
      type = "double"
    }
  }

  partition_keys {
    name = "year"
    type = "int"
  }
  partition_keys {
    name = "month"
    type = "int"
  }
  partition_keys {
    name = "day"
    type = "int"
  }
}
