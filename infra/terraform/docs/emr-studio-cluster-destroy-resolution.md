# EMR Studio Cluster Destroy – DependencyViolation Resolution

## Issue

When commenting out the `emr_studio_cluster` module in `main.tf` and running `terraform apply`, Terraform attempted to destroy the EMR-related resources but failed with:

```
Error: deleting Security Group (sg-0269917657894b560): ... DependencyViolation: resource sg-0269917657894b560 has a dependent object
Error: deleting Security Group (sg-0d8575fd8c20e1d0e): ... DependencyViolation: resource sg-0d8575fd8c20e1d0e has a dependent object
```

- **sg-0269917657894b560** – EMR Studio workspace security group  
- **sg-0d8575fd8c20e1d0e** – EMR slave (core/task) security group  

Security groups could not be deleted until their dependent objects were removed.

---

## Root Causes

### 1. Orphaned ENIs (EMR Studio SG)

EMR Studio creates **Elastic Network Interfaces (ENIs)** when establishing workspace-to-cluster connections. After the EMR cluster and Studio are destroyed, these ENIs can remain and are still associated with the EMR Studio security group. AWS will not delete a security group while any ENI is attached to it.

### 2. Circular security group references (EMR Slave SG)

EMR automatically adds **extra rules** (UDP, ICMP, etc.) between the **master** and **slave** security groups at cluster launch. These rules are not managed by Terraform. The result:

- **Master SG** (`sg-03720fa5aa133707a`) had ingress rules referencing the **slave SG** (`sg-0d8575fd8c20e1d0e`).
- **Slave SG** had ingress rules referencing the **master SG**.

That circular reference blocked deletion of either group until the cross-references were removed.

---

## Resolution Steps

### Step 1: Find ENIs using the EMR Studio security group

```bash
aws ec2 describe-network-interfaces --filters "Name=group-id,Values=sg-0269917657894b560" --query "NetworkInterfaces[].{ID:NetworkInterfaceId,Status:Status}" --output table
```

### Step 2: Delete orphaned ENIs (Studio SG)

For each ENI returned (status `available` = not attached, safe to delete):

```bash
aws ec2 delete-network-interface --network-interface-id eni-xxxxxxxxx
```

Example (two ENIs were found and deleted):

```bash
aws ec2 delete-network-interface --network-interface-id eni-03fe9d030c680f617
aws ec2 delete-network-interface --network-interface-id eni-03df06f84ed67451b
```

After this, `terraform apply` could delete the EMR Studio security group (`sg-0269917657894b560`).

### Step 3: Identify what blocks the slave security group

- **Check for ENIs:**

  ```bash
  aws ec2 describe-network-interfaces --filters "Name=group-id,Values=sg-0d8575fd8c20e1d0e" --query "NetworkInterfaces[].NetworkInterfaceId" --output text
  ```

  (In this case, no ENIs were found.)

- **Find security groups that reference the slave SG:**

  ```bash
  aws ec2 describe-security-groups --filters "Name=ip-permission.group-id,Values=sg-0d8575fd8c20e1d0e" --query "SecurityGroups[].{GroupId:GroupId,GroupName:GroupName}" --output table
  ```

  This showed the **master SG** (`sg-03720fa5aa133707a`) had rules referencing the slave.

### Step 4: Break the circular reference by revoking cross-referencing rules

Rules were revoked in two places using `--ip-permissions` with JSON (e.g. from files to avoid shell escaping issues).

**From the slave SG** – revoke ingress from the master:

```bash
# revoke-slave.json:
[
  {"IpProtocol":"tcp","FromPort":0,"ToPort":65535,"UserIdGroupPairs":[{"GroupId":"sg-03720fa5aa133707a"}]},
  {"IpProtocol":"udp","FromPort":0,"ToPort":65535,"UserIdGroupPairs":[{"GroupId":"sg-03720fa5aa133707a"}]},
  {"IpProtocol":"icmp","FromPort":-1,"ToPort":-1,"UserIdGroupPairs":[{"GroupId":"sg-03720fa5aa133707a"}]}
]

aws ec2 revoke-security-group-ingress --group-id sg-0d8575fd8c20e1d0e --ip-permissions file://scripts/revoke-slave.json
```

**From the master SG** – revoke ingress from the slave:

```bash
# revoke-master.json:
[
  {"IpProtocol":"tcp","FromPort":0,"ToPort":65535,"UserIdGroupPairs":[{"GroupId":"sg-0d8575fd8c20e1d0e"}]},
  {"IpProtocol":"udp","FromPort":0,"ToPort":65535,"UserIdGroupPairs":[{"GroupId":"sg-0d8575fd8c20e1d0e"}]},
  {"IpProtocol":"icmp","FromPort":-1,"ToPort":-1,"UserIdGroupPairs":[{"GroupId":"sg-0d8575fd8c20e1d0e"}]}
]

aws ec2 revoke-security-group-ingress --group-id sg-03720fa5aa133707a --ip-permissions file://scripts/revoke-master.json
```

After revoking these rules, the circular dependency was removed and Terraform could delete both security groups.

### Step 5: Re-run Terraform

```bash
terraform apply
```

The remaining EMR Studio cluster resources (including the slave and master security groups) were destroyed successfully.

---

## Summary

| Blocker              | Cause                          | Fix                                                                 |
|----------------------|---------------------------------|---------------------------------------------------------------------|
| EMR Studio SG        | Orphaned ENIs from EMR Studio   | List ENIs by `group-id`, then `delete-network-interface` for each.  |
| EMR Slave SG         | Circular refs with Master SG    | Revoke cross-referencing ingress rules on both SGs via AWS CLI.    |

**Takeaway:** When tearing down EMR/EMR Studio, dependency violations on security groups are usually due to (1) ENIs still attached to the SG, or (2) other SGs (or the same SG) having rules that reference it. Resolve ENIs and cross-SG rules manually, then re-run `terraform apply`.
