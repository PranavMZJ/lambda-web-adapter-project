output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.no_adapter.arn
}

output "invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.no_adapter.invoke_arn
}
