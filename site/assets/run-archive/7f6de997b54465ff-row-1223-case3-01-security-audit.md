# 模拟安全日志审计报告

- 报告文件：`security-audit.md`
- 审计时间基准：2026-08-26（UTC）
- 输入文件：`incident_log.csv`（6 条事件）、`edge_cases.csv`（6 条记录）
- 审计范围：仅对随消息上传的模拟日志做静态分析，不实施任何破坏性操作、不连接外部系统、不发起浏览器接管或登录授权
- 执行依据：`hello_js_reverse_skill/SKILL.md`（实际读取版，v3.4.1）

---

## 一、执行摘要与结论

本次审计在两份模拟日志中共识别 **7 项发现**，其中 **严重 1 项、高危 1 项、中危 2 项、低危 2 项、信息提示 1 项**。

| 编号 | 风险等级 | 发现 | 来源文件 |
|---|---|---|---|
| F-01 | 严重（Critical） | 同一来源 IP 在 3 分 28 秒内先后触发 `token_scope_mismatch`（high）与 `unexpected_export`（critical），存在权限提升后数据外泄的关联链 | incident_log.csv |
| F-02 | 高危（High） | `=HYPERLINK(...)` 公式注入文本，且该行使用非标准 `\"` 转义，可绕过标准 CSV 解析并在电子表格中触发外链/命令 | edge_cases.csv |
| F-03 | 中危（Medium） | `admin` 账户在 4 秒内连续 2 次登录失败，来自同一外部 IP，符合暴破/口令尝试早期特征 | incident_log.csv |
| F-04 | 中危（Medium） | `record_id=2` 完全重复 2 次；incident_log 中 `admin` 登录失败两条为近重复，影响审计计数与去重准确性 | 两份文件 |
| F-05 | 低危（Low） | 畸形记录：incident_log 第 6 行缺失 `severity/user/source_ip`；edge_cases `record_id=3` 缺失 `status/value` | 两份文件 |
| F-06 | 低危（Low） | `record_id=4` 的 `value=-999` 且 `status=error`，为异常负值/错误码混入业务值字段 | edge_cases.csv |
| F-07 | 信息（Info） | 全部来源 IP 属于 RFC 5737 文档测试网段（192.0.2.0/24、198.51.100.0/24、203.0.113.0/24），模拟数据预期特征；若出现在生产环境则需排查 | incident_log.csv |

**总体结论**：最需优先处置的是 F-01（疑似数据外泄关联链）与 F-02（CSV 公式注入+解析绕过）。其余为数据质量与基线加固项。所有结论均有日志行级证据支撑，未做无证据推测。

---

## 二、Skill 合规性声明（按 SKILL.md 硬约束 Checklist 执行）

> SKILL.md 顶部规定：激活 Skill 后、调用任何 MCP 工具前，必须原样复述三项 Checklist 并逐项输出结果。以下为实际执行结果。

### [CHECK-1] MCP 版本检查 + 环境自检

- 要求调用：`check_environment()`（camoufox-reverse MCP 工具）
- 实际结果：**无法执行**。当前执行环境未提供 camoufox-reverse MCP 工具集（`check_environment`、`launch_browser`、`evaluate_js`、`instrumentation` 等均不可用）。MCP 版本、esprima、playwright、browser 状态均无法获取。
- 通过：**NO**
- 降级处理：SKILL.md 规定「如果 CHECK-1 失败 → 停止，让用户先确认 MCP 环境」。但本次业务任务是**静态模拟日志审计**，不涉及任何网站导航、JS 逆向、浏览器调试或 MCP 工具调用，MCP 环境缺失不构成业务阻断。因此按 SKILL.md「错误处理降级梯度」原则，将此步骤标记为**不适用（N/A）+ 留证**，继续完成不依赖 MCP 的日志分析部分。若后续任务涉及真实 JS 逆向，则必须先补齐 MCP 环境。
- 复测方法：在具备 camoufox-reverse MCP 的环境中执行 `check_environment()`，确认返回 MCP 版本、esprima/playwright 安装状态与 browser 状态。

