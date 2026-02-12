# EMR Studio Cluster Module

Creates a **persistent EMR on EC2 cluster** (single master node, m5.xlarge by default) with **EMR Studio** for Jupyter notebooks.

## What You Get

- **EMR cluster**: Single-node EC2 (master only), Spark + Livy + JupyterEnterpriseGateway
- **EMR Studio**: Web UI to create workspaces and run Jupyter notebooks against the cluster
- **S3 logging**: Log URI set at creation so step/container logs are written to S3
- **IAM roles** and **security groups** for cluster and Studio

## Usage

The root `main.tf` wires the module with VPC and S3 from existing modules:

```hcl
module "emr_studio_cluster" {
  source = "./modules/emr_studio_cluster"

  environment         = var.environment
  vpc_id              = module.vpc.vpc_id
  subnet_id           = module.vpc.public_subnet_ids[0]
  studio_subnet_ids   = module.vpc.public_subnet_ids
  data_bucket_name    = module.s3.bucket_names["data"]
  log_prefix          = "emr-studio-logs/"
  master_instance_type = "m5.xlarge"
}
```

## Accessing Jupyter

1. Deploy: `terraform apply`
2. Get Studio URL: `terraform output emr_studio_url`
3. Open the URL in a browser and sign in with AWS IAM
4. **Create a workspace**: In EMR Studio click **Create workspace** → in **Advanced configuration** attach your **EMR EC2 cluster** (use cluster name or ID from `terraform output emr_studio_cluster_name` / `emr_studio_cluster_id`) and set **Execution role** to the EC2 role ARN: `terraform output -raw emr_studio_execution_role_arn`
5. Open the workspace and create a Jupyter notebook (PySpark kernel); select the same cluster and execution role.

See **[docs/EMR_STUDIO_WORKSPACE.md](../../docs/EMR_STUDIO_WORKSPACE.md)** for step-by-step and the script **scripts/emr-studio-workspace-values.ps1** to print all values.

## Optional: Session mappings (Terraform-managed)

Set `studio_session_identity_id` to an IAM user’s ID (e.g. from `aws iam get-user`) so that user gets a session mapping. Or use `studio_session_mappings` for multiple users/groups.

## Inputs

| Name | Description | Default |
|-----|-------------|--------|
| `environment` | Environment name | required |
| `vpc_id` | VPC for cluster and Studio | required |
| `subnet_id` | Subnet for master node | required |
| `studio_subnet_ids` | Subnets for EMR Studio | required |
| `data_bucket_name` | S3 bucket for data/logs/workspace | required |
| `log_prefix` | S3 prefix for EMR logs | `"emr-logs/"` |
| `master_instance_type` | Master instance type | `"m5.xlarge"` |
| `release_label` | EMR release | `"emr-6.15.0"` |
| `cluster_name` | Cluster name | auto |
| `studio_name` | Studio name | auto |
| `key_name` | EC2 key pair for SSH | `null` |
| `workspace_s3_bucket` | Override workspace bucket | `null` (uses data bucket) |
| `studio_session_identity_id` | Single IAM user ID for one session mapping | `null` |
| `studio_session_mappings` | List of `{ identity_type, identity_id? }` or `{ identity_type, identity_name? }` | `[]` |

## Outputs

- `cluster_id`, `cluster_name`, `cluster_master_public_dns`
- `studio_id`, `studio_url`, `studio_name`
- `log_uri`, `workspace_s3_path`
- IAM role ARNs

## Cost

Cluster is persistent until you terminate it. Approximate cost: ~$0.19/hr for m5.xlarge plus EMR. Terminate when not in use: AWS Console (EMR → Clusters) or `terraform destroy -target=module.emr_studio_cluster`.
