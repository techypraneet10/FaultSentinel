# ==============================================================================
# SentinelLog Production Infrastructure Definition (Terraform >= 1.5.0)
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
    bucket         = "sentinellog-terraform-state-production"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "sentinellog-tf-locks-production"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "SentinelLog"
      Environment = "production"
      ManagedBy   = "Terraform"
    }
  }
}

module "networking" {
  source               = "../../modules/networking"
  environment          = "production"
  vpc_cidr             = "10.0.0.0/16"
  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24"]
  availability_zones   = ["us-east-1a", "us-east-1b"]
}

module "ecr" {
  source          = "../../modules/ecr"
  environment     = "production"
  repository_name = "sentinellog"
}

module "alb" {
  source                = "../../modules/alb"
  environment           = "production"
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  certificate_arn       = var.certificate_arn
}

module "storage" {
  source        = "../../modules/storage"
  environment   = "production"
  bucket_prefix = "sentinellog-artifacts"
}

module "secrets" {
  source      = "../../modules/secrets"
  environment = "production"
}

module "database" {
  source                = "../../modules/database"
  environment           = "production"
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id
  database_name         = "sentinellog_production"
  backup_retention_days = 30
}

module "ecs" {
  source                     = "../../modules/ecs"
  environment                = "production"
  image_uri                  = var.image_uri
  cpu                        = 2048
  memory                     = 4096
  desired_count              = 4
  private_subnet_ids         = module.networking.private_subnet_ids
  ecs_security_group_id      = module.networking.ecs_security_group_id
  target_group_arn           = module.alb.target_group_arn
  api_key_secret_arn         = module.secrets.api_key_secret_arn
  db_credentials_secret_arn  = module.secrets.db_credentials_secret_arn
  llm_credentials_secret_arn = module.secrets.llm_credentials_secret_arn
  storage_bucket_arn         = module.storage.bucket_arn
}
