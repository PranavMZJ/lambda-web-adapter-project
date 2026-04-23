variable "name_prefix" {
  description = "Prefix for all resource names"
  type        = string
}

variable "permissions_boundary" {
  description = "ARN of the IAM permissions boundary to attach to the role"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for the inline policy"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
}
