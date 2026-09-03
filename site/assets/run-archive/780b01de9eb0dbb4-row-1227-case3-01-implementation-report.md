# 实现报告：最小示例项目审阅与改进

## 一、执行依据

本报告严格依据随消息上传的 Skill ZIP 中 `SKILL.md` 执行。Skill 名称 `using-agent-skills`，分类"自动化与工具"，是一个元技能（meta-skill），规定了技能发现与调用流程以及六条核心操作行为。

### 实际读取的 Skill 文件相对路径

| 文件 | 相对路径 | 状态 |
|------|----------|------|
| SKILL.md | `using-agent-skills/using-agent-skills/SKILL.md` | 已完整读取 |
| definition-of-done.md | `using-agent-skills/references/definition-of-done.md` | **未找到**（SKILL.md 中引用但 ZIP 内不存在） |

ZIP 解压后仅包含一个文件 `using-agent-skills/using-agent-skills/SKILL.md`，无其他子技能或参考文档。

### 确实影响结果的 SKILL.md 规则

> **Core Operating Behavior #6 — Verify, Don't Assume**："A task is not complete until verification passes. 'Seems right' is never sufficient — there must be evidence (passing tests, build output, runtime data)."

这条规则直接决定了本任务的执行方式：不能仅"审阅后给出建议"，必须实际修复代码、编写可运行测试、执行验证并保留输出证据。报告中所有结论均附带运行输出或复现命令，而非主观判断。

此外，**Core Behavior #1（Surface Assumptions）** 要求在实现前显式声明假设，本报告第二节列出了全部假设；**Core Behavior #4（Enforce Simplicity）** 要求优先选择最简方案，因此测试使用 Node 内置 `assert` 而非引入外部框架，CSV 解析手写极简实现而非引入依赖。

---

## 二、假设声明

按 SKILL.md Core Behavior #1，实现前声明以下假设：

1. 项目使用 ESM 模块（`app.js` 含 `export` 关键字），因此 `package.json` 需补充 `"type": "module"`。
2. `test.js` 中 `import { normalizeOrder } from "./src/app.js"` 是路径笔误——`app.js` 实际位于项目根目录，不存在 `src/` 子目录。
3. `id=0` 应视为合法订单 ID；原始代码 `!order.id` 将 `0` 误判为缺失。
4. `amount` 业务语义为金额，应为有限非负数；`NaN`、`Infinity`、负值均应拒绝而非静默返回。
5. 不引入外部测试框架（jest/mocha 等），使用 Node 内置 `node:assert/strict`，保持零依赖、可重复验证。
6. 不访问任何生产凭据、外部 API 或付费服务。
7. 不启动持续运行的预览或开发服务器，验证使用一次性命令。

---

## 三、原始项目审阅发现

### 3.1 package.json

| 问题 | 严重度 | 说明 |
|------|--------|------|
| 缺少 `"type": "module"` | 高 | `app.js` 使用 ESM `export`，无此字段时 `node test.js` 会因 `import` 语法报错 |
| 无依赖声明 | 低 | 项目本身零依赖，可接受；但 test 脚本仅 `node test.js`，原始 test.js 并非真实测试 |

### 3.2 app.js — normalizeOrder

原始代码：
```js
export function normalizeOrder(order) {
  if (!order || !order.id) throw new Error("missing order id");
  return { id: String(order.id), amount: Number(order.amount || 0) };
}
```

| 问题 | 严重度 | 复现证据 |
|------|--------|----------|
| `!order.id` 把 `id=0` 误判为缺失 | 高 | `normalizeOrder({id:0,amount:5})` 抛出 `missing order id` |
| `order` 非对象时未校验 | 中 | `normalizeOrder("x")` 会尝试访问 `.id` 不抛预期错误 |
| `amount` 为非数字字符串时静默返回 `NaN` | 高 | `normalizeOrder({id:1,amount:"abc"})` 返回 `{amount: NaN}` |
| `amount` 为负值时不拒绝 | 中 | `normalizeOrder({id:1,amount:-5})` 返回 `{amount: -5}` |
| `amount` 为 `Infinity` 时不拒绝 | 低 | 返回 `{amount: Infinity}` |
| `amount \|\| 0` 吞掉 `amount=0` | 低 | 此处 `0 \|\| 0 = 0` 结果巧合正确，但逻辑模式不安全 |

