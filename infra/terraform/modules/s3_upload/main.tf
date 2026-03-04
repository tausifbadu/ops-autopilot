resource "aws_s3_object" "upload" {
  bucket = var.bucket_name
  key    = var.s3_key
  source = abspath(var.local_file)

  etag         = filemd5(abspath(var.local_file))
  content_type = "text/csv"
}