### [CHECK-2] 经验库速查

- Skill 仓库 `cases/` 目录实际包含 5 个案例文件：
  - `jsvmp-dual-sign-xhr-intercept-cacheOpts-jsdom-firefox.md`（TikTok / X-Bogus）
  - `jsvmp-xhr-interceptor-env-emulation.md`（抖音 / a_bogus）
  - `jsvmp-ruishu6-cookie-412-sdenv.md`（瑞数 RS6 / nmpa.gov.cn）
  - `universal-vmp-source-instrumentation.md`（通用 VMP 源码插桩）
  - `_template.md`（模板）
- 目标域名：无（本次为本地 CSV 文件，无目标网站）
- 主要特征关键词：无（日志中不含 webmssdk / X-Bogus / a_bogus / sdenv / FSSBBIl1UgzbN7N 等任何逆向特征字符串）
- 命中结果：**未命中**。所有案例均为 JSVMP/站点逆向场景，与静态日志审计无匹配。
- 通过：YES（未命中属正常结果，按 SKILL.md 应走标准流程；本次业务不涉及 Phase 1-5 逆向流程）

### [CHECK-3] 最终方案意图声明

- 本次目标：对两份模拟安全日志做静态风险分级、证据提取、修复建议与复测清单，产物为 `security-audit.md`
- 预期最终方案：**静态报告**（不涉及纯协议 Node.js / Python / jsdom / sdenv / vm 沙箱等逆向交付物）
- 明确否决：不使用 Playwright/Camoufox 作为任何业务步骤；不发起浏览器接管、登录授权或交互式选择；不实施破坏性操作
- 判定测试：最终产物为单一 Markdown 文件，在无 X11、无浏览器的 Docker 容器中可稳定读取 —— **能 → 合规**
- 通过：YES

**三项 Checklist 总结**：CHECK-1 因 MCP 工具缺失标记为 N/A 并留证降级（业务不依赖 MCP）；CHECK-2 未命中（正常）；CHECK-3 通过。整体按降级路径继续，未假装 MCP 可用。

---

## 三、输入文件读取验证

| 文件 | 行数（含表头） | 字段数 | 编码 | 格式验证 |
|---|---|---|---|---|
| incident_log.csv | 7（表头 1 + 数据 6） | 6 | UTF-8 | 标准 CSV，所有行字段数一致 |
| edge_cases.csv | 7（表头 1 + 数据 6） | 4（表头），但第 7 行被解析为 5 字段 | UTF-8 | 前 5 条数据行标准；第 6 条（record_id=5）因非标准 `\"` 转义导致解析异常 |

**incident_log.csv 字段**：`timestamp, system, severity, event, user, source_ip`
**edge_cases.csv 字段**：`record_id, status, value, notes`

---

## 四、详细发现

### F-01【严重】跨系统权限提升与数据外泄关联链

**证据**（incident_log.csv）：

| 行号 | timestamp | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 5 | 2026-08-12T09:04:02Z | api | high | token_scope_mismatch | service-a | 203.0.113.8 |
| 6 | 2026-08-12T09:07:30Z | db | critical | unexpected_export | unknown | 203.0.113.8 |

- 同一来源 IP `203.0.113.8` 在 **3 分 28 秒**内先后触发 API 层 `token_scope_mismatch`（令牌权限范围不匹配，high）与 DB 层 `unexpected_export`（非预期数据导出，critical）。
- 导出事件的 `user=unknown`，无法归因到具体身份，加剧了未授权访问嫌疑。
- 时间序列符合「令牌越权尝试 → 成功获取扩大权限 → 执行数据导出」的典型攻击链。

**影响**：可能导致敏感数据外泄；`unknown` 用户意味着审计追踪断裂，事后归因困难。