复现命令输出（原始逻辑）：
```
id=0 抛错: missing order id
amount=abc 结果: { id: '1', amount: NaN }
amount=-5 结果: { id: '1', amount: -5 }
```

### 3.3 test.js

原始代码：
```js
import { normalizeOrder } from "./src/app.js";
console.log(normalizeOrder({ id: 42, amount: "19.9" }));
```

| 问题 | 严重度 | 说明 |
|------|--------|------|
| 导入路径错误 `./src/app.js` | 高 | 实际文件在根目录，运行即报 `MODULE_NOT_FOUND` |
| 无断言，仅 `console.log` | 高 | 不是测试，无法自动判断通过/失败 |
| 仅覆盖一个正常场景 | 高 | 无边界场景、无异常场景覆盖 |

### 3.4 edge_cases.csv

| record_id | 问题类型 | 说明 |
|-----------|----------|------|
| 2 | 重复记录 | 完全相同的行出现两次 |
| 3 | 缺失值 | `status` 和 `value` 均为空，`notes` 为 `-` |
| 4 | 异常负值 | `status=error`，`value=-999` |
| 5 | 公式注入 | `value` 为 `=HYPERLINK("https://example.invalid","do not execute")`，在 Excel 中可执行 |
| 5 | 非标准 CSV 转义 | 字段内使用反斜杠转义 `\"`，不符合 RFC 4180（应使用 `""`） |

---

## 四、修复与实现

### 4.1 package.json

补充 `"type": "module"`，新增 `process` 脚本：
```json
{
  "name": "wechat-skill-eval-sample",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node test.js",
    "process": "node process_csv.js"
  }
}
```

### 4.2 app.js — 修复后

```js
export function normalizeOrder(order) {
  if (order === null || typeof order !== "object") {
    throw new Error("order must be an object");
  }
  if (order.id === undefined || order.id === null || order.id === "") {
    throw new Error("missing order id");
  }
  const amount = Number(order.amount ?? 0);
  if (!Number.isFinite(amount)) {
    throw new Error("amount must be a finite number");
  }
  if (amount < 0) {
    throw new Error("amount must be non-negative");
  }
  return { id: String(order.id), amount };
}
```

修复要点：
- `id` 校验改用 `=== undefined/null/""`，`id=0` 不再被误判
- 新增 `order` 类型校验
- `amount` 使用 `?? 0`（空值合并）替代 `\|\| 0`，避免吞掉合法的 `0`
- 新增 `Number.isFinite` 校验，拒绝 `NaN` 和 `Infinity`
- 新增负值校验

### 4.3 test.js — 重写为真实断言测试

使用 Node 内置 `node:assert/strict`，共 13 个测试用例，覆盖：
- 正常场景（数字 id + 字符串金额、省略 amount、amount=0）
- id=0 合法性验证（bug 修复回归测试）
- 输入异常（null、undefined、非对象、id 缺失/null/空串）
- 金额异常（非数字字符串 NaN、负值、Infinity）

测试运行失败时 `process.exit(1)`，可用于 CI 门禁。

### 4.4 process_csv.js — 新增 CSV 边界处理脚本

零依赖 Node 脚本，功能：
1. **去重**：按整行内容去重，记录被丢弃的重复行
2. **缺失值检测**：标记 `status` 或 `value` 为空的行
3. **负值检测**：标记可解析为负数的 `value`
4. **公式注入净化**：对以 `= + - @` 开头且非合法数字的字段，前置单引号 `'` 防止 Excel 执行
5. **非标准 CSV 兼容**：解析器同时支持 RFC 4180 双引号转义（`""`）和本文件使用的反斜杠转义（`\"`）
6. 输出清洗后 CSV（附加 `issues` 列）和 JSON 统计报告

---

## 五、验证证据

### 5.1 单元测试

命令：`npm test`

