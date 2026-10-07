# ==============================================================================
# SentinelLog Database Module (Aurora PostgreSQL Serverless v2, Private, KMS)
# ==============================================================================

resource "aws_db_subnet_group" "db" {
  name       = "sentinellog-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "sentinellog-${var.environment}-db-subnet-group"
    Environment = var.environment
  }
}

# Rule 42: Database security group accepts ingress strictly from ECS tasks
resource "aws_security_group" "db" {
  name        = "sentinellog-${var.environment}-db-sg"
  description = "Security group for Aurora PostgreSQL"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow inbound PostgreSQL connection from ECS tasks strictly"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  tags = {
    Name        = "sentinellog-${var.environment}-db-sg"
    Environment = var.environment
  }
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier     = "sentinellog-${var.environment}-aurora"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = "15.4"
  database_name          = var.database_name
  master_username        = "sentineladmin"
  manage_master_user_password = true

  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]

  storage_encrypted   = true
  deletion_protection = var.environment == "production" ? true : false

  backup_retention_period = var.backup_retention_days
  preferred_backup_window = "03:00-04:00"

  serverlessv2_scaling_configuration {
    max_capacity = var.environment == "production" ? 16 : 4
    min_capacity = 0.5
  }

  tags = {
    Name        = "sentinellog-${var.environment}-aurora"
    Environment = var.environment
  }
}

resource "aws_rds_cluster_instance" "instances" {
  count              = var.environment == "production" ? 2 : 1
  identifier         = "sentinellog-${var.environment}-aurora-${count.index + 1}"
  cluster_identifier = aws_rds_cluster.aurora.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.aurora.engine
  engine_version     = aws_rds_cluster.aurora.engine_version

  publicly_accessible = false
}
