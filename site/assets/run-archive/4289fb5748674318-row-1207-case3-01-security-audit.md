# 安全审计报告 — 模拟安全日志分析

> 生成时间：2026-08-26  
> 输入文件：`incident_log.csv`、`edge_cases.csv`  
> 评测 Skill：`protocol-reverse`（分类：安全与合规）  
> 授权范围：仅在授权测试范围内分析模拟安全日志，禁止实施破坏性操作

---

## 一、执行边界与 Skill 适配性声明

### 1.1 Skill 与任务不匹配（根本性边界问题）

本次评测指定的 Skill 为 **protocol-reverse**，其 `SKILL.md` 明确定义适用场景为：

- 自定义 TCP/UDP 二进制协议逆向
- Protobuf / gRPC / FlatBuffers / MessagePack 序列化还原
- WebSocket / MQTT / 私有 RPC 帧分析
- PCAP / PCAPNG 流量还原字段与状态机

而本次业务任务为**安全日志审计**（输入为两个 CSV 文本日志文件），不涉及任何二进制协议、网络抓包或序列化格式逆向。

**依据 SKILL.md 规则**：`ACTION REQUIRED` 第 2 条要求"确认任务是否为协议/流量/序列化格式逆向"，且"不走本 skill"表格明确列出了不适用场景及应转走的方向。本次任务不属于 protocol-reverse 的适用范围。

### 1.2 SKILL.md 引用文件全部缺失

`SKILL.md` 在 `ACTION REQUIRED` 和"参考"章节引用了以下外部文件，经核实**均不存在**于解压后的 Skill 包中：

| 引用路径 | 用途 | 是否存在 |
|---|---|---|
| `../field-journal/precedent-reverse.md` | 确认授权与常规操作边界 | 否 |
| `../scripts/case-init.ps1` | 完成 scope 初始化 | 否 |
| `../tool-index.md` | 工具索引与自举 | 否 |
| `../ida-reverse/SKILL.md` | 下游客户端算法逆向 | 否 |
| `../js-reverse/SKILL.md` | 下游 JS 加密逆向 | 否 |
| `../firmware-pentest/SKILL.md` | 下游固件渗透 | 否 |
| `../pentest-tools/SKILL.md` | 下游渗透工具 | 否 |

ZIP 包内实际仅包含 **2 个文件**：

```
protocol-reverse/SKILL.md
protocol-reverse/references/protocol-workflow.md
```

### 1.3 降级方案

由于 Skill 与任务类型不匹配且引用文件缺失，无法按 protocol-reverse 的 Phase 1–4 工作流执行（该工作流要求 PCAP 样本、tshark/Wireshark、二进制帧布局还原等）。

**降级方案**：基于实际输入的两个 CSV 文件，直接执行安全日志审计——识别缺失、重复、异常、不安全输入，完成风险分级、证据提取、修复建议和复测清单。此方案不涉及任何破坏性操作，符合授权范围。

---

## 二、实际读取的 Skill 文件

| 相对路径 | 说明 |
|---|---|
| `protocol-reverse/SKILL.md` | Skill 主文件，定义工作流与适用边界 |
| `protocol-reverse/references/protocol-workflow.md` | 帧布局与 Protobuf 速查参考 |

---

## 三、incident_log.csv 分析

### 3.1 文件概况

- 格式：标准 CSV，6 个字段，6 条数据记录
- 字段：`timestamp`, `system`, `severity`, `event`, `user`, `source_ip`
- 时间范围：2026-08-12 09:00:12Z ~ 09:09:00Z（约 9 分钟窗口）

### 3.2 记录明细

| # | 时间 | 系统 | 严重度 | 事件 | 用户 | 来源IP |
|---|---|---|---|---|---|---|
| 1 | 09:00:12 | web | info | login_success | alice | 192.0.2.10 |
| 2 | 09:03:45 | web | warning | login_failed | admin | 198.51.100.23 |
| 3 | 09:03:49 | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 09:04:02 | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 5 | 09:07:30 | db | critical | unexpected_export | unknown | 203.0.113.8 |
| 6 | 09:09:00 | web | **(空)** | malformed_record | **(空)** | **(空)** |

### 3.3 数据质量问题

- **缺失字段**：记录 #6（malformed_record）缺失 `severity`、`user`、`source_ip` 三个字段，影响审计追溯完整性。
- **无完全重复记录**：6 条记录全字段比对无重复。

### 3.4 攻击链关联分析

**IP 203.0.113.8 — 疑似越权数据窃取攻击链**

