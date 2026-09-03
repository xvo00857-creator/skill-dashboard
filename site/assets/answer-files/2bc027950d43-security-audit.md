# 模拟安全日志安全审计报告 / security-audit

- 报告日期：2026-08-13（Asia/Shanghai）
- 审计对象：`incident_log.csv`、`edge_cases.csv`（随题模拟日志，非真实目标数据）
- 执行 Skill：`case-review`（安全与合规 / Evidence Graph Review）
- 审查模式：离线只读（offline），未进行任何侦察、利用、动态插测或目标变更
- case-review 结果：**PASS**（`--strict --verify-hashes`，0 error / 0 warning，exit 0）

---

## 1. 结论摘要

在授权测试范围内对两份模拟日志做离线静态分析，共形成 **8 条发现**，其中：

| 等级 | 数量 | 发现编号 |
|---|---:|---|
| critical | 1 | F-004 |
| high | 3 | F-002、F-003、F-008 |
| medium | 2 | F-001、F-006 |
| low | 2 | F-005、F-007 |

最需优先处置的是 **F-004**：来源 IP `203.0.113.8` 先触发服务账号 `service-a` 的令牌权限范围不匹配（F-003 / E-003），约 3 分 28 秒后又以 `unknown` 身份触发 `critical` 级异常数据导出（E-004），构成疑似令牌盗用后数据外传的攻击链（P-001）。因缺少身份、主机与流量日志，该发现置信度为 medium、状态为 candidate，需补充日志后复测确认。

此外 `edge_cases.csv` 第 7 行包含以 `=` 开头的 `HYPERLINK` 公式注入载荷（F-008），且该字段使用反斜杠转义引号、不符合 CSV 标准，标准解析器会错列——这既是不安全输入问题，也是数据质量问题。

所有结论均有 Evidence 记录支撑，每条 Evidence 均提供可复现的只读命令；两个 CSV 工件已计算 SHA-256 并通过 `--verify-hashes` 校验。

---

## 2. 范围与授权声明

- 授权依据：用户明确要求“仅在授权测试范围内分析模拟安全日志”，输入为随附的模拟 CSV 文件。
- 网络模式：`offline`（见 `work/security-audit/scope.md`）。全程仅读取本地文件与运行本地 Python 脚本，未访问任何网络目标、未发送任何请求。
- 禁止行为遵守：依据 SKILL.md 第 21 行 “It MUST NOT perform reconnaissance, exploitation, dynamic instrumentation, or target changes”，本次未执行任何攻击性或目标变更操作；所有 `repro_command` 均为对本地 CSV 的只读 `awk`/`grep` 命令。
- 本报告不是法律意见，也不替代组织的证据保全流程。

---

## 3. 输入文件与完整性

| 文件 | 大小（字节） | SHA-256 |
|---|---:|---|
| `incident_log.csv` | 429 | `be958718de1678cdb5ee2758bedb8745dd07143930d19efe57b2e695eb60010c` |
| `edge_cases.csv` | 218 | `67fe12d762eb5ac0a48043121de7f2da8146004bb953c7206eca17f58fc85d87` |

原始文件已复制为 case 内工件：`work/security-audit/evidence/artifacts/`。哈希已写入各 Evidence 记录的 `content_hash`，并经 `review_case.py --verify-hashes` 校验通过（哈希不匹配在 Skill 中属 hard failure）。

---

## 4. 风险分级汇总表

| 编号 | 等级 | 状态 | 置信度 | 标题 | 证据 |
|---|---|---|---|---|---|
| F-004 | critical | candidate | medium | unknown 用户异常数据导出（与令牌异常同源 IP） | E-003, E-004 |
| F-002 | high | candidate | medium | admin 短时连续登录失败（疑似暴力破解） | E-002 |
| F-003 | high | validated | high | service-a 令牌权限范围不匹配 | E-003 |
| F-008 | high | validated | high | CSV 公式注入载荷（含非标准引号转义） | E-008 |
| F-001 | medium | validated | high | 日志记录字段缺失（畸形记录） | E-001 |
| F-006 | medium | validated | high | edge_cases 缺失 status/value | E-006 |
| F-005 | low | validated | high | edge_cases 重复记录 | E-005 |
| F-007 | low | validated | high | edge_cases 异常负值 | E-007 |

---

## 5. 详细发现

### F-004 / critical / candidate — unknown 用户异常数据导出（与令牌异常同源 IP）

- 证据：E-003、E-004（`incident_log.csv` 第 5、6 行）
- 现象：
  - `09:04:02` `service-a` 自 `203.0.113.8` 触发 `token_scope_mismatch`（high）。
  - `09:07:30` 同一 IP 以 `unknown` 用户触发 `unexpected_export`（critical）。
