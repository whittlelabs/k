resource "aws_ses_email_identity" "ses_email_identity" {
  email = var.email
}