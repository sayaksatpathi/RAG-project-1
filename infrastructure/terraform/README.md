# RAGBench Terraform (opt-in AWS)

Minimal, secure, cost-aware infrastructure to run the RAGBench container on AWS.
**Opt-in and not auto-applied.** No resources are created until you run
`terraform apply` with your own credentials.

## Resource inventory

| Resource | Created | Cost |
|---|---|---|
| ECR repository (+ lifecycle: keep 5) | always | ~free (storage only) |
| CloudWatch log group (retention configurable) | always | low |
| IAM task execution role | only if `enable_service` | free |
| Security group | only if `enable_service` | free |
| ECS Fargate cluster + task def + service | only if `enable_service` | **ongoing compute cost** |

The costly runtime (`enable_service`) defaults to **false**.

## Security / exposure

- Region is a required variable (`aws_region`) — no location is hard-coded.
- The service is **private by default**: `assign_public_ip = false` and the
  security group opens port 8000 only to CIDRs you list in `ingress_cidrs`
  (empty = no public ingress). Do not set `0.0.0.0/0` unless you intend it.
- IAM uses the AWS-managed `AmazonECSTaskExecutionRolePolicy` (least privilege
  for pulling the image and writing logs).
- No secrets are stored in this configuration. Provide `RAGBENCH_API_TOKEN` via
  a real deployment's secret mechanism.

## Validation status

- `terraform fmt` — clean.
- `terraform init -backend=false` + `terraform validate` — **VERIFIED: "the
  configuration is valid."** (run 2026-10-15).
- `terraform plan` / `apply` — **NOT RUN**: requires AWS credentials and would
  reach AWS. Do not apply without explicit authorization.

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars   # set aws_region
terraform init
terraform validate
terraform plan                                 # review; needs AWS creds
terraform apply                                # creates resources (your account)
# push the image:
#   aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-url>
#   docker build -t <ecr-url>:v1 .. && docker push <ecr-url>:v1
#   terraform apply -var enable_service=true -var image_tag=v1
```

## Teardown and data loss

```bash
terraform destroy
```

`destroy` removes everything, including the ECR repository (`force_delete` is on,
so stored images are deleted) and the CloudWatch log group (logs are lost).
There is no managed database here; the container's SQLite lives on ephemeral
task storage and is not persisted by this configuration — treat any Fargate data
as disposable. State is stored locally by default (`terraform.tfstate`); use a
remote backend with locking for shared/real use.