- 影响：存在令牌被盗用后进行数据外传的可能；用户字段为 `unknown`，无法仅凭当前日志确认身份与数据范围。
- 置信度：medium（同源 IP + 短时间窗 + 权限异常后紧接导出，相关性强；但缺少身份/主机/流量日志，不能确认外传成功）。
- 修复建议：
  1. 立即冻结 `203.0.113.8` 相关会话与令牌，核查导出内容、体量与去向。
  2. 关联身份系统/WAF/主机日志确认 `unknown` 真实身份与登录态。
  3. 对 db 导出增加审批与二次确认，禁止 `unknown` 身份执行导出。
  4. 按事件响应流程升级并保留现场。
- 复测方法：
  1. 以 unknown/匿名身份尝试导出，确认被阻断。
  2. 验证同源 IP 在 scope 异常后自动进入隔离/熔断。
  3. 复核导出审批与审计日志完整可查。

### F-002 / high / candidate — admin 短时连续登录失败（疑似暴力破解）

- 证据：E-002（`incident_log.csv` 第 3、4 行）
- 现象：`198.51.100.23` 在 4 秒内对 `admin` 连续两次 `login_failed`。
- 影响：若为暴力破解，admin 账户可能被攻破。
- 置信度：medium（仅 2 次失败，无成功登录记录，不能区分攻击与误输入）。
- 修复建议：
  1. 对 admin 登录失败配置速率限制与账户锁定/二次验证。
  2. 拉长时间窗（如 5 分钟）统计同 IP/同账户失败次数并设阈值告警。
  3. 核查 `198.51.100.23` 是否为可信管理网段。
- 复测方法：
  1. 模拟同 IP 对 admin 连续失败登录，确认触发锁定/告警。
  2. 验证阈值与白名单不会误封合法运维。

### F-003 / high / validated — service-a 令牌权限范围不匹配

- 证据：E-003（`incident_log.csv` 第 5 行）
- 现象：`service-a` 自 `203.0.113.8` 触发 `token_scope_mismatch`。
- 影响：服务账号令牌请求了超出其范围的资源，可能为令牌滥用、配置错误或被盗用。
- 修复建议：
  1. 核查 service-a 令牌签发范围与实际请求资源，吊销异常令牌。
  2. 对 scope 不匹配请求默认拒绝并告警。
  3. 轮换 service-a 凭据并审计其近期调用。
- 复测方法：
  1. 用超范围令牌重放请求，确认被拒绝并记录 high 级告警。
  2. 确认轮换后的新令牌仅含最小权限。

### F-008 / high / validated — CSV 公式注入载荷

- 证据：E-008（`edge_cases.csv` 第 7 行）
- 现象：`value` 字段为 `"=HYPERLINK(\"https://example.invalid\",\"do not execute\")"`，以 `=` 开头并含 `HYPERLINK` 公式。
- 附加问题：该字段使用反斜杠转义内嵌引号，而非 CSV 标准的双引号转义（`""`）；用 Python 标准 `csv` 解析器会将该行错列（解析为 5 个字段而非 4 个），存在解析差异风险。
- 影响：在 Excel/WPS 等表格软件中打开可能被解释执行公式/发起外联；非标准转义会导致下游解析错列。
- 修复建议：
  1. 导出/展示 CSV 时对以 `=`、`+`、`-`、`@` 开头的单元格前置单引号或强制文本格式。
  2. 写入 CSV 使用标准双引号转义，不要用反斜杠转义。
  3. 对用户输入做公式注入过滤与内容类型校验。
- 复测方法：
  1. 提交 `=CMD|...` 类载荷，确认导出后不被表格识别为公式。
  2. 用标准 `csv` 解析器读取，确认列数与表头一致、无错列。

### F-001 / medium / validated — 日志记录字段缺失（畸形记录）

- 证据：E-001（`incident_log.csv` 第 7 行：`2026-08-12T09:09:00Z,web,,malformed_record,,`）
- 影响：缺失 severity/user/source_ip 的记录无法参与告警关联与溯源，可能造成监控盲区。
- 修复建议：
  1. 采集端对必填字段做校验，缺字段时拒绝写入或标记 invalid 并单独告警。
  2. 对 `malformed_record` 建立独立计数与告警阈值。
  3. 排查 09:09:00 前后采集管道是否有截断/解析异常。
- 复测方法：
  1. 重新注入缺字段日志，确认被拒绝或进入隔离队列并产生告警。
  2. 复查 24 小时内 `malformed_record` 计数是否在阈值内。