| 时间 | 事件 | 严重度 | 分析 |
|---|---|---|---|
| 09:04:02 | token_scope_mismatch | high | service-a 的 token 权限范围与请求不匹配，疑似越权获取高权限 token |
| 09:07:30 | unexpected_export | critical | 同一 IP 在 3 分 28 秒后触发数据库意外导出，用户为 unknown，疑似利用越权 token 导出数据 |

**结论**：两事件来自同一 IP 且时间紧密衔接，高度疑似一次完整攻击链：越权获取 token → 利用 token 导出数据库数据。应作为最高优先级处置。

**IP 198.51.100.23 — 暴力破解尝试**

| 时间 | 事件 | 分析 |
|---|---|---|
| 09:03:45 | login_failed (admin) | 对管理员账户的登录失败 |
| 09:03:49 | login_failed (admin) | 4 秒后再次失败，疑似自动化暴力破解 |

两次失败间隔仅 4 秒，针对 admin 账户，符合暴力破解特征。虽然仅 2 次尝试未达常见阈值，但针对管理员账户应提高敏感度。

---

## 四、edge_cases.csv 分析

### 4.1 文件概况

- 格式：标准 CSV，4 个字段，6 条数据记录
- 字段：`record_id`, `status`, `value`, `notes`

### 4.2 记录明细与异常分类

| # | record_id | status | value | notes | 异常类型 |
|---|---|---|---|---|---|
| 1 | 1 | ok | 120 | 正常记录 | 无 |
| 2 | 2 | ok | 120 | 重复记录 | **重复记录** |
| 3 | 2 | ok | 120 | 重复记录 | **重复记录**（与 #2 完全相同） |
| 4 | 3 | **(空)** | **(空)** | - | **缺失字段**（status、value） |
| 5 | 4 | error | **-999** | 异常负值 | **异常负值** |
| 6 | 5 | ok | `=HYPERLINK(...)` | （引号转义错误） | **CSV 公式注入 + 列溢出** |

### 4.3 详细异常说明

**1. 重复记录（record_id=2）**
- 记录 #2 和 #3 的 record_id、status、value、notes 完全一致。
- 风险：数据去重缺失，可能导致统计偏差、计费错误或审计证据重复计数。

**2. 缺失字段（record_id=3）**
- status 和 value 均为空，notes 为占位符 `-`。
- 风险：不完整记录进入下游分析管道，可能引发空指针、除零或误判。

**3. 异常负值（record_id=4）**
- value = -999，status = error。
- 风险：若 value 为计数、金额或度量字段，负值可能触发逻辑分支错误；-999 常被用作哨兵值但未被显式处理。

**4. CSV 公式注入（record_id=5）**
- value 字段以 `=` 开头，内容为 `=HYPERLINK("https://example.invalid","do not execute")`。
- 该记录的引号未正确转义，导致 CSV 解析时出现**列溢出**（第 5 列被解析为额外字段）。
- 风险：若此 CSV 被 Excel / WPS / Google Sheets 打开，公式将被执行，可能触发恶意链接跳转或代码执行。这是一个真实的 CSV 注入漏洞。

---

## 五、风险分级汇总

| 风险等级 | 风险项 | 来源 | 证据 |
|---|---|---|---|
| **严重 (Critical)** | 越权 token 导致数据库数据导出 | incident_log #4→#5 | IP 203.0.113.8 在 3.5 分钟内从 token_scope_mismatch 升级到 unexpected_export，用户 unknown |
| **高危 (High)** | CSV 公式注入漏洞 | edge_cases #6 | value 字段含 `=HYPERLINK()`，可在电子表格软件中执行 |
| **高危 (High)** | 管理员账户暴力破解尝试 | incident_log #2→#3 | IP 198.51.100.23 针对 admin 4 秒内连续登录失败 |
| **中危 (Medium)** | 日志畸形记录（字段缺失） | incident_log #6 | severity/user/source_ip 为空，事件类型自描述为 malformed_record |
| **中危 (Medium)** | CSV 引号转义错误导致列溢出 | edge_cases #6 | 解析产生额外列，下游管道可能错位 |
| **低危 (Low)** | 重复记录 | edge_cases #2/#3 | record_id=2 完全重复 |
| **低危 (Low)** | 异常负值未处理 | edge_cases #5 | value=-999，status=error 但无哨兵值处理逻辑 |

---

## 六、修复建议

### 6.1 严重 — 越权数据导出

1. **立即封禁** IP 203.0.113.8，吊销 service-a 的所有活跃 token。
2. **核查导出范围**：审计 09:07:30 前后数据库导出操作，确认导出的数据表、行数与敏感程度。
3. **修复 token 权限校验**：API 网关应在请求时强制校验 token scope 与操作权限的匹配，scope 不匹配时直接拒绝而非降级放行。
4. **数据库导出管控**：对 unexpected_export 类操作实施二次审批 / 速率限制 / 数据脱敏。
5. **关联告警**：建立"token_scope_mismatch + 同 IP 敏感操作"的关联告警规则。

