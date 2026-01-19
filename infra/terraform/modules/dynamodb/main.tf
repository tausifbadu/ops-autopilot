# DynamoDB Module - Creates DynamoDB tables

variable "environment" {
  type = string
}

resource "aws_dynamodb_table" "workflow_registry" {
  name           = "${var.environment}-ops-autopilot-workflow-registry"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "workflow_name"
  
  attribute {
    name = "workflow_name"
    type = "S"
  }
  
  tags = {
    Name        = "${var.environment}-workflow-registry"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "incidents" {
  name           = "${var.environment}-ops-autopilot-incidents"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "incident_id"
  
  attribute {
    name = "incident_id"
    type = "S"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Name        = "${var.environment}-incidents"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "baselines" {
  name           = "${var.environment}-ops-autopilot-baselines"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "baseline_key"
  
  attribute {
    name = "baseline_key"
    type = "S"
  }
  
  tags = {
    Name        = "${var.environment}-baselines"
    Environment = var.environment
  }
}

output "table_names" {
  value = {
    workflow_registry = aws_dynamodb_table.workflow_registry.name
    incidents         = aws_dynamodb_table.incidents.name
    baselines         = aws_dynamodb_table.baselines.name
  }
}
