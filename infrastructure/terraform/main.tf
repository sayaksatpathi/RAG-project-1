provider "aws" {
  region = var.aws_region
}

locals {
  name = var.project
  tags = {
    Project   = var.project
    ManagedBy = "terraform"
  }
}

# --- Always created (cheap) -------------------------------------------------

# Container registry for the image. Scans on push; keeps only recent images.
resource "aws_ecr_repository" "api" {
  name                 = "${local.name}-api"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true # allow teardown without manual image cleanup

  image_scanning_configuration {
    scan_on_push = true
  }
  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/${local.name}/api"
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

# --- Opt-in runtime (ongoing cost; default OFF) -----------------------------

data "aws_vpc" "default" {
  count   = var.enable_service ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.enable_service ? 1 : 0
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

resource "aws_iam_role" "task_execution" {
  count = var.enable_service ? 1 : 0
  name  = "${local.name}-task-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  count      = var.enable_service ? 1 : 0
  role       = aws_iam_role.task_execution[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_security_group" "api" {
  count       = var.enable_service ? 1 : 0
  name        = "${local.name}-api"
  description = "RAGBench API. No public ingress unless ingress_cidrs is set."
  vpc_id      = data.aws_vpc.default[0].id

  dynamic "ingress" {
    for_each = length(var.ingress_cidrs) > 0 ? [1] : []
    content {
      description = "HTTP"
      from_port   = 8000
      to_port     = 8000
      protocol    = "tcp"
      cidr_blocks = var.ingress_cidrs
    }
  }

  egress {
    description = "all egress"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = local.tags
}

resource "aws_ecs_cluster" "this" {
  count = var.enable_service ? 1 : 0
  name  = local.name
  tags  = local.tags
}

resource "aws_ecs_task_definition" "api" {
  count                    = var.enable_service ? 1 : 0
  family                   = "${local.name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.task_execution[0].arn

  container_definitions = jsonencode([{
    name         = "api"
    image        = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
    essential    = true
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "RAGBENCH_STORAGE", value = "sqlite" },
      { name = "RAGBENCH_EMBEDDING_PROVIDER", value = "fake" },
      { name = "RAGBENCH_LLM_PROVIDER", value = "mock" }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
  tags = local.tags
}

resource "aws_ecs_service" "api" {
  count           = var.enable_service ? 1 : 0
  name            = "${local.name}-api"
  cluster         = aws_ecs_cluster.this[0].id
  task_definition = aws_ecs_task_definition.api[0].arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default[0].ids
    security_groups  = [aws_security_group.api[0].id]
    assign_public_ip = false # private by default; do not expose accidentally
  }
  tags = local.tags
}