### 6.2 高危 — CSV 公式注入

1. **输入清洗**：在写入 CSV 前，对以 `=`、`+`、`-`、`@` 开头的单元格值前置单引号 `'` 或转义。
2. **输出安全**：CSV 导出工具应默认对公式元字符进行中和处理。
3. **用户教育**：提醒使用者不要直接打开来源不明的 CSV 文件。
4. **修复引号转义**：确保 CSV 生成时对含逗号/引号的字段使用标准双引号包裹和内部引号转义（`""`）。

### 6.3 高危 — 暴力破解

1. **账户锁定**：admin 账户登录失败 N 次后临时锁定（如 5 次 / 15 分钟）。
2. **IP 限流**：对同一 IP 的登录请求实施速率限制（如 10 次 / 分钟）。
3. **MFA 强制**：管理员账户必须启用多因素认证。
4. **告警升级**：针对管理员账户的登录失败应降低告警阈值（如 2 次即触发告警）。

### 6.4 中低危 — 数据质量

1. **日志采集校验**：在日志入库前增加 schema 校验，缺失必填字段的记录应进入隔离队列而非主日志流。
2. **去重机制**：基于 record_id 或内容哈希在入库时去重。
3. **哨兵值处理**：对 -999 等哨兵值建立显式处理逻辑，不参与正常统计。
4. **空值处理**：下游分析管道对空值字段做防御性编程。

---

## 七、复测清单

| # | 复测项 | 方法 | 通过标准 |
|---|---|---|---|
| 1 | token scope 校验 | 构造 scope 不匹配的 API 请求 | 请求被拒绝，返回 403，不产生后续操作 |
| 2 | 数据库导出授权 | 用低权限 token 尝试导出 | 操作被拒绝，触发告警 |
| 3 | 关联告警规则 | 模拟同 IP token 异常 + 导出操作 | 5 分钟内产生关联告警 |
| 4 | CSV 公式注入防护 | 生成含 `=HYPERLINK()` 的 CSV 并用 Excel 打开 | 公式不被执行，显示为文本 |
| 5 | CSV 引号转义 | 生成含逗号和引号的字段并解析 | 列数正确，无溢出 |
| 6 | 暴力破解防护 | 对 admin 连续发送失败登录 | 达到阈值后账户锁定 / IP 限流 |
| 7 | 日志 schema 校验 | 发送缺失字段的日志记录 | 记录进入隔离队列，不污染主日志 |
| 8 | 重复记录去重 | 写入两条完全相同的记录 | 仅保留一条，或标记重复 |
| 9 | 异常负值处理 | 输入 value=-999 的记录 | 哨兵值被识别，不参与正常统计 |

---

## 八、影响结果的 SKILL.md 规则

以下规则确实影响了本次执行的路径与结论：

> **SKILL.md `ACTION REQUIRED` 第 2 条**："确认任务是否为协议/流量/序列化格式逆向（非纯 Web 参数签名 → 转 `js-reverse/`）"

该规则要求在执行前确认任务类型。经确认，本次任务为安全日志审计而非协议逆向，因此**不进入 protocol-reverse 的 Phase 1–4 工作流**（该工作流要求 PCAP 样本、tshark 解析、帧布局还原等），转而采用基于 CSV 内容的直接日志分析作为降级方案。若忽略此规则强行套用协议逆向工作流，将因缺少 PCAP/二进制样本而无法产出任何有效结果。

此外，**SKILL.md "不走本 skill" 表格**也支持了上述判断——该表格明确列出了不适用场景，安全日志审计不在适用范围内。

---

## 九、阻断与未完成项说明

| 项目 | 状态 | 原因 |
|---|---|---|
| protocol-reverse Phase 1–4 协议逆向工作流 | **未执行** | 任务类型不匹配（无 PCAP / 二进制样本），且 SKILL.md 引用的授权确认文件、初始化脚本、工具索引均缺失 |
| `case-init.ps1` scope 初始化 | **未执行** | 文件不存在于 Skill 包中 |
| `precedent-reverse.md` 授权边界确认 | **未执行** | 文件不存在于 Skill 包中 |
| 安全日志审计（降级方案） | **已完成** | 基于实际输入 CSV 完成分析 |

本次未发起任何浏览器接管、登录授权、交互式选择或持续运行的服务进程。所有分析均为静态文本处理，未实施破坏性操作。