### F-006 / medium / validated — edge_cases 缺失 status/value

- 证据：E-006（`edge_cases.csv` 第 5 行：`3,,,-`）
- 影响：空值可能导致下游空指针、类型错误或规则漏判。
- 修复建议：
  1. 定义 status、value 为必填并在入库前校验，空值进入死信队列。
  2. 统一 `notes="-"` 这类占位符规范。
- 复测方法：提交缺字段记录，确认被校验拦截并产生数据质量告警。

### F-005 / low / validated — edge_cases 重复记录

- 证据：E-005（`edge_cases.csv` 第 3、4 行，`record_id=2` 完全重复）
- 影响：重复数据导致计数/统计偏高，可能引发误告警或错误报表。
- 修复建议：以 `record_id` 为键做幂等去重；入库增加唯一约束或 upsert。
- 复测方法：重复投递同一 `record_id`，确认仅保留一条且无重复计数。

### F-007 / low / validated — edge_cases 异常负值

- 证据：E-007（`edge_cases.csv` 第 6 行：`4,error,-999,异常负值`）
- 影响：若 value 语义为非负计量值，-999 为越界输入，可能造成统计失真。
- 修复建议：
  1. 为 value 增加取值范围校验（如 >=0）。
  2. 与上游确认 -999 是否为约定错误码，若是则改用独立错误码字段。
- 复测方法：提交负值记录，确认被拦截或正确映射为错误码。

---

## 6. 攻击/调用链（Paths）

### P-001 / attack — 203.0.113.8 令牌异常到数据导出

- 证据：E-003、E-004
- 步骤：
  1. `09:04:02` service-a 自 `203.0.113.8` 触发令牌 scope 不匹配（E-003）。
  2. `09:07:30` 同一 IP 以 unknown 身份触发 critical 级 unexpected_export（E-004）。
  3. 同源 IP、短时间窗、权限异常后紧接数据导出，构成疑似令牌盗用后外传路径。
- 残余风险：缺少身份/主机/流量日志，无法确认是否真正外传成功及数据范围。

### P-002 / attack — admin 登录暴力破解尝试

- 证据：E-002
- 步骤：
  1. `09:03:45` 与 `09:03:49` 同一 IP 对 admin 连续两次登录失败（E-002）。
  2. 若持续尝试可能导致账户被攻破。
- 残余风险：仅 2 次失败，无成功登录记录，无法确认攻击或误输入。

---

## 7. 数据质量问题汇总

| 类型 | 位置 | 说明 |
|---|---|---|
| 缺失字段 | incident_log.csv:7 | severity/user/source_ip 为空 |
| 重复 | edge_cases.csv:3-4 | record_id=2 完全重复 |
| 缺失字段 | edge_cases.csv:5 | status、value 为空 |
| 异常值 | edge_cases.csv:6 | value=-999 负值 |
| 不安全输入 | edge_cases.csv:7 | `=HYPERLINK(...)` 公式注入 |
| 非标准格式 | edge_cases.csv:7 | 反斜杠转义引号，标准 csv 解析器错列 |

---

## 8. case-review 审查结果

按 SKILL.md Phase 1→4 执行，命令与结果如下：

```bash
# 非严格预检
python3 case-review-extracted/case-review/scripts/review_case.py work/security-audit --format markdown
# → status: PASS, errors=0, warnings=0

# Phase 3/4 严格模式 + 哈希校验，并保存交接结果
python3 case-review-extracted/case-review/scripts/review_case.py work/security-audit \
    --strict --verify-hashes --format markdown > work/security-audit/report/case-review.md
# → exit 0, status: PASS, errors=0, warnings=0
```

审查摘要：evidence=8、workitems=3、timeline_events=7、findings=8、paths=2；所有 Finding 均引用现存 Evidence，所有 Path 均含合法 `path_type` 与 Evidence 引用，无未链接 Evidence，两个 CSV 工件 SHA-256 校验通过。完整结果见 `work/security-audit/report/case-review.md`。

工具可用性证据：Skill 自带 8 个单元测试全部通过（`python3 -m unittest tests.test_review_case -v`，Ran 8 tests / OK）。

---

## 9. 缺失项、限制与降级方案