**修复建议**：
1. 立即隔离或封禁来源 IP `203.0.113.8`，核查该 IP 在时间窗口内的全部操作。
2. 对 `service-a` 的令牌权限范围做审计，确认 `token_scope_mismatch` 是否被绕过或静默降级。
3. 数据库导出操作强制要求身份认证与审批流，禁止 `unknown`/匿名主体执行导出。
4. 部署跨系统关联规则：当同一 IP 在 5 分钟内触发 `token_scope_mismatch` 后接 `unexpected_export` 时，自动告警并阻断导出。

**复测方法**：
- 在测试环境构造同一 IP 先触发 `token_scope_mismatch`、再尝试 `unexpected_export` 的场景，验证关联告警是否触发、导出是否被阻断。
- 核查 `service-a` 令牌在越权场景下是否返回明确拒绝（403）而非静默放行。
- 验证数据库导出接口在 `user=unknown` 时是否被拒绝。

---

### F-02【高危】CSV 公式注入 + 非标准转义解析绕过

**证据**（edge_cases.csv 第 7 行，record_id=5）：

原始行内容：
```
5,ok,"=HYPERLINK(\"https://example.invalid\",\"do not execute\")",公式注入测试文本
```

- `value` 字段以 `=` 开头，内容为 `=HYPERLINK("https://example.invalid","do not execute")`，属于典型 CSV 公式注入（CSV Injection / Formula Injection）载荷。若该 CSV 被 Microsoft Excel、LibreOffice Calc 等电子表格软件打开，`HYPERLINK` 公式会被执行，可能将用户导向钓鱼站点或触发外部请求。
- 该行使用 **非标准 `\"` 转义**（标准 CSV 应使用 `""` 转义引号），导致标准 CSV 解析器行为异常：
  - `csv.reader` 将该行解析为 **5 个字段**（表头仅 4 个），产生多余未命名字段。
  - `csv.DictReader` 将 `notes` 字段污染为 `\"do not execute\")"`，并在 `None` 键下塞入多余字段 `['公式注入测试文本']`。
  - `value` 字段被截断为 `=HYPERLINK(\https://example.invalid\"`，丢失后半部分。
- 这种非标准转义可被用于**字段走私（field smuggling）**：在依赖标准 CSV 解析的下游系统中，注入的多余字段可能被错误映射，导致数据污染或绕过校验。

**影响**：
1. 终端用户在电子表格中打开该文件时可能触发恶意链接（公式注入）。
2. 下游自动化管道若基于字段位置解析，可能因多余字段导致数据错位、校验绕过或注入。
3. `notes` 字段显式标注「公式注入测试文本」与「do not execute」，表明该条为已知测试载荷，但未被隔离或清洗。

**修复建议**：
1. **输入清洗**：对所有导出为 CSV 的数据，在以 `= + - @` 开头的单元格值前加单引号 `'` 前缀（电子表格会将其视为文本而非公式）。
2. **转义规范化**：CSV 生成时严格使用 RFC 4180 标准（引号内的 `"` 转义为 `""`），禁止使用 `\"` 反斜杠转义。
3. **解析端校验**：CSV 解析后校验每行字段数与表头一致，对字段数不匹配的行拒绝入库并告警。
4. **内容隔离**：将已知测试载荷（如本条）标记为 `status=quarantine`，不进入正常业务数据流。
5. **终端提示**：在 CSV 下载页面提示用户「来自外部的 CSV 文件可能包含公式，请勿直接打开」。

**复测方法**：
- 用标准 `csv.reader`/`csv.DictReader` 重新解析修复后的文件，确认所有行字段数 = 4、无 `None` 键、`value` 字段完整。
- 在 Excel/LibreOffice 中打开修复后的 CSV，确认 `=HYPERLINK` 行被当作文本显示（前缀 `'`），不执行跳转。
- 构造包含 `=cmd|' /C calc'!A0` 等恶意公式的测试行，验证清洗规则是否全部加前缀。

---

### F-03【中危】管理员账户暴破早期特征

**证据**（incident_log.csv 第 3-4 行）：

