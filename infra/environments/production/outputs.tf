output "alb_dns_name" {
  value       = module.alb.alb_dns_name
  description = "Public DNS of the production ALB"
}

output "ecr_repository_url" {
  value       = module.ecr.repository_url
  description = "ECR repository URL for production"
}

output "ecs_cluster_name" {
  value       = module.ecs.cluster_name
  description = "ECS cluster name for production"
}

output "ecs_service_name" {
  value       = module.ecs.service_name
  description = "ECS service name for production"
}

output "database_endpoint" {
  value       = module.database.cluster_endpoint
  description = "Writer endpoint for production Aurora PostgreSQL"
}
