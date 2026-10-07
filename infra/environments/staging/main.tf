# ==============================================================================
# SentinelLog Staging Infrastructure Definition (Terraform >= 1.5.0)
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
  }

  backend "s3" {
    bucket         = "sentinellog-terraform-state-staging"
    key            = "staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "sentinellog-tf-locks-staging"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "SentinelLog"
      Environment = "staging"
      ManagedBy   = "Terraform"
    }
  }
}

module "networking" {
  source               = "../../modules/networking"
  environment          = "staging"
  vpc_cidr             = "10.1.0.0/16"
  public_subnet_cidrs  = ["10.1.1.0/24", "10.1.2.0/24"]
  private_subnet_cidrs = ["10.1.10.0/24", "10.1.20.0/24"]
  availability_zones   = ["us-east-1a", "us-east-1b"]
}

module "ecr" {
  source          = "../../modules/ecr"
  environment     = "staging"
  repository_name = "sentinellog"
}

module "alb" {
  source                = "../../modules/alb"
  environment           = "staging"
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
}

module "storage" {
  source        = "../../modules/storage"
  environment   = "staging"
  bucket_prefix = "sentinellog-artifacts"
}

module "secrets" {
  source      = "../../modules/secrets"
  environment = "staging"
}

module "database" {
  source                = "../../modules/database"
  environment           = "staging"
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id
  database_name         = "sentinellog_staging"
  backup_retention_days = 7
}

module "ecs" {
  source                     = "../../modules/ecs"
  environment                = "staging"
  image_uri                  = var.image_uri
  cpu                        = 1024
  memory                     = 2048
  desired_count              = 2
  private_subnet_ids         = module.networking.private_subnet_ids
  ecs_security_group_id      = module.networking.ecs_security_group_id
  target_group_arn           = module.alb.target_group_arn
  api_key_secret_arn         = module.secrets.api_key_secret_arn
  db_credentials_secret_arn  = module.secrets.db_credentials_secret_arn
  llm_credentials_secret_arn = module.secrets.llm_credentials_secret_arn
  storage_bucket_arn         = module.storage.bucket_arn
}