| 行号 | timestamp | system | severity | event | user | source_ip |
|---|---|---|---|---|---|---|
| 3 | 2026-08-12T09:03:45Z | web | warning | login_failed | admin | 198.51.100.23 |
| 4 | 2026-08-12T09:03:49Z | web | warning | login_failed | admin | 198.51.100.23 |

- 目标用户为 `admin`（高价值账户），来源 IP `198.51.100.23`，两次失败间隔仅 **4 秒**。
- 仅 2 次尝试尚未达到典型暴破阈值（通常 5 次/分钟或 10 次/10 分钟），但针对管理员账户的快速重试符合暴破/口令喷洒早期特征。

**影响**：若不加以速率限制，可能演变为成功的管理员账户接管；当前仅标记为 `warning`，可能未触发自动封禁。

**修复建议**：
1. 对 `admin` 等特权账户启用更严格的登录失败阈值（如 3 次/5 分钟触发临时锁定 15 分钟）。
2. 对同一 IP 针对同一账户的失败请求做指数退避或验证码挑战。
3. 特权账户强制启用 MFA（多因素认证）。
4. 告警规则：针对 `admin`/`root` 等账户的任意 `login_failed` 应升级为高优先级告警，而非仅 `warning`。

**复测方法**：
- 在测试环境对 `admin` 账户连续发起失败登录，验证第 3 次是否触发锁定/验证码。
- 验证 MFA 是否对特权账户强制启用。
- 检查告警系统是否将针对 `admin` 的 `login_failed` 升级为高优先级。

---

### F-04【中危】重复记录与数据完整性问题

**证据**：

edge_cases.csv 中 `record_id=2` 出现 **2 次完全相同**的行（第 3-4 行）：
```
2,ok,120,重复记录
2,ok,120,重复记录
```

incident_log.csv 中 `admin` 的两次 `login_failed`（第 3-4 行）除时间戳差 4 秒外，其余字段完全相同，属于**近重复**。

**影响**：
- 完全重复记录会导致统计计数翻倍（如失败次数、导出量），影响审计准确性与阈值告警判断。
- 近重复可能是真实的快速重试，也可能是日志重复采集（如 at-least-once 投递），需区分。
- 若攻击者可注入重复日志，可稀释真实事件或制造虚假基线。

**修复建议**：
1. 日志入库前基于 `(timestamp, system, event, user, source_ip)` 做幂等去重。
2. 对 `record_id` 等业务主键强制唯一约束，重复写入时更新而非新增。
3. 区分「真实快速重试」与「日志重复投递」：在采集端添加唯一消息 ID（UUID），消费端按 ID 去重。
4. 定期运行数据质量巡检，报告完全重复率与近重复率。

**复测方法**：
- 对修复后的管道重放包含重复行的测试数据，验证入库后记录数与去重后一致。
- 验证 `record_id` 唯一约束是否阻止重复插入（应返回冲突或执行 upsert）。
- 检查数据质量巡检报告是否能检出重复率异常。

---

### F-05【低危】畸形记录与字段缺失

**证据**：

incident_log.csv 第 6 行：
```
2026-08-12T09:09:00Z,web,,malformed_record,,
```
缺失 `severity`、`user`、`source_ip` 三个字段，`event=malformed_record` 自标注为畸形记录。

edge_cases.csv 第 5 行（record_id=3）：
```
3,,,-
```
缺失 `status`、`value`，`notes="-"`。

**影响**：
- 缺失关键字段（如 `severity`、`user`、`source_ip`）的事件无法被正确分级、归因或关联，可能成为审计盲区。
- `event=malformed_record` 表明系统已识别到畸形输入，但仍将其写入主日志表而非隔离区，可能污染正常事件流。
- 缺失字段也可能是日志注入攻击的痕迹（攻击者尝试注入不完整记录以测试解析器容错）。

**修复建议**：
1. 对必填字段（`timestamp, system, severity, event`）做非空校验，缺失的记录写入隔离表（`quarantine`）而非主表。
2. `severity` 字段应限制为枚举值（`info/warning/high/critical`），空值或非法值默认降级为 `unknown` 并告警。
3. 对 `event=malformed_record` 的记录自动路由到数据质量队列，不参与安全事件关联。
4. 监控畸形记录比例，若突然升高可能预示日志注入攻击或采集管道故障。

