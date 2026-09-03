# aims-audit Skill 安全审计报告

**审计对象**：aims-audit Skill（compliance-os Claude Code 插件 v2.9.0 的组成部分）
**审计日期**：2026-08-12
**审计环境**：macOS，Python 3.9.6（系统）/ 3.13.13（沙箱），无第三方依赖
**审计方法**：静态代码审查 + 黑盒输入测试 + 路径解析验证 + 依赖分析

---

## 一、审计范围

| 组件 | 路径（相对插件根目录） | 说明 |
|------|------------------------|------|
| aims-audit Skill | `skills/aims-audit/SKILL.md` | 本次评测目标，六问审查工具 |
| compliance-os 主 Skill | `skills/compliance-os/SKILL.md` | 元编排器，aims-audit 依赖其脚本 |
| 插件清单 | `.claude-plugin/plugin.json` | 插件元数据与 Skill 列表 |
| Agent 定义 | `agents/cs-aims-iso42001.md` | aims-audit 关联的智能体 |
| 插件内脚本（4个） | `skills/compliance-os/scripts/*.py` | framework_selector / cross_framework_mapper / audit_simulator / evidence_pool_generator |
| 外部脚本（3个） | `ra-qm-team/skills/iso42001-specialist/scripts/*.py` | aims_gap_analyzer / ai_risk_register_builder / aims_audit_scheduler |

**说明**：上传的 `aims-audit.zip` 仅含 `SKILL.md`（5258 字节），不含任何被引用的脚本或知识库文件。审计在系统上找到的完整 `compliance-os` 插件副本上进行，ZIP 中的 SKILL.md 与完整项目中的版本经比对完全一致。

---

## 二、约束导致的方案变化

| 约束 | 对审计方案的影响 |
|------|------------------|
| 不新增非必要依赖 | 未安装任何第三方包；静态分析仅用 `grep`/`find`，动态测试仅用系统 Python3 标准库 |
| 不改动无关文件 | 所有测试输入文件写入 `/tmp/`，未修改项目中任何文件；审计全程只读 |
| 可重复的验证命令 | 每个发现均附带可直接复制执行的命令和预期结果（见下文各节"复测方法"） |
| 外部账号依赖 | 本项目所有脚本均为本地离线运行，无网络调用、无外部账号，无需模拟 |

---

## 三、安全发现

### 发现 1：未捕获的类型转换异常导致拒绝服务（中危）

**位置**：
- `ra-qm-team/skills/iso42001-specialist/scripts/ai_risk_register_builder.py` 第 138-139 行
- `ra-qm-team/skills/iso42001-specialist/scripts/aims_audit_scheduler.py` 第 112 行

**证据**：

`ai_risk_register_builder.py` 第 138-139 行直接对用户输入调用 `int()`，未包裹 try/except：
```python
likelihood = int(risk.get("likelihood", 0))
impact = int(risk.get("impact", 0))
```

`aims_audit_scheduler.py` 第 112 行同理：
```python
year = int(payload.get("audit_year", 2026))
```

当输入为非数字字符串或 `null` 时，脚本抛出未捕获异常并输出完整 Python traceback：

```
$ echo '{"risks":[{"id":"R1","likelihood":"abc","impact":3}]}' > /tmp/t.json
$ python3 ai_risk_register_builder.py /tmp/t.json
  ...
  File ".../ai_risk_register_builder.py", line 138, in annotate_risk
    likelihood = int(risk.get("likelihood", 0))
ValueError: invalid literal for int() with base 10: 'abc'
```

`null` 值导致 `TypeError`：
```
$ echo '{"risks":[{"id":"R1","likelihood":true,"impact":null}]}' > /tmp/t.json
TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType'
```

**影响**：
- 在智能体自动化工作流中，单个格式错误的输入会中断整个审计流程
- traceback 向 stderr 输出服务器内部文件绝对路径，属于信息泄露
- 无输入校验意味着攻击者可通过构造畸形 JSON 持续触发崩溃

**修复建议**：
在 `int()` 调用处增加类型检查与友好错误处理，或在 `main()` 中统一捕获 `ValueError`/`TypeError` 并输出非 traceback 的错误信息后以退出码 1 返回。

