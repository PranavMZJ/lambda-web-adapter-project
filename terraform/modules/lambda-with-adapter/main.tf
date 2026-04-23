resource "aws_lambda_function" "with_adapter" {
  function_name    = "${var.name_prefix}-with-adapter"
  filename         = var.deployment_zip_path
  source_code_hash = var.source_code_hash
  handler          = "run.sh"
  runtime          = "python3.12"
  role             = var.role_arn

  layers = [
    "arn:aws:lambda:ap-northeast-1:753240598075:layer:LambdaAdapterLayerX86:27"
  ]

  environment {
    variables = {
      DYNAMODB_TABLE_NAME      = var.dynamodb_table
      AWS_LAMBDA_EXEC_WRAPPER  = "/opt/bootstrap"
      AWS_LWA_REMOVE_BASE_PATH = "/test2"
      PORT                     = "8000"
    }
  }

  tags = var.tags
}