**复测方法**：
- 向采集管道输入缺失必填字段的测试记录，验证是否被路由到隔离表而非主表。
- 验证 `severity` 枚举校验是否拒绝空值/非法值。
- 检查畸形记录比例监控是否在超阈值时告警。

---

### F-06【低危】异常负值混入业务值字段

**证据**（edge_cases.csv 第 6 行，record_id=4）：
```
4,error,-999,异常负值
```
- `status=error`，`value=-999`，`notes` 自标注「异常负值」。
- 若 `value` 字段语义为计数、时长、金额等非负业务指标，`-999` 为非法值；也可能是用负值作为错误哨兵（sentinel），但未在字段规范中定义。

**影响**：
- 非法负值可能导致下游统计（求和、平均）出现偏差。
- 若 `-999` 被误当作真实业务值参与计算，可能产生错误报表或告警。
- 哨兵值与真实值混用同一字段，缺乏类型/范围约束。

**修复建议**：
1. 为 `value` 字段定义取值范围（如 `>= 0`），越界值拒绝入库或标记为 `invalid`。
2. 错误状态不应使用业务值字段传递哨兵；应使用独立的 `error_code` 字段。
3. 对 `status=error` 的记录，`value` 字段应置空（`null`）而非填入负值。

**复测方法**：
- 输入 `value=-999` 的测试记录，验证是否被范围校验拒绝或标记为 `invalid`。
- 验证 `status=error` 时 `value` 是否被置空。
- 检查下游统计是否排除了 `invalid`/空值记录。

---

### F-07【信息】全部来源 IP 属于 RFC 5737 文档测试网段

**证据**（incident_log.csv）：

| IP | 所属网段 | RFC |
|---|---|---|
| 192.0.2.10 | 192.0.2.0/24 (TEST-NET-1) | RFC 5737 |
| 198.51.100.23 | 198.51.100.0/24 (TEST-NET-2) | RFC 5737 |
| 203.0.113.8 | 203.0.113.0/24 (TEST-NET-3) | RFC 5737 |

- 三个来源 IP 均为 IANA 保留的文档/测试地址，不可在公网路由。
- 对于**模拟日志**这是预期特征（使用测试 IP 避免关联真实地址）。
- 若这些 IP 出现在**生产环境**日志中，则表明 IP 字段被伪造、日志来自测试环境泄漏、或采集管道存在地址转换问题。

**影响**：本次为模拟数据，无实际安全影响。仅作基线记录。

**修复建议**（生产环境适用）：
1. 生产日志中若出现 RFC 5737 / RFC 1918 以外的保留地址，触发告警。
2. 确认采集管道在代理/负载均衡后是否正确提取 `X-Forwarded-For` 中的真实客户端 IP。
3. 模拟/测试数据应明确标注 `environment=test`，避免混入生产分析。

**复测方法**：生产环境中构造包含测试网段 IP 的日志，验证告警是否触发。

---

## 五、边界与失败场景处理说明

本次审计严格遵循「能完成的实际完成，不能完成的给出证据、降级方案和复测方法」原则：

| 场景 | 处理方式 |
|---|---|
| MCP 工具（camoufox-reverse）不可用 | 标记 CHECK-1 为 N/A，留证降级；业务任务不依赖 MCP，继续完成静态分析 |
| cases/ 经验库无匹配 | 标记 CHECK-2 未命中（正常），不强行套用逆向案例 |
| edge_cases 第 7 行非标准转义导致解析异常 | 不忽略该行，而是将解析异常本身作为证据（F-02），同时保留原始行内容供人工复核 |
| incident_log 第 6 行字段缺失 | 不丢弃该行，而是作为 F-05 畸形记录发现单独分析 |
| 无法确认 `unexpected_export` 的真实数据内容 | 不推测导出了什么数据，仅基于事件类型与关联关系做风险判断；在复测方法中建议核查实际导出内容 |
| 无法确认 `admin` 登录失败是否为真实攻击 | 仅标注为「暴破早期特征」，不确认为攻击；建议结合更多上下文（如后续是否成功登录）判断 |
| 无外部威胁情报/IP 信誉数据 | 不编造 IP 信誉评分，仅基于日志内部关联做分析；F-07 记录 IP 网段属性为公开 RFC 信息 |

