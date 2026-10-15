# Region is a required, user-configurable variable with no default so no personal
# location assumption is baked in.
variable "aws_region" {
  description = "AWS region to deploy into (e.g. us-east-1)."
  type        = string
}

variable "project" {
  description = "Resource name prefix."
  type        = string
  default     = "ragbench"
}

variable "image_tag" {
  description = "Container image tag to run."
  type        = string
  default     = "latest"
}

# The costly runtime (ECS Fargate service) is OPT-IN and defaults to OFF. ECR and
# the log group are cheap and always created.
variable "enable_service" {
  description = "Create the ECS Fargate service (incurs ongoing cost)."
  type        = bool
  default     = false
}

variable "container_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "container_memory" {
  description = "Fargate task memory (MiB)."
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Number of running tasks (SQLite backend supports only 1)."
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days (cost control)."
  type        = number
  default     = 14
}

variable "ingress_cidrs" {
  description = "CIDRs allowed to reach the service. Empty = no public ingress."
  type        = list(string)
  default     = []
}
