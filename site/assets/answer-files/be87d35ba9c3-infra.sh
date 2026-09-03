#!/usr/bin/env bash
# =============================================================================
# AlloyDB 基础设施与数据管理命令（订单/退款库）
# 所有 gcloud 命令均严格取自 Skill 文档：
#   - references/cli-usage.md  （集群/实例/备份/扩缩容命令）
#   - references/iam-security.md（IAM 角色绑定与 IAM 数据库用户）
# 执行前需：安装 Google Cloud SDK 并完成 gcloud auth login（SKILL.md 第25行）。
# 占位符：PROJECT_ID / REGION / CLUSTER / VPC_NAME / SA_EMAIL 需替换为真实值。
# =============================================================================
set -euo pipefail

PROJECT_ID="YOUR_PROJECT_ID"
REGION="us-central1"            # 与定价口径一致（成本测算使用 us-central1）
CLUSTER="orders-refunds-cluster"
PRIMARY="orders-primary"
READPOOL="orders-readpool"
VPC_NAME="your-vpc"             # Skill 示例使用 --network；新部署建议 PSC（见下方说明）

# 1. 启用 AlloyDB API（SKILL.md 第29-31行） -----------------------------------
gcloud services enable alloydb.googleapis.com --quiet

# 2. 创建集群（cli-usage.md 第11-14行） ---------------------------------------
#    生产环境应使用 IAM 数据库认证而非密码（SKILL.md 第40-42行）；
#    若必须用密码，应存入 Secret Manager，勿明文。
gcloud alloydb clusters create "$CLUSTER" --region="$REGION" \
    --password="REDACTED_FOR_PUBLIC_RELEASE" --network="$VPC_NAME" --quiet

# 3. 创建主实例 2 vCPU（cli-usage.md 第39-42行，SKILL.md Quick Start 用 2 vCPU）
gcloud alloydb instances create "$PRIMARY" --cluster="$CLUSTER" \
    --region="$REGION" --instance-type=PRIMARY --cpu-count=2 --quiet

# 4. 创建读池 2 节点、2 vCPU（cli-usage.md 第46-50行） ------------------------
#    分析/报表查询走读池，降低主实例负载。
gcloud alloydb instances create "$READPOOL" --cluster="$CLUSTER" \
    --region="$REGION" --instance-type=READ_POOL \
    --read-pool-node-count=2 --cpu-count=2 --quiet

# 5. 备份与恢复（数据管理） ---------------------------------------------------
# 5a. 连续备份/PITR 保留窗口设为 14 天（cli-usage.md 第103-106行；
#     core-concepts.md 第58行：默认14天，可配 1-35 天）
gcloud alloydb clusters update "$CLUSTER" --region="$REGION" \
    --continuous-backup-recovery-window-days=14

# 5b. 自动备份：每周一三五 01:00，保留 30 天（cli-usage.md 第110-117行）
gcloud alloydb clusters update "$CLUSTER" --region="$REGION" \
    --automated-backup-days-of-week=MONDAY,WEDNESDAY,FRIDAY \
    --automated-backup-start-times=01:00 \
    --automated-backup-retention-period=30d

# 5c. 按需备份（cli-usage.md 第90-93行）
gcloud alloydb backups create "${CLUSTER}-manual-$(date +%Y%m%d)" \
    --cluster="$CLUSTER" --region="$REGION"

# 6. 扩缩容（成本控制手段，均来自 cli-usage.md） ------------------------------
# 6a. 读池水平扩节点（第67-70行）
gcloud alloydb instances update "$READPOOL" --cluster="$CLUSTER" \
    --region="$REGION" --read-pool-node-count=4
# 6b. 主实例垂直扩 CPU（第74-77行）
gcloud alloydb instances update "$PRIMARY" --cluster="$CLUSTER" \
    --region="$REGION" --cpu-count=4
# 注：读池自动扩缩容（autoscaling）为 Preview 功能（core-concepts.md 第129行）。

# 7. IAM 数据库用户（不能仅用 SQL 创建，须先经控制平面注册） ------------------
#    iam-security.md 第90-93行
gcloud alloydb users create "app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --cluster="$CLUSTER" --region="$REGION" --type=IAM_USER

# 8. 连接侧最小权限：客户端服务账号只授 alloydb.client + serviceUsageConsumer
#    （iam-security.md 第24-33行；禁止用 roles/alloydb.admin 做连接）
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/alloydb.client"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:app-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/serviceusage.serviceUsageConsumer"

# 9. 恢复（演练用；恢复会创建新集群，core-concepts.md 第59/76行） -------------
# 9a. 从离散备份恢复（cli-usage.md 第128-131行）
# gcloud alloydb clusters restore "${CLUSTER}-restored" --region="$REGION" \
#     --backup="${CLUSTER}-manual-YYYYMMDD"
# 9b. PITR（时间戳须为 RFC3339，cli-usage.md 第135-139行）
# gcloud alloydb clusters restore "${CLUSTER}-pitr" --region="$REGION" \
#     --source-cluster="$CLUSTER" --point-in-time="2026-08-12T01:00:00.00Z"

# =============================================================================
# 控制台（Console）等价操作（依据 Skill 的“Provide Multiple Methods”指令）：
# - 按需备份：AlloyDB Clusters 页 → 点集群ID → Data protection → Create backup
#   （core-concepts.md 第63-71行）
# - 读池水平扩：集群页 → Instances → 读池行 Edit → Read pool nodes → Update
#   （core-concepts.md 第86-92行）
# - 垂直扩：集群页 → Instances → 目标实例 Edit → Machine configuration → Update
#   （core-concepts.md 第103-110行）
#
# 连接方式说明（core-concepts.md / iam-security.md）：
# - 新部署推荐 Private Service Connect（PSC）；PSA 用 VPC Peering。
# - 从 Cloud Run 连私网 IP 必须配 Serverless VPC Access 或 Direct VPC Egress。
# - 必须用 AlloyDB Auth Proxy 或语言连接器，不要直连 TCP；
#   直连私网 IP 虽可行但不推荐（缺少 IAM 认证与自动 mTLS）。
# - 若用公网 IP，Authorized Networks 严禁 0.0.0.0/0，且更应配合 Auth Proxy。
# =============================================================================
