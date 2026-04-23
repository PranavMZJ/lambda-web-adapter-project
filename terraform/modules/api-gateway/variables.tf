variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
}

variable "lambda_no_adapter_arn" {
  description = "ARN of the no-adapter Lambda function"
  type        = string
}

variable "lambda_no_adapter_invoke_arn" {
  description = "Invoke ARN of the no-adapter Lambda function"
  type        = string
}

variable "lambda_with_adapter_arn" {
  description = "ARN of the with-adapter Lambda function"
  type        = string
}

variable "lambda_with_adapter_invoke_arn" {
  description = "Invoke ARN of the with-adapter Lambda function"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
}
