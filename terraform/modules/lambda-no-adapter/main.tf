resource "aws_lambda_function" "no_adapter" {
  function_name    = "${var.name_prefix}-no-adapter"
  filename         = var.deployment_zip_path
  source_code_hash = var.source_code_hash
  handler          = "run.sh"
  runtime          = "python3.12"
  role             = var.role_arn

  environment {
    variables = {
      DYNAMODB_TABLE_NAME      = var.dynamodb_table
      AWS_LWA_REMOVE_BASE_PATH = "/test1"
    }
  }

  tags = var.tags
}
