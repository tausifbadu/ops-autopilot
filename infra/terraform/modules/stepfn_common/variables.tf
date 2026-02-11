variable "name" {
  type        = string
  description = "State machine name."
}

variable "definition" {
  type        = string
  description = "Amazon States Language JSON definition."
}

variable "assume_role_service" {
  type        = string
  default     = "states.amazonaws.com"
  description = "Service principal for the Step Functions role."
}

variable "policy_json" {
  type        = string
  description = "IAM policy JSON for the Step Functions role."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags to apply."
}
