output "function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.with_adapter.arn
}

output "invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.with_adapter.invoke_arn
}