**复测方法**：
```bash
# 修复前：应输出 traceback 并以非零退出码退出
echo '{"risks":[{"id":"R1","likelihood":"abc","impact":3}]}' > /tmp/t.json
python3 ai_risk_register_builder.py /tmp/t.json; echo "退出码: $?"

# 修复后：应输出 "error: likelihood must be an integer 1-5" 类提示，退出码 1，无 traceback
```

---

### 发现 2：输入类型混淆导致静默错误结果（中危）

**位置**：
- `skills/compliance-os/scripts/cross_framework_mapper.py`（`set()` 迭代字符串）
- `skills/compliance-os/scripts/audit_simulator.py`（列表迭代字符串）

**证据**：

当 JSON 中 `enabled_frameworks` 传入字符串而非数组时，Python 的 `set()` 会逐字符迭代：

```
$ echo '{"enabled_frameworks": "iso_27001"}' > /tmp/t.json
$ python3 cross_framework_mapper.py /tmp/t.json
...
Enabled frameworks (8): 0, 1, 2, 7, _, i, o, s
Merged controls in scope: 0
```

`audit_simulator.py` 同理，`scope_controls` 传字符串 `"A.5.15"` 被逐字符拆分为 `A, ., 5, ., 1, 5`，产生 0 个审计发现但无任何错误提示。

**影响**：
- 脚本不报错但输出完全错误的结果，可能误导合规决策
- 在智能体场景中，上游 LLM 可能因误解 schema 而传入字符串，下游静默接受，错误难以发现
- 这是所有 7 个脚本的共性问题：均无输入 schema 验证，仅用 `.get(key, default)` 提供默认值

**修复建议**：
在 `analyze()`/`plan()` 等核心函数入口增加类型断言或 schema 校验，例如：
```python
frameworks = payload.get("enabled_frameworks", [])
if not isinstance(frameworks, list):
    raise ValueError("enabled_frameworks must be a list")
```

**复测方法**：
```bash
echo '{"enabled_frameworks": "iso_27001"}' > /tmp/t.json
python3 cross_framework_mapper.py /tmp/t.json
# 修复前：输出 "Enabled frameworks (8): 0, 1, 2, 7, _, i, o, s"
# 修复后：应输出明确错误并退出码 1
```

---

### 发现 3：ZIP 包不完整，Skill 无法独立运行（中危）

**位置**：`aims-audit.zip` 包内容

**证据**：

上传的 ZIP 仅含一个文件：
```
aims-audit/
└── SKILL.md    (5258 bytes)
```

SKILL.md 工作流引用 4 个脚本，均不在包内。从解压目录执行工作流命令全部失败：

```
$ cd aims-audit/
$ python3 ra-qm-team/skills/iso42001-specialist/scripts/aims_gap_analyzer.py evidence.json
can't open file '.../aims-audit/ra-qm-team/.../aims_gap_analyzer.py': [Errno 2] No such file or directory
退出码: 2

$ python3 ../../skills/compliance-os/scripts/cross_framework_mapper.py program.json
can't open file '.../skills/compliance-os/scripts/cross_framework_mapper.py': [Errno 2] No such file or directory
退出码: 2
```

**影响**：
- 用户单独获取 aims-audit.zip 后无法执行任何工作流命令
- Skill 的六问审查流程完全依赖外部脚本，包本身不可用
- 插件清单 `.claude-plugin/plugin.json` 声明"Reuses the 14 existing ra-qm-team skills"但未声明版本约束或来源

**修复建议**：
- 在 ZIP 中包含被引用脚本，或在 SKILL.md 中明确说明前置依赖（需先获取完整 compliance-os 插件和 ra-qm-team 仓库）
- 在 plugin.json 中声明对 ra-qm-team 的版本依赖

**复测方法**：
```bash
# 在仅含 SKILL.md 的目录中验证
cd /path/to/extracted/aims-audit
ls ra-qm-team/skills/iso42001-specialist/scripts/ 2>&1
# 预期：No such file or directory（修复后应能找到脚本）
```

---

### 发现 4：相对路径基准不一致（低危）

