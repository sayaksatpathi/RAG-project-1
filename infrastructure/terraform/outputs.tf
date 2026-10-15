output "ecr_repository_url" {
  description = "Push the image here, then set image_tag."
  value       = aws_ecr_repository.api.repository_url
}

output "log_group" {
  description = "CloudWatch log group for the API."
  value       = aws_cloudwatch_log_group.api.name
}

output "service_name" {
  description = "ECS service name (null unless enable_service=true)."
  value       = var.enable_service ? aws_ecs_service.api[0].name : null
}
