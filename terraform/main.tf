terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile
}

locals {
  common_tags = {
    User    = var.user_tag
    Project = var.project_tag
  }
  name_prefix      = var.name_prefix
  deployment_zip   = "${path.module}/../deployment.zip"
  source_code_hash = filebase64sha256("${path.module}/../deployment.zip")
}

module "dynamodb" {
  source      = "./modules/dynamodb"
  name_prefix = local.name_prefix
  tags        = local.common_tags
}

module "iam" {
  source               = "./modules/iam"
  name_prefix          = local.name_prefix
  permissions_boundary = var.permissions_boundary_arn
  dynamodb_table_arn   = module.dynamodb.table_arn
  tags                 = local.common_tags
}

module "lambda_no_adapter" {
  source              = "./modules/lambda-no-adapter"
  name_prefix         = local.name_prefix
  role_arn            = module.iam.lambda_role_arn
  dynamodb_table      = module.dynamodb.table_name
  deployment_zip_path = local.deployment_zip
  source_code_hash    = local.source_code_hash
  tags                = local.common_tags
}

module "lambda_with_adapter" {
  source              = "./modules/lambda-with-adapter"
  name_prefix         = local.name_prefix
  role_arn            = module.iam.lambda_role_arn
  dynamodb_table      = module.dynamodb.table_name
  deployment_zip_path = local.deployment_zip
  source_code_hash    = local.source_code_hash
  tags                = local.common_tags
}

module "api_gateway" {
  source                         = "./modules/api-gateway"
  name_prefix                    = local.name_prefix
  lambda_no_adapter_arn          = module.lambda_no_adapter.function_arn
  lambda_no_adapter_invoke_arn   = module.lambda_no_adapter.invoke_arn
  lambda_with_adapter_arn        = module.lambda_with_adapter.function_arn
  lambda_with_adapter_invoke_arn = module.lambda_with_adapter.invoke_arn
  tags                           = local.common_tags
}