| 项目 | 状态 | 证据 | 影响 | 降级方案 / 复测方法 |
|---|---|---|---|---|
| `../field-journal/precedent-reverse.md` | 缺失 | `ls` 该路径返回 No such file or directory；`find` 未找到 | SKILL.md ACTION REQUIRED 第 1 步要求读取该先例文件以确认“这是对已授权既有 case 包的审查” | 以用户书面授权语“仅在授权测试范围内分析模拟安全日志”作为授权确认依据；不伪造该文件内容。复测：补齐该先例文件后重新走 Intake 确认。 |
| `../tool-index.md` | 缺失 | 同上 | SKILL.md ACTION REQUIRED 第 3 步要求读取以确认“仅用 Python 3 标准库、无需 bootstrap” | 直接验证：`python3 --version` = Python 3.13.13；脚本 import 仅含 argparse/hashlib/json/os/re/sys/datetime/pathlib，均为标准库；8 个单测通过。复测：补齐 tool-index.md 后核对。 |
| 真实目标/网络/身份日志 | 不具备 | scope 设为 offline；仅两份 CSV | F-002、F-004 只能定为 candidate/medium，无法验证攻击是否成功 | 不进行任何在线探测（遵守 MUST NOT 条款）；建议在授权环境补充身份系统、WAF、主机、NetFlow 日志后重新关联。复测：在隔离实验环境复现 P-001 时间线并验证阻断。 |
| 更长时间窗日志 | 不具备 | 仅 6 条 incident 记录 | 无法判断 admin 失败登录是否达到暴力破解阈值 | 拉长窗口统计同 IP/账户失败次数；复测：用 5 分钟窗口重跑统计。 |
| CSV 第 7 行非标准转义 | 已识别 | Python `csv` 解析该行得到 5 个字段 | 简单 `awk -F,` 对该行列定位不可靠 | E-008 的复现命令改用 `grep -n '=HYPERLINK'` 按内容匹配，避免列错位；建议上游改用标准 CSV 转义。 |

未发生因缺少依赖、权限或凭据导致的整体阻断；Python 运行时、文件读权限、脚本执行均正常。上述缺失均已按“能完成的实际完成，不能完成的给出证据与降级方案”处理。

---

## 10. 复测清单（汇总）

- [ ] F-001：注入缺字段日志，确认被拒绝/隔离并告警；24h 内 malformed_record 在阈值内。
- [ ] F-002：模拟 admin 连续失败登录，确认锁定/告警；验证白名单不误封。
- [ ] F-003：超范围令牌重放被拒并告警；新令牌最小权限。
- [ ] F-004：unknown 导出被阻断；scope 异常后同源 IP 自动隔离；导出审批与审计完整。
- [ ] F-005：重复 record_id 幂等去重，无重复计数。
- [ ] F-006：缺字段记录被校验拦截并产生数据质量告警。
- [ ] F-007：负值记录被拦截或正确映射错误码。
- [ ] F-008：公式载荷导出后不被表格执行；标准 csv 解析器读取无错列。
- [ ] 补齐 `precedent-reverse.md`、`tool-index.md` 后重新执行 Intake 确认。
- [ ] 补充身份/主机/流量日志后，将 F-002、F-004 由 candidate 升级或排除。

---

## 11. 附录

### 11.1 实际读取的 Skill 文件（相对项目目录路径）

- `case-review-extracted/case-review/SKILL.md`
- `case-review-extracted/case-review/scripts/review_case.py`
- `case-review-extracted/case-review/tests/test_review_case.py`

### 11.2 确实影响结果的 SKILL.md 规则

1. **第 21 行 “It MUST NOT perform reconnaissance, exploitation, dynamic instrumentation, or target changes.”**
   影响：本次全程离线只读，未对任何目标发起探测或利用；因此 F-002（疑似暴力破解）与 F-004（疑似数据外传）虽相关性强，也只能依据现有日志定为 `candidate`/置信度 medium，而不能通过在线验证升级为 validated。这直接决定了风险分级与“降级方案”的写法。

2. **第 70 行 “An offline observation may use `repro_command: n/a` only when its `notes` field explicitly documents the offline limitation.”**
   影响：所有 8 条 Evidence 均未使用 `n/a`，而是为每条记录提供了可在本地复现的只读命令（`awk`/`grep`），从而满足可复现性要求并通过审查。

3. **第 94 行 “A hash mismatch is a hard failure.” 与 Phase 3 fixity verification**
   影响：对两个 CSV 工件计算了 SHA-256 并写入 Evidence，使用 `--verify-hashes` 校验通过；若哈希不匹配，本次交接将直接判 FAIL。

### 11.3 case 包产物结构

```
work/security-audit/
├── scope.md
├── timeline.md
├── workitems.md
├── evidence/
│   ├── E-001.md … E-008.md
│   └── artifacts/
│       ├── incident_log.csv
│       └── edge_cases.csv
└── report/
    ├── analysis.md      # Findings & Paths
    └── case-review.md   # strict + verify-hashes 审查输出
```
