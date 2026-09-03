# 模拟安全日志审计报告（security-audit）

- 审计对象：`incident_log.csv`（模拟数据，授权测试范围内）
- 执行依据：随包 Skill `gke-service-networking/SKILL.md`（实际读取版本）
- 生成时间：2026-08-26
- 审计性质：只读分析 + 修复建议，未执行任何破坏性或变更性操作

---

## 0. 执行范围与 Skill 适用性声明

本次任务被标注为“安全与合规”分类，但实际读取到的 `gke-service-networking/SKILL.md` 在 frontmatter 中声明：

```yaml
metadata:
  category: Networking
description: >-
  Configures GKE edge networking, traffic routing, load balancing, and private
  service endpoints. ...
  Don't use for core cluster IP planning, Dataplane V2 network policies, or
  node NAT egress (use gke-networking instead).
```

因此本报告严格遵守以下边界：

1. 该 Skill **不提供**日志取证、SIEM 规则、入侵检测或事件响应流程，本报告的分析方法为通用只读日志分析，修复建议仅引用 Skill 中真实存在的 GKE 联网控制项。
2. 该 Skill **明确排除** Dataplane V2 NetworkPolicy、节点 NAT 出口、集群核心 IP 规划。因此对数据库异常导出这类东西向流量问题，本报告**不**推荐 NetworkPolicy 作为修复项（超出本 Skill 范围），而改用 Skill 覆盖的 PSC / 内部负载均衡 / 边界 WAF 等控制。
3. 所有 YAML 均为 Skill 示例形态的建议，未在任何真实集群执行 `kubectl apply` 或 `gcloud` 变更。

---

## 1. 输入数据概览与数据质量约束

`incident_log.csv` 共 6 条事件记录，时间窗口 2026-08-12 09:00:12Z ~ 09:09:00Z，约 9 分钟。

| # | 时间 (UTC) | 系统 | 严重级 | 事件 | 用户 | 源 IP |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | (空) | malformed_record | (空) | (空) |

### 数据质量问题（约束一）

- 文件扩展名为 `.csv`，但实际为**竖线分隔的 Markdown 表格**，并非标准逗号分隔。若直接用通用 CSV 解析器会把整行读为单字段，影响自动化统计。本报告已人工规整。
- 第 6 条 `malformed_record` 的 `severity / user / source_ip` 均为空，无法参与基于字段的聚合。
- 三个源 IP 均属于 IANA 文档保留段（192.0.2.0/24、198.51.100.0/24、203.0.113.0/24），符合“模拟数据”特征，不能用于真实地理定位或威胁情报比对。

---

## 2. 风险分级与证据

采用四级：`低 / 中 / 高 / 严重`。分级同时考虑事件本身严重级、时间相关性、同源聚合与可归因性。

### 事件 A：admin 账号暴力破解尝试 — 风险：中

- 证据：记录 #2、#3，同一源 IP `198.51.100.23` 在 4 秒内对 `admin` 账号连续两次 `login_failed`。
- 判断：样本量小（仅 2 次），未达典型爆破阈值，但针对高权限账号 `admin`、时间密集，定为“中”。若后续窗口内同 IP 失败次数继续上升，应升级为“高”。
- 归因：源 IP 明确，用户名为 `admin`，可归因性高。

### 事件 B：service-a 令牌作用域不匹配 — 风险：高

- 证据：记录 #4，`api` 系统，`severity=high`，`token_scope_mismatch`，主体 `service-a`，源 IP `203.0.113.8`。
- 判断：服务账号使用了超出其授权范围的令牌，是典型的权限提升/令牌滥用信号，定为“高”。
- 归因：用户字段为服务名 `service-a`，可定位到具体工作负载，但无法区分是配置错误还是令牌被盗。

### 事件 C：数据库异常导出 — 风险：严重

- 证据：记录 #5，`db` 系统，`severity=critical`，`unexpected_export`，用户 `unknown`，源 IP `203.0.113.8`。
- 关键关联（约束二：归因冲突）：事件 C 与事件 B 同源 IP `203.0.113.8`，且时间上 B(09:04:02) → C(09:07:30) 仅间隔约 3.5 分钟。最合理假设是：`service-a` 的越权令牌被用于访问并导出数据库。但事件 C 的 `user=unknown`，**无法在日志层面直接证明**操作者就是 `service-a`，存在“同源巧合 / 代理出口 / NAT 共享”的替代解释。
- 判断：即便归因存疑，`critical` 级数据导出本身定为“严重”；在结论中保留归因不确定性，不做有罪推定。

