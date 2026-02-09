resource "aws_s3_object" "upload" {
  bucket = var.bucket_name
  key    = var.s3_key
  source = var.local_file

  etag = filemd5(var.local_file)
  content_type = "text/csv"
}