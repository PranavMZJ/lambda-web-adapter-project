variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
}

variable "role_arn" {
  description = "ARN of the Lambda execution IAM role"
  type        = string
}

variable "dynamodb_table" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "deployment_zip_path" {
  description = "Path to the deployment.zip file"
  type        = string
}

variable "source_code_hash" {
  description = "Base64-encoded SHA256 hash of the deployment zip"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
}