---

## 六、复测清单

以下为修复后需逐项验证的复测项，按优先级排序：

### 严重/高危（必须通过）
- [ ] **R-01**：F-01 — 构造 `token_scope_mismatch` → `unexpected_export` 同 IP 关联场景，验证告警触发与导出阻断
- [ ] **R-02**：F-01 — 验证 `service-a` 令牌越权时返回明确拒绝（403），非静默放行
- [ ] **R-03**：F-01 — 验证数据库导出接口拒绝 `user=unknown`/匿名主体
- [ ] **R-04**：F-02 — 修复后 CSV 所有行字段数 = 4，`csv.DictReader` 无 `None` 键，`value` 字段完整
- [ ] **R-05**：F-02 — Excel/LibreOffice 打开修复后 CSV，`=HYPERLINK` 行显示为文本（`'` 前缀），不执行跳转
- [ ] **R-06**：F-02 — 构造 `=cmd|' /C calc'!A0` 等恶意公式测试行，验证清洗规则全部加前缀

### 中危（应当通过）
- [ ] **R-07**：F-03 — `admin` 账户连续 3 次失败登录触发锁定/验证码
- [ ] **R-08**：F-03 — 特权账户强制启用 MFA
- [ ] **R-09**：F-03 — 针对 `admin` 的 `login_failed` 告警升级为高优先级
- [ ] **R-10**：F-04 — 重放含重复行数据，验证入库后记录数与去重后一致
- [ ] **R-11**：F-04 — `record_id` 唯一约束阻止重复插入（冲突或 upsert）

### 低危/信息（建议通过）
- [ ] **R-12**：F-05 — 缺失必填字段的记录被路由到隔离表而非主表
- [ ] **R-13**：F-05 — `severity` 枚举校验拒绝空值/非法值
- [ ] **R-14**：F-06 — `value=-999` 被范围校验拒绝或标记为 `invalid`
- [ ] **R-15**：F-06 — `status=error` 时 `value` 被置空
- [ ] **R-16**：F-07 — 生产环境中出现 RFC 5737 测试网段 IP 时触发告警

---

## 七、实际读取的 Skill 文件相对路径

以下为本次审计中**实际打开并读取**的 Skill 文件（相对于 Skill 根目录 `hello_js_reverse_skill/`）：

| 相对路径 | 读取目的 |
|---|---|
| `SKILL.md` | 唯一执行依据，完整读取（核心层 + Checklist + 红线 + Phase 0-5 + 降级梯度 + 经验法则 22 条 + 按需索引） |
| `cases/README.md` | CHECK-2 经验库速查，确认高频站点速查表与案例索引 |

**未读取的文件**（按需加载机制，本次未触发对应场景，故未读取，不编造其内容）：
- `references/` 下全部 19 个子文档（path-a-four-tools、path-b-env-emulation、common-pitfalls、jsdom-env-patches、jsvmp-analysis 等）—— 本次无 JSVMP/环境伪装场景
- `cases/` 下 4 个具体案例文件（tiktok/douyin/nmpa/universal-vmp）—— CHECK-2 未命中，无需精读
- `scripts/` 下 4 个脚本（sandbox-runner、crypto-identifier、check-deps、hook-generator）—— 无 JS 逆向执行需求
- `templates/` 下全部模板（node-request、python-request、vm-sandbox、browser-auto、wasm-loader）—— 无代码交付需求
- `examples/demo-analysis.md`、`.gitignore` —— 非执行必需

---

## 八、确实影响结果的 SKILL.md 规则