**位置**：`skills/aims-audit/SKILL.md` 工作流命令

**证据**：

SKILL.md 中的 4 条工作流命令使用了两种不同的相对路径基准：

| 命令 | 路径风格 | 基准目录 |
|------|----------|----------|
| `python ra-qm-team/skills/.../aims_gap_analyzer.py` | `ra-qm-team/...` | 仓库根目录（`claude-skills/`） |
| `python ../../skills/compliance-os/scripts/cross_framework_mapper.py` | `../../skills/...` | aims-audit Skill 目录 |

前 3 条命令假设工作目录是 monorepo 根，第 4 条假设工作目录是 Skill 自身目录。无法从同一目录成功执行全部 4 条命令。

**影响**：
- 用户按 SKILL.md 顺序执行命令时，前 3 条和第 4 条必有一组路径解析失败
- 在智能体场景中，Agent 可能从任意工作目录执行命令，导致间歇性失败

**修复建议**：
统一使用一种路径基准（建议全部相对于 Skill 目录），或在 SKILL.md 中明确标注每条命令的执行目录。

**复测方法**：
```bash
# 从 aims-audit 目录执行
cd .../compliance-os/skills/aims-audit
python3 ra-qm-team/skills/iso42001-specialist/scripts/aims_gap_analyzer.py 2>&1
# 预期：No such file or directory（路径基准错误）
```

---

### 发现 5：ANSI 转义序列注入（低危）

**位置**：所有 7 个脚本的 `render_text()` 函数

**证据**：

脚本将用户控制的 JSON 字符串直接通过 f-string 拼接到终端输出，未过滤 ANSI 转义码：

```
$ python3 -c "
import json
data = {'program': '\u001b[31mRED\u001b[0m', 'enabled_frameworks': ['iso_27001']}
json.dump(data, open('/tmp/t.json','w'))
"
$ python3 cross_framework_mapper.py /tmp/t.json | cat -v
...
Program: ^[[31mRED^[[0m
```

在真实终端中，`^[[31m` 会将后续文本渲染为红色。

**影响**：
- 可伪造终端输出颜色/样式，用于社会工程（如将错误信息伪装成正常输出）
- 可插入终端控制序列（如清屏、光标移动）隐藏恶意输出
- 在 CI/CD 日志中可能导致日志注入

**修复建议**：
在输出用户可控字符串前过滤 ANSI 转义序列，或使用 `repr()` 输出。可添加一个 `sanitize()` 函数：
```python
import re
ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
def sanitize(s): return ANSI_RE.sub('', str(s))
```

**复测方法**：
```bash
python3 -c "
import json
json.dump({'program':'\u001b[31mRED\u001b[0m','enabled_frameworks':['iso_27001']}, open('/tmp/t.json','w'))
"
python3 cross_framework_mapper.py /tmp/t.json | cat -v
# 修复后：应输出 "Program: RED"（无转义序列）
```

---

### 发现 6：`python` 与 `python3` 命令指向不同解释器（低危）

**位置**：SKILL.md 所有工作流命令均使用 `python`

**证据**：

```
$ python --version   → Python 3.13.13（沙箱路径）
$ python3 --version  → Python 3.9.6（系统 /usr/bin/python3）
```

SKILL.md 使用 `python`，但在不同系统上 `python` 可能指向 Python 2、Python 3 或不存在。

**影响**：
- 跨平台可移植性问题；在某些 Linux 发行版上 `python` 不存在或指向 Python 2
- 不同解释器版本可能导致行为差异（虽然脚本仅用 stdlib，兼容性风险较低）

**修复建议**：在 SKILL.md 中统一使用 `python3`，或在脚本 shebang 中使用 `#!/usr/bin/env python3` 并建议通过 `./script.py` 执行。

**复测方法**：
```bash
which python && python --version
which python3 && python3 --version
# 检查两者是否一致
```

---

### 发现 7：Agent 工具权限过宽（低危）

**位置**：`agents/cs-aims-iso42001.md` frontmatter

**证据**：

```yaml
tools: [Read, Write, Bash, Grep, Glob]
```

