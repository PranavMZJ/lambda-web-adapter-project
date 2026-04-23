variable "region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "terraform"
}

variable "name_prefix" {
  description = "Prefix for all resource names (e.g. Pranav-lambda-web-adapter-migration-test)"
  type        = string
}

variable "permissions_boundary_arn" {
  description = "ARN of the IAM permissions boundary to attach to all IAM roles"
  type        = string
}

variable "user_tag" {
  description = "Value for the User tag applied to all resources"
  type        = string
}

variable "project_tag" {
  description = "Value for the Project tag applied to all resources"
  type        = string
}
