output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_endpoint
}

output "lambda_no_adapter_arn" {
  description = "ARN of the no-adapter Lambda function"
  value       = module.lambda_no_adapter.function_arn
}

output "lambda_with_adapter_arn" {
  description = "ARN of the with-adapter Lambda function"
  value       = module.lambda_with_adapter.function_arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table"
  value       = module.dynamodb.table_name
}
