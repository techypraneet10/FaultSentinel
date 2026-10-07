output "cluster_name" {
  value       = aws_ecs_cluster.cluster.name
  description = "Name of the ECS Cluster"
}

output "service_name" {
  value       = aws_ecs_service.app.name
  description = "Name of the ECS Service"
}

output "task_definition_arn" {
  value       = aws_ecs_task_definition.app.arn
  description = "ARN of the active task definition"
}