### 事件 D：日志记录损坏 — 风险：中（完整性）

- 证据：记录 #6，`malformed_record`，关键字段全空，发生在严重导出之后约 1.5 分钟。
- 两种解释：(a) 采集管道/序列化故障；(b) 攻击者尝试擦除或污染日志以掩盖行踪。在安全审计语境下不能默认 (a)。
- 判断：定为“中”，作为日志完整性事件单独跟踪，不与事件 C 合并定级。

### 事件 E：alice 正常登录 — 风险：低（基线）

- 证据：记录 #1，`login_success`，`severity=info`。
- 判断：无异常，作为时间基线保留。源 IP `192.0.2.10` 与后续事件无重叠。

---

## 3. 关键取舍、依赖与风险

| 维度 | 取舍说明 |
|---|---|
| 归因 vs 证据充分性 | 事件 B/C 同源强相关，但 C 的 user 为空。本报告选择“严重定级 + 标注归因不确定”，而非直接定性为 service-a 数据外泄，避免误报扩大化。 |
| Skill 范围 vs 修复完整性 | 数据库东西向访问控制最直接的手段是 NetworkPolicy，但 SKILL.md 明确将 Dataplane V2 NetworkPolicy 排除在外。本报告改用 Skill 覆盖的 PSC + 内部 LB 收敛数据库暴露面，牺牲了“东西向细粒度策略”这一维度，换取“严格在 Skill 范围内”的合规性。 |
| 数据格式 vs 自动化 | 输入为伪 CSV，未编写解析脚本，采用人工规整以避免对脏数据做错误聚合；代价是不可复现的统计量。 |
| 模拟数据 vs 真实处置 | 所有 IP 为文档保留段，不做威胁情报查询、不封禁、不回连；仅输出建议。 |
| 变更风险 | 不执行任何 `kubectl` / `gcloud` 变更，所有 manifest 仅作建议；避免在未授权集群上造成业务中断。 |

依赖项：
- 修复落地依赖 GKE 集群为 VPC-native（Skill 第 5 节 NEG 前置条件）。
- Cloud Armor 策略需先在 Cloud Armor 侧创建，再通过 `BackendConfig` 引用（Skill 第 3 节），本报告不包含其创建命令。
- PSC 需预先规划专用 NAT 子网（`natSubnets`）。

---

## 4. 修复建议（仅引用 Skill 内控制项）

### 4.1 针对事件 A（web 暴力破解）— 边界防护

依据 Skill 第 3 节“Secure with Cloud Armor”与最佳实践第 2 条“Always protect public-facing endpoints with Cloud Armor”。

1. 在 Cloud Armor 安全策略中启用针对 `admin` 登录路径的速率限制/自适应防护（WAF 规则由 Cloud Armor 侧配置，不在本 Skill manifest 内）。
2. 通过 `BackendConfig` 绑定到 web Service：

```yaml
apiVersion: cloud.google.com/v1
kind: BackendConfig
metadata:
  name: web-backend-config
  namespace: {namespace}
spec:
  securityPolicy:
    name: {security_policy_name}
```

并在 Service 注解中关联：
`cloud.google.com/backend-config: '{"default": "web-backend-config"}'`

### 4.2 针对事件 B/C（API 越权 + 数据库导出）— 收敛暴露面

依据 Skill 第 6 节“Configure Private Service Connect (PSC)”：数据库不应通过公网或大平面暴露，改为通过 PSC 向授权消费者 VPC 私下发布，配合内部负载均衡。

```yaml
apiVersion: networking.gke.io/v1
kind: ServiceAttachment
metadata:
  name: db-service-attachment
  namespace: {namespace}
spec:
  connectionPreference: ACCEPT_AUTOMATIC
  natSubnets:
    - {nat_subnet_name}
  resourceRef:
    kind: Service
    name: {db_service_name}
```

说明：`connectionPreference: ACCEPT_AUTOMATIC` 会自动接受连接，在高安全场景下应评估改为手动审批（Skill 未给出该字段的其他取值示例，落地前需核对 GKE API 文档）。

