# ECS Service Module

Creates an ECS Fargate service with task definition.

## Usage

```hcl
module "agent_host" {
  source = "./modules/ecs-service"
  
  name                = "agent-host"
  environment         = "dev"
  cluster_id          = aws_ecs_cluster.main.id
  ecr_repository_uri  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/ops-autopilot/agent-host:latest"
  task_role_arn       = aws_iam_role.task.arn
  execution_role_arn  = aws_iam_role.execution.arn
  log_group_name      = aws_cloudwatch_log_group.main.name
  
  cpu    = 2048
  memory = 4096
  
  subnet_ids        = [aws_subnet.private.id]
  security_group_ids = [aws_security_group.ecs.id]
}
```
