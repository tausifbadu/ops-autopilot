# Create an EMR Studio Workspace and Open Jupyter (EC2 Cluster + Runtime Role)

EMR Studio **workspaces** cannot be created with Terraform (no AWS API). Create the workspace in the EMR Studio UI and attach your cluster and **Runtime role** using the values below.

## If the Runtime Role dropdown is empty

The Terraform module was updated so that:

1. **EMR security configuration** enables application-scoped IAM (runtime roles) on the cluster.
2. The **EC2 role** can be used as a runtime role (trust + AssumeRole/TagSession on self).
3. The **session policy** grants `GetClusterSessionCredentials` for that role so it appears in the dropdown.

You must **apply** and **recreate the cluster** for the security configuration to take effect (security config is set only at cluster launch):

```powershell
cd infra/terraform
terraform apply
# If the cluster already exists, Terraform may require replacing it (destroy + create) to apply the security configuration. Approve if prompted.
```

If you use **IAM auth** and do **not** have a session mapping, your IAM user or role must allow `elasticmapreduce:GetClusterSessionCredentials` with a condition on `elasticmapreduce:ExecutionRoleArn` = the EC2 role ARN. The module’s session policy includes this for users who have a session mapping.

## 1. Get the values you need

From your `infra/terraform` directory run:

```powershell
terraform output emr_studio_url
terraform output emr_studio_cluster_id
terraform output emr_studio_cluster_name
terraform output emr_studio_execution_role_arn
```

Or in one go:

```powershell
terraform output -json | ConvertFrom-Json | Select-Object emr_studio_url, emr_studio_cluster_id, emr_studio_cluster_name, emr_studio_execution_role_arn
```

You need:

- **Studio URL** – open this in your browser
- **Cluster ID** – e.g. `j-2H3EEJJ1EOUTN` (to identify the EMR EC2 cluster)
- **Cluster name** – e.g. `dev-ops-autopilot-emr-studio`
- **Execution role ARN** – e.g. `arn:aws:iam::009160054691:role/dev-ops-autopilot-emr-studio-ec2` (use this when attaching the cluster / running the notebook)

## 2. Open EMR Studio

1. Open **Studio URL** in your browser (from `terraform output emr_studio_url`).
2. Sign in with AWS (IAM user or role that has access to this Studio).

## 3. Create a workspace

1. In EMR Studio, click **Create workspace** (or **Create a Workspace**).
2. **Name**: e.g. `my-notebooks`.
3. **Description** (optional): e.g. `Jupyter on EMR EC2 cluster`.
4. Expand **Advanced configuration** (or equivalent).
5. **Attach workspace to an EMR cluster**:
   - Turn on “Attach to cluster” (or similar).
   - In the list, select the cluster whose **name** or **ID** matches:
     - **Cluster name**: `terraform output -raw emr_studio_cluster_name`
     - **Cluster ID**: `terraform output -raw emr_studio_cluster_id`
6. **Execution role** (for running notebooks on the cluster):
   - Choose **Select role** / **Execution role**.
   - Paste or select the **Execution role ARN** from:
     - `terraform output -raw emr_studio_execution_role_arn`
   - Example: `arn:aws:iam::009160054691:role/dev-ops-autopilot-emr-studio-ec2`
7. Click **Create workspace** (or **Create**).

## 4. Open Jupyter and use the cluster

1. Open the workspace you just created.
2. Create a notebook: **File → New → Notebook** (or **+** and choose **Notebook**).
3. When asked for **kernel** or **cluster**:
   - Select the **EMR EC2 cluster** you attached (same cluster name/ID as above).
   - The **execution role** should already be the one you set (e.g. `dev-ops-autopilot-emr-studio-ec2`).
4. Choose **PySpark** (or **Spark**) and start coding.

## Summary: what to select

| In EMR Studio UI      | Value to use |
|-----------------------|--------------|
| **Cluster**           | EMR EC2 cluster: name = `emr_studio_cluster_name`, ID = `emr_studio_cluster_id` |
| **Execution role**    | Role ARN = `emr_studio_execution_role_arn` (e.g. `.../dev-ops-autopilot-emr-studio-ec2`) |

The **execution role** is the EMR cluster’s EC2 role (`dev-ops-autopilot-emr-studio-ec2`); it already has S3 and EMR permissions so notebooks can run on the cluster.

## If you don’t see “Attach to cluster” or “Execution role”

- UI wording can vary by region/version; look for **Advanced configuration**, **Attach cluster**, **Compute**, or **Execution role**.
- Ensure the cluster is in **Waiting** state in EMR Console (Clusters).
- Ensure your IAM user/role has EMR Studio and EMR cluster permissions.

## Optional: one-line values for copy-paste

```powershell
# PowerShell
Write-Host "Studio URL:        $(terraform output -raw emr_studio_url)"
Write-Host "Cluster ID:        $(terraform output -raw emr_studio_cluster_id)"
Write-Host "Cluster name:      $(terraform output -raw emr_studio_cluster_name)"
Write-Host "Execution role:    $(terraform output -raw emr_studio_execution_role_arn)"
```

Use these when creating the workspace and when opening a Jupyter notebook so you select the **EMR EC2 instance** (cluster) and this **service/execution role**.