输出：
```
normalizeOrder 测试套件
  PASS  正常订单：数字 id + 字符串金额
  PASS  amount 省略时默认为 0
  PASS  amount 为 0 时保留 0（不被 || 吞掉）
  PASS  id=0 是合法订单 id（原代码 bug 修复验证）
  PASS  order 为 null 时抛错
  PASS  order 为 undefined 时抛错
  PASS  order 为非对象时抛错
  PASS  id 缺失时抛错
  PASS  id 为 null 时抛错
  PASS  id 为空字符串时抛错
  PASS  amount 为非数字字符串时抛错（NaN）
  PASS  amount 为负值时抛错
  PASS  amount 为 Infinity 时抛错

结果：13 通过，0 失败
```

退出码：`0`

### 5.2 CSV 边界处理

命令：`node process_csv.js`

统计输出：
```json
{
  "total": 6,
  "duplicates": 1,
  "missingStatus": 1,
  "missingValue": 1,
  "negativeValues": 1,
  "formulaInjection": 2,
  "kept": 5,
  "dropped": [
    { "reason": "duplicate", "record_id": "2", "row": ["2","ok","120","重复记录"] }
  ]
}
```

清洗后 CSV（`edge_cases_cleaned.csv`）：
```
record_id,status,value,notes,issues
1,ok,120,正常记录,ok
2,ok,120,重复记录,ok
3,(missing),,'-,missing_status;missing_value;formula_injection_sanitized
4,error,-999,异常负值,negative_value
5,ok,"'=HYPERLINK(""https://example.invalid"",""do not execute"")",公式注入测试文本,formula_injection_sanitized
```

处理说明：
- record_id=2 的重复行被丢弃 1 条，保留 1 条
- record_id=3：status 标记为 `(missing)`，value 为空，notes `-` 被净化为 `'-`（防止 Excel 将 `-` 识别为公式起始）
- record_id=4：`-999` 是合法负数，不做公式净化（避免变成文本），但标记 `negative_value`
- record_id=5：`=HYPERLINK(...)` 被净化为 `'=HYPERLINK(...)`，CSV 输出使用标准双引号转义

---

## 六、未完成项与降级说明

| 项目 | 状态 | 原因 | 降级方案 / 复测方法 |
|------|------|------|---------------------|
| `definition-of-done.md` | 未读取 | SKILL.md 引用 `../../references/definition-of-done.md`，但 ZIP 中不存在该文件 | 以 SKILL.md 正文所述 Definition of Done 原则（测试通过、无回归、运行时验证、文档更新）为准执行；若后续提供该文件可补充对照 |
| 原始 `test.js` 路径 `./src/app.js` | 已修正 | 判定为笔误，实际无 `src/` 目录 | 修正为 `./app.js`；若项目后续确有 `src/` 重构计划，需同步调整 |
| 生产环境凭据 / 外部服务 | 未涉及 | 任务明确要求不得访问生产凭据 | 全部验证在本地零依赖环境完成，无需外部服务 |
| CI/CD 集成 | 未实现 | 超出"最小示例项目"范围，按 SKILL.md Scope Discipline 不做额外扩展 | `npm test` 退出码已支持 CI 门禁，可直接接入 |

---

## 七、复测方法

在项目目录下依次执行：

```bash
# 1. 单元测试（应输出 13 通过，0 失败，退出码 0）
npm test

# 2. CSV 边界处理（应生成 edge_cases_cleaned.csv 和 csv_report.json）
node process_csv.js

# 3. 验证原始 bug 已修复（id=0 不再抛错）
node --input-type=module -e '
import { normalizeOrder } from "./app.js";
console.log(normalizeOrder({ id: 0, amount: 5 }));
'
# 期望输出：{ id: '0', amount: 5 }
```

环境要求：Node.js 14+（支持 ESM 和 `node:assert/strict`），无需安装任何依赖。

---

## 八、产物清单

| 文件 | 说明 |
|------|------|
| `package.json` | 修复后（补充 type:module、process 脚本） |
| `app.js` | 修复后（输入校验、id=0 修复、金额校验） |
| `test.js` | 重写后（13 个断言测试用例） |
| `process_csv.js` | 新增（CSV 边界处理脚本） |
| `edge_cases_cleaned.csv` | 生成（清洗后 CSV，含 issues 列） |
| `csv_report.json` | 生成（统计报告 JSON） |
| `implementation-report.md` | 本报告 |
