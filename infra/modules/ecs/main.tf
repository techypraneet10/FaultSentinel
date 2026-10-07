# ==============================================================================
# SentinelLog ECS Fargate Module (Non-Root, Rolling Rollout, Secret Injection)
# ==============================================================================

resource "aws_ecs_cluster" "cluster" {
  name = "sentinellog-${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "sentinellog-${var.environment}-cluster"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "logs" {
  name              = "/ecs/sentinellog-${var.environment}"
  retention_in_days = var.environment == "production" ? 90 : 30

  tags = {
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# IAM Roles (Least-Privilege Task Execution & Task Runtime Roles)
# ------------------------------------------------------------------------------

resource "aws_iam_role" "task_execution" {
  name = "sentinellog-${var.environment}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Grant execution role access to read required Secrets Manager ARNs
resource "aws_iam_policy" "secrets_read" {
  name        = "sentinellog-${var.environment}-secrets-read-policy"
  description = "Allows ECS execution role to decrypt and fetch specified secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [
          var.api_key_secret_arn,
          var.db_credentials_secret_arn,
          var.llm_credentials_secret_arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_secrets" {
  role       = aws_iam_role.task_execution.name
  policy_arn = aws_iam_policy.secrets_read.arn
}

resource "aws_iam_role" "task_role" {
  name = "sentinellog-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })
}

# Task role S3 access to artifacts bucket
resource "aws_iam_policy" "s3_access" {
  name        = "sentinellog-${var.environment}-task-s3-policy"
  description = "Allows task runtime to access private S3 artifacts bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.storage_bucket_arn,
          "${var.storage_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_role_s3" {
  role       = aws_iam_role.task_role.name
  policy_arn = aws_iam_policy.s3_access.arn
}

# ------------------------------------------------------------------------------
# Task Definition (Strict Non-Root USER 10001, Graceful Shutdown, Secret Env)
# ------------------------------------------------------------------------------

resource "aws_ecs_task_definition" "app" {
  family                   = "sentinellog-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name      = "sentinellog-api"
      image     = var.image_uri
      essential = true
      user      = "10001:10001"

      stopTimeout = 30

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        { name = "SENTINELLOG_ENV", value = var.environment },
        { name = "SENTINELLOG_AUTH_ENABLED", value = "true" },
        { name = "SENTINELLOG_DEBUG", value = "false" },
        { name = "SENTINELLOG_ENFORCE_PRODUCTION_MODE", value = "true" }
      ]

      secrets = [
        { name = "SENTINELLOG_API_KEY", valueFrom = var.api_key_secret_arn },
        { name = "SENTINELLOG_LLM_API_KEY", valueFrom = var.llm_credentials_secret_arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.logs.name
          "awslogs-region"        = "us-east-1"
          "awslogs-stream-prefix" = "sentinellog"
        }
      }

      healthCheck = {
        command     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${var.container_port}/health/live')"]
        interval    = 15
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    }
  ])

  tags = {
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# ECS Service (Rolling Deploy: 100% Min Healthy, 200% Max Healthy)
# ------------------------------------------------------------------------------

resource "aws_ecs_service" "app" {
  name            = "sentinellog-${var.environment}-service"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "sentinellog-api"
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Environment = var.environment
  }
}