该 Agent 的职责是只读合规审计（运行 Python 脚本、读取知识库文件），但被授予了 `Write` 和 `Bash` 权限。

**影响**：
- `Write` 允许 Agent 修改任意文件，超出审计所需
- `Bash` 允许执行任意系统命令，若 Agent 被提示注入可导致命令执行
- 违反最小权限原则

**修复建议**：
- 移除 `Write` 权限（审计工具不需要写入文件）
- 若必须保留 `Bash`，应限制为特定命令或通过白名单机制
- 考虑仅使用 `[Read, Grep, Glob]` + 预定义脚本执行

**复测方法**：
```bash
grep "^tools:" agents/cs-aims-iso42001.md
# 修复后：应不包含 Write
```

---

### 发现 8：错误消息回显文件路径（信息）

**位置**：所有 7 个脚本的 `main()` 函数

**证据**：

```python
print(f"error: could not read {args.path}: {e}", file=sys.stderr)
print(f"error: invalid JSON in {args.path}: {e}", file=sys.stderr)
```

**影响**：向用户回显其提供的文件路径本身风险较低（用户已知路径），但在智能体场景中，若路径由上游 LLM 生成且包含敏感信息，可能在日志中泄露。

**修复建议**：低优先级，可保持现状。如需加固，可仅输出文件名而非完整路径。

---

## 四、正面安全属性

经审计确认，以下安全属性成立：

| 属性 | 验证方法 | 结果 |
|------|----------|------|
| 无第三方依赖 | `grep -E "^import \|^from " *.py` | 全部仅用 argparse, json, sys, typing |
| 无代码执行函数 | `grep -nE "eval(\|exec(\|subprocess\|os\.system\|pickle\|marshal\|shell=True"` | 无匹配（退出码 1） |
| 无网络调用 | `grep -nE "urllib\|requests\|socket\|http"` | 无匹配（退出码 1） |
| 无文件写入/删除 | `grep -nE "open\(.*'w\|os\.remove\|shutil\|mkdir"` | 无匹配（退出码 1） |
| 无外部账号依赖 | 代码审查 | 全部本地离线运行 |
| 确定性逻辑 | 代码审查 | 无 LLM 调用、无随机数、无时间依赖 |
| 文件读取仅限 JSON 解析 | 黑盒测试 `/etc/passwd` | 非 JSON 文件被拒绝，仅输出解析错误 |

---

## 五、风险汇总

| 编号 | 发现 | 风险等级 | 可利用性 | 影响范围 |
|------|------|----------|----------|----------|
| 1 | 未捕获异常导致 DoS + 路径泄露 | 中 | 高（任意用户输入） | 工作流中断、信息泄露 |
| 2 | 类型混淆导致静默错误结果 | 中 | 中（需 LLM 传错类型） | 审计结论错误 |
| 3 | ZIP 包不完整，无法独立运行 | 中 | 不适用（可用性缺陷） | Skill 不可用 |
| 4 | 相对路径基准不一致 | 低 | 不适用（可用性缺陷） | 命令执行失败 |
| 5 | ANSI 转义序列注入 | 低 | 中（需控制输入 JSON） | 终端输出伪造 |
| 6 | python/python3 命令不一致 | 低 | 不适用（可移植性） | 跨平台失败 |
| 7 | Agent 权限过宽 | 低 | 低（需提示注入） | 潜在文件篡改/命令执行 |
| 8 | 错误消息回显路径 | 信息 | 低 | 轻微信息泄露 |

**总体评价**：该 Skill 的 Python 脚本安全基线良好——纯标准库、无网络、无写入、无危险函数。主要风险集中在输入验证缺失（异常崩溃和类型混淆）和打包/路径问题上。未发现可直接导致远程代码执行或数据泄露的漏洞。

---

## 六、实际读取的 Skill 文件

以下是本次审计实际读取的文件（相对于 `aims-audit.zip` 解压目录或插件根目录）：