### 4.3 针对公网入口统一加固 — Gateway API + TLS + NEG

依据 Skill 第 1、4、5 节与最佳实践第 1、3、4 条：

1. 优先使用 Gateway API 替代传统 Ingress（角色分离更清晰）。
2. 公网入口强制 HTTPS，使用 Google 托管证书或 Certificate Map，避免明文传输令牌。
3. 启用容器原生负载均衡（NEG），降低延迟并改善流量分布。

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: {gateway_name}
  namespace: {namespace}
  annotations:
    networking.gke.io/cert-map: {certificate_map_name}
spec:
  gatewayClassName: gke-l7-global-external-managed
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: {secret_name}
```

### 4.4 针对事件 D（日志完整性）

该问题超出本 Skill 范围（Skill 不覆盖日志管道）。建议转交日志/可观测性团队核查采集管道，并对 `db` 与 `web` 系统启用日志不可变存储与校验。本报告仅记录，不给出 Skill 外的具体实现。

---

## 5. 复测清单

复测均为只读或一次性校验，不启动长期服务，不执行破坏性操作。

- [ ] **数据格式**：将 `incident_log.csv` 重新导出为标准逗号分隔 CSV，确认 6 条记录字段数一致、无空 `severity`。
- [ ] **事件 A 复测**：在测试窗口内从受控源 IP 对 `admin` 发起 ≥5 次失败登录，确认 Cloud Armor 速率规则触发并在 `BackendConfig` 绑定的 Service 上生效（只读查 Cloud Armor 日志，不封禁真实用户）。
- [ ] **事件 B 复测**：用 `service-a` 的令牌调用超出其 scope 的 API，确认网关返回 403 且产生 `token_scope_mismatch` 告警；同时验证令牌不经过 HTTP 明文入口。
- [ ] **事件 C 复测**：从非授权 VPC 尝试访问数据库 PSC endpoint，确认连接被拒绝；从授权消费者 VPC 验证 `ServiceAttachment` 可达。
- [ ] **TLS 复测**：对 Gateway 公网域名执行一次性 `curl -I https://{domain}`，确认 443 监听且证书有效；确认 80 端口无明文业务流量。
- [ ] **NEG 复测**：`kubectl get svc {service_name} -o yaml` 只读检查 `cloud.google.com/neg` 注解与后端 NEG 健康状态。
- [ ] **日志完整性复测**：重放 09:09 前后的采集管道，确认 `malformed_record` 是管道问题还是人为注入；若无法复现，升级为安全事件。
- [ ] **归因闭环**：拉取 `203.0.113.8` 在 09:00–09:10 的全量会话（若真实环境有此数据），验证事件 B 与 C 是否为同一主体。

---

## 6. 结论

1. 在 9 分钟窗口内识别出 **1 严重（数据库异常导出）、1 高（令牌越权）、2 中（admin 爆破尝试、日志损坏）、1 低（基线登录）**。
2. 最值得关注的线索是 `203.0.113.8` 在 3.5 分钟内先后触发 `token_scope_mismatch` 与 `unexpected_export`，存在越权令牌被用于数据导出的合理怀疑，但因导出事件 `user=unknown`，归因未闭环，需复测确认。
3. 修复建议严格限定在 `gke-service-networking` Skill 覆盖范围内：Cloud Armor 边界防护、PSC 私有发布、Gateway API + 托管证书 + NEG 公网入口加固。东西向 NetworkPolicy 因被 Skill 明确排除而未纳入。
4. 输入文件存在格式不规范与一条空字段记录，已在报告中如实标注，未做编造或补全。

---

## 附录 A：实际读取的 Skill 文件相对路径

- `gke-service-networking/SKILL.md`（ZIP 内唯一文件，解压后相对路径）

## 附录 B：确实影响结果的 SKILL.md 规则

> “Don't use for core cluster IP planning, Dataplane V2 network policies, or node NAT egress (use gke-networking instead).”

该规则直接决定了本报告**不推荐** NetworkPolicy 作为数据库异常导出的修复手段，转而使用 Skill 覆盖的 PSC + 内部 LB 方案，是影响修复章节结论的关键约束。此外，frontmatter 中 `category: Networking` 与任务标注“安全与合规”不一致，促使本报告在第 0 节明确声明 Skill 适用性边界。
