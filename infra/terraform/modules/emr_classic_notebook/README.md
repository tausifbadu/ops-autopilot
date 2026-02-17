# EMR Classic Notebook Module

Creates a **persistent EMR on EC2 cluster** (single master node, m5.xlarge by default) with **JupyterHub 1.5** for Jupyter notebook access via SSH tunnel.

## What You Get

- **EMR cluster**: Single-node EC2 (master only), m5.xlarge, with Spark + Livy + JupyterEnterpriseGateway + **JupyterHub 1.5**
- **JupyterHub**: On the master (port 9443); access via SSH tunnel
- **Glue Data Catalog**: Hive metastore backed by Glue so Spark SQL queries work on Glue tables
- **IAM roles**: EMR service role, EC2 instance role (S3 + Glue)
- **Security groups**: Master and slave SGs — both with `revoke_rules_on_delete = true`
- **S3 logging**: Log URI for step/container/YARN logs

## Usage

```hcl
module "emr_notebook" {
  source = "./modules/emr_classic_notebook"

  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  subnet_id            = module.vpc.public_subnet_ids[0]
  data_bucket_name     = module.s3.bucket_names["data"]
  log_prefix           = "emr-notebook-logs/"
  master_instance_type = "m5.xlarge"
  key_name             = "emr-notebook-key"
  ssh_allowed_cidrs    = ["0.0.0.0/0"]
}
```

## Accessing Jupyter Notebooks (JupyterHub)

JupyterHub runs on the master node (port **9443**). Use an SSH tunnel then open JupyterHub in your browser. **You need an EC2 key pair (PEM) and must set `key_name` and `ssh_allowed_cidrs`** (see [PEM key (Windows)](#pem-key-windows) below).

1. SSH tunnel (use the cluster key pair and master DNS):
   ```bash
   ssh -i /path/to/your-key.pem -L 9443:localhost:9443 hadoop@$(terraform output -raw emr_notebook_master_dns)
   ```
   On **Windows (PowerShell)** use the full path to the PEM, e.g.:
   ```powershell
   ssh -i C:\Users\YourName\.ssh\emr-key.pem -L 9443:localhost:9443 hadoop@<master_dns>
   ```
2. In your browser open: **https://localhost:9443**
3. Accept the self-signed certificate; log in with the JupyterHub user(s) configured on the cluster (see [Adding Jupyter Notebook users](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-jupyterhub-user-access.html)).

You can also use the EMR Console → cluster → **Application user interfaces** → JupyterHub when the master is reachable.

### PEM key (Windows)

To SSH to the master (and use JupyterHub or port-forward), you need a **.pem** key and the cluster must be launched with that key (`key_name`).

1. **Create and download the key in AWS**
   - **Console:** EC2 → **Key Pairs** (left menu, under Network & Security) → **Create key pair** → name e.g. `emr-notebook-key`, type **RSA**, format **.pem** → Create. The browser downloads the `.pem` file (you get it only once).
   - **CLI:** `aws ec2 create-key-pair --key-name emr-notebook-key --query KeyMaterial --output text > emr-notebook-key.pem`

2. **Save it on Windows**
   - Put the file somewhere safe, e.g. `C:\Users\<YourUsername>\.ssh\emr-notebook-key.pem`.
   - Restrict permissions (optional but recommended): right‑click → Properties → Security → Advanced → Disable inheritance → Remove all except your user → OK.

3. **Use the key with the module**
   - In the root `main.tf` where you call the module, set `key_name = "emr-notebook-key"` (the name you gave in AWS, not the file path).
   - Run `terraform apply`. If the cluster was created without a key, adding `key_name` forces a **new cluster** (replace). Existing clusters cannot get a key pair later.

4. **SSH from Windows**
   - Use **PowerShell** or **Windows Terminal** (OpenSSH is built in on Windows 10/11):
     ```powershell
     ssh -i C:\Users\YourName\.ssh\emr-notebook-key.pem -L 9443:localhost:9443 hadoop@<master_public_dns>
     ```
   - Or use **Git Bash** and the same `ssh -i ...` command with a path like `~/.ssh/emr-notebook-key.pem`.

## Inputs

| Name | Description | Default |
|------|-------------|---------|
| `environment` | Environment name (dev, staging, prod) | required |
| `vpc_id` | VPC for security groups | required |
| `subnet_id` | Subnet for the master node | required |
| `data_bucket_name` | S3 bucket for data/logs/workspace | required |
| `log_prefix` | S3 prefix for EMR logs | `"emr-notebook-logs/"` |
| `master_instance_type` | Instance type for master | `"m5.xlarge"` |
| `release_label` | EMR release | `"emr-6.15.0"` |
| `cluster_name` | Override cluster name | auto |
| `key_name` | EC2 key pair for SSH | `null` |
| `ssh_allowed_cidrs` | CIDRs allowed to SSH to master (port 22). Required for JupyterHub tunnel. e.g. `["0.0.0.0/0"]` or your IP | `[]` |

## Outputs

| Name | Description |
|------|-------------|
| `cluster_id` | EMR cluster ID |
| `cluster_name` | EMR cluster name |
| `master_public_dns` | Master node public DNS |
| `log_uri` | S3 log URI |
| `emr_service_role_arn` | EMR service role ARN |
| `emr_ec2_role_arn` | EC2 instance role ARN |
| `emr_ec2_instance_profile_arn` | EC2 instance profile ARN |
| `master_security_group_id` | Master SG ID |
| `slave_security_group_id` | Slave SG ID |

## Destroy Notes

All security groups use `revoke_rules_on_delete = true`. Terraform will automatically revoke all ingress/egress rules (including EMR-added UDP/ICMP cross-references) before deleting, avoiding the `DependencyViolation` errors.

If you still hit issues, check for orphaned ENIs:

```bash
aws ec2 describe-network-interfaces --filters "Name=group-id,Values=<sg-id>" --query "NetworkInterfaces[].NetworkInterfaceId" --output text
aws ec2 delete-network-interface --network-interface-id <eni-id>
```

## Cost

Cluster is persistent until terminated. Approximate cost: ~$0.24/hr (m5.xlarge $0.192 + EMR surcharge $0.048). Terminate when not in use via AWS Console or `terraform destroy -target=module.emr_notebook`.