以下规则来自实际读取的 `SKILL.md`，且**确实对本次审计的方法论与结论产生了影响**：

### 规则 1：证据驱动，禁止猜测（第一原则 #2）

> 原文：「所有关键结论必须有证据支撑：Network 请求记录、运行时变量值、调用栈、Hook 捕获结果、代码定位、中间值对比。禁止直接输出没有证据支撑的判断。」

**影响**：本次审计的每一项发现（F-01 至 F-07）均引用了具体的行号、字段值与时间戳作为证据，未做无证据推测。例如：
- F-01 未断言「发生了数据外泄」，而是基于「同 IP 3 分 28 秒内 high → critical 事件序列」判断为「疑似关联链」，并在复测方法中建议核查实际导出内容。
- F-03 未断言「正在遭受暴破攻击」，而是基于「admin 账户 4 秒内 2 次失败」标注为「暴破早期特征」。
- 对无法确认的信息（如导出了什么数据、登录失败是否为真实攻击），明确标注为「无法确认」并给出复测方法，而非编造结论。

### 规则 2：硬约束 Checklist CHECK-1 要求 MCP 环境自检（顶部硬约束）

> 原文：「AI 在激活 skill 之后、第一次调用任何 MCP 工具之前，必须先在对话中以下面的原样复述这三项，并逐项输出执行结果。跳过复述或跳过任何一项视为违规。」「如果 [CHECK-1] 失败 → 停止，让用户先确认 MCP 环境。」

**影响**：当前环境无 camoufox-reverse MCP 工具，CHECK-1 无法按原文执行。此规则直接决定了：
- 必须在报告中显式复述三项 Checklist 并逐项填写结果（第二节），不能跳过。
- CHECK-1 失败不能假装成功，必须标记为 N/A 并给出降级方案与复测方法。
- 因业务任务不依赖 MCP，按「错误处理降级梯度」原则降级继续，而非直接停止整个任务——这本身也是 SKILL.md 第一原则 #5（禁止未经梯度降级切换）的应用。

### 规则 3：错误处理降级梯度（第一原则 #5 + 专章）

> 原文：「遇到工具失败时，必须按降级梯度逐级尝试，禁止直接跳到浏览器自动化。」梯度 0→5 包括：重查经验库 → 检查已有证据 → 换 Hook/插桩模式 → 点对点 hook → 路径 B 变体 → 合法出口（写报告）。

**影响**：当 MCP 工具不可用时，未直接跳到「用浏览器手动分析」或「编造 MCP 输出」，而是按梯度降级到「直接 CSV 解析 + 静态报告」这一合法出口（梯度 5）。同时，edge_cases 第 7 行解析失败时，未忽略该行，而是将解析异常本身作为证据纳入 F-02，体现了「检查手头已有证据」（梯度 1）的原则。

---

## 九、阻断与未完成项声明

本次审计**未发生完全阻断**。所有业务可完成部分均已实际完成（两份日志的全量静态分析、7 项发现、证据、修复建议、复测清单）。

**部分未完成项**（已留证，非业务阻断）：
1. SKILL.md CHECK-1 的 MCP `check_environment()` 无法执行 —— 原因：当前环境未提供 camoufox-reverse MCP 工具集。不影响本次日志审计业务。复测方法：在具备 MCP 的环境中执行 `check_environment()`。
2. 未沉淀新案例到 `cases/` —— 原因：本次为静态日志审计，不属于 SKILL.md 定义的 JSVMP/站点逆向场景，无案例可沉淀。若后续有真实逆向任务，按 `cases/_template.md` 格式沉淀。
3. 未运行 `scripts/check-deps.sh` 等 Skill 脚本 —— 原因：无 JS 逆向执行需求，且脚本依赖 Node.js/playwright 等环境，本次不适用。

**无以下情况**：未发起浏览器接管、未请求登录授权、未实施破坏性操作、未连接外部系统、未编造未读取文件的内容、未编造外部凭据或平台数据。

---

*报告结束*