| 文件 | 相对路径 | 读取原因 |
|------|----------|----------|
| aims-audit Skill 定义 | `aims-audit/SKILL.md`（ZIP 内） | 评测目标，必须完整阅读 |
| compliance-os 主 Skill | `skills/compliance-os/SKILL.md` | aims-audit 依赖其脚本和工作流 |
| 插件清单 | `.claude-plugin/plugin.json` | 了解插件结构、版本和依赖声明 |
| Agent 定义 | `agents/cs-aims-iso42001.md` | 审查关联智能体的工具权限 |
| 框架选择脚本 | `skills/compliance-os/scripts/framework_selector.py` | 安全审查 |
| 跨框架映射脚本 | `skills/compliance-os/scripts/cross_framework_mapper.py` | 安全审查 |
| 审计模拟脚本 | `skills/compliance-os/scripts/audit_simulator.py` | 安全审查 |
| 证据池脚本 | `skills/compliance-os/scripts/evidence_pool_generator.py` | 安全审查 |
| 差距分析脚本 | `ra-qm-team/skills/iso42001-specialist/scripts/aims_gap_analyzer.py` | SKILL.md 引用，安全审查 |
| 风险登记册脚本 | `ra-qm-team/skills/iso42001-specialist/scripts/ai_risk_register_builder.py` | SKILL.md 引用，安全审查 |
| 审计计划脚本 | `ra-qm-team/skills/iso42001-specialist/scripts/aims_audit_scheduler.py` | SKILL.md 引用，安全审查 |

### SKILL.md 规则对执行的实际影响

1. **六问审查框架**（SKILL.md 第 7-25 行）：决定了审计需覆盖范围声明、AI 政策、风险登记册、风险评估重审、内部审计计划、ISMS/QMS 集成六个维度。本次安全审计参照此结构检查了每个问题对应的工具链是否可用。
2. **工作流命令**（第 27-44 行）：4 条 `python` 命令是发现路径问题（发现 3、4）和缺失脚本问题的直接依据。
3. **输出格式要求**（第 46-74 行）：要求 Markdown 报告含差距分析、风险登记册、审计计划、跨框架复用、结论和前 3 项行动。本报告的结构参照此要求。
4. **脚本路径引用**（第 29-35 行）：`ra-qm-team/skills/...` 和 `../../skills/compliance-os/scripts/...` 的混合路径是发现 4 的来源。
5. **关联 Agent 声明**（第 78 行 `cs-aims-iso42001`）：引导我读取并审查了 Agent 定义文件，发现权限过宽问题（发现 7）。

---

## 七、缺失项与已完成范围

### 缺失项

| 缺失项 | 影响 | 状态 |
|--------|------|------|
| ZIP 中不含 3 个 ra-qm-team 脚本 | 无法从 ZIP 独立运行工作流 | 已在系统完整项目中找到并审计 |
| ZIP 中不含 4 个 compliance-os 脚本 | 同上 | 已在系统完整项目中找到并审计 |
| ZIP 中不含知识库文件（iso42001_clauses.md 等 4 个 .md） | 无法验证知识库内容安全性 | 已确认文件在完整项目中存在，未逐行审查（为静态 Markdown，无执行风险） |
| ZIP 中不含 plugin.json 和 agents/ | 无法从 ZIP 判断插件结构 | 已在系统完整项目中找到并审查 |

### 已完成范围

- 全部 7 个 Python 脚本的静态代码审查（含危险函数、依赖、网络、文件操作检查）
- 全部 7 个脚本的内置样例运行验证
- 黑盒安全测试：路径遍历、异常类型、ANSI 注入、空值、越界值
- 相对路径解析验证（从多个工作目录测试）
- Agent 权限配置审查
- 插件清单和依赖声明审查
- `python`/`python3` 解释器差异验证

### 未完成范围及原因

- 未对知识库 Markdown 文件（4 个 references .md）做内容安全审查：这些文件为静态文档，不被任何脚本 `exec`/`eval`，无代码执行风险；且不在上传的 ZIP 中。
- 未对其他 7 个 Agent（cs-compliance-officer 等）做权限审查：本次评测对象为 aims-audit，仅审查了其直接关联的 cs-aims-iso42001。
- 未进行动态模糊测试（如长时间大输入压测）：受"不新增依赖"约束，未安装模糊测试框架；手工测试已覆盖主要异常输入类型。
