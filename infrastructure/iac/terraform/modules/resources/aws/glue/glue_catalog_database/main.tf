resource "aws_glue_catalog_database" "glue_catalog_database" {
  name = "${var.environment}-${var.name}"
}
