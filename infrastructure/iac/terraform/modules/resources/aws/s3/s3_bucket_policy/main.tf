resource "aws_s3_bucket_policy" "s3_bucket_policy" {
  bucket = var.bucket
  policy = var.policy
}