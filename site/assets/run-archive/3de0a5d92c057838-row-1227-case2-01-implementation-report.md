# 实现报告：最小示例项目审阅与改进

## 一、结论概述

原始项目 `wechat-skill-eval-sample` 存在 **四处缺陷**，导致 `npm test` 无法运行或运行结果无意义。经最小化改动后，项目可通过一次性命令 `npm test` 重复验证，7 个断言测试全部通过（退出码 0），无外部依赖、无生产凭据、无常驻进程。

---

## 二、实际读取的 Skill 文件

| 相对路径 | 说明 |
|---|---|
| `using-agent-skills/SKILL.md` | 本次评测的元技能，唯一执行依据 |

> ZIP 解压后仅含上述一个文件，未发现 `references/definition-of-done.md` 等被引用的外部文件，因此以 SKILL.md 正文中的 Definition of Done 描述（测试通过、无回归、运行时行为验证、文档更新）为准。

---

## 三、识别到的冲突与约束（至少两种）

### 冲突 A：导入路径与文件实际位置不一致

- **现象**：`test.js` 中写 `import { normalizeOrder } from "./src/app.js"`，但 `app.js` 实际位于项目根目录。
- **复现**：运行 `npm test` 立即抛出 `ERR_MODULE_NOT_FOUND: Cannot find module '.../src/app.js'`。
- **根因**：测试文件假定了 `src/` 目录结构，但项目未建立该结构。

### 冲突 B：ESM 语法与 package.json 模块类型不匹配

- **现象**：`app.js` 和 `test.js` 均使用 `export` / `import`（ESM 语法），但 `package.json` 缺少 `"type": "module"` 字段。
- **风险**：Node.js 默认将 `.js` 文件按 CommonJS 解析，在未显式声明模块类型时，ESM 语法可能触发 `SyntaxError` 或行为不一致。
- **取舍**：选择在 `package.json` 加 `"type":"module"` 而非将源码改写为 CommonJS（`require`/`module.exports`），因为源码已统一使用 ESM，改写反而增加改动量并引入风格不一致。

### 冲突 C：测试无断言，"通过"无意义

- **现象**：原始 `test.js` 仅含一行 `console.log(normalizeOrder(...))`，无任何 `assert` 或期望校验。
- **后果**：只要进程不崩溃，`npm test` 退出码恒为 0；即使 `normalizeOrder` 返回错误结果也无法发现。这直接违反 SKILL.md 的 **"Verify, Don't Assume"** 规则——"Seems right" is never sufficient。
- **改进**：使用 Node.js 内置 `node:test` + `node:assert/strict`，零外部依赖，编写 7 个含明确断言的测试用例。

### 冲突 D：边界值处理缺陷（数据污染风险）

| 输入 | 原始行为 | 问题 |
|---|---|---|
| `{ id: 0 }` | 抛出 "missing order id" | `!0` 为 `true`，数字 0 被误判为缺失 |
| `{ id: 1, amount: "abc" }` | 返回 `{ amount: NaN }` | NaN 向下游传播，污染数据 |
| `{ id: 1, amount: -5 }` | 返回 `{ amount: -5 }` | 负金额未拦截，业务上非法 |
| `{ id: 1, amount: 0 }` | `0 \|\| 0 → 0`（碰巧正确） | `\|\|` 对 falsy 值不精确，`??` 更安全 |

---

## 四、改进方案（最小化改动）

### 4.1 package.json

```json
{
  "name": "wechat-skill-eval-sample",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test test.js" }
}
```

改动点：新增 `"type":"module"`（解决冲突 B）；测试脚本改为 `node --test test.js`（启用内置测试运行器）。

### 4.2 app.js

```js
export function normalizeOrder(order) {
  if (!order || order.id == null || order.id === "") {
    throw new Error("missing order id");
  }
  const amount = Number(order.amount ?? 0);
  if (!Number.isFinite(amount) || amount < 0) {
    throw new Error("invalid amount");
  }
  return { id: String(order.id), amount };
}
```

改动点：
- `!order.id` → `order.id == null || order.id === ""`：精确判断 null/undefined/空串，不再误杀 `id=0`。
- `Number(order.amount || 0)` → `Number(order.amount ?? 0)`：仅在 null/undefined 时缺省为 0。
- 新增 `Number.isFinite` 和负数校验：拦截 NaN 和负金额。

### 4.3 test.js

将导入路径从 `./src/app.js` 修正为 `./app.js`（解决冲突 A），使用 `node:test` + `node:assert/strict` 编写 7 个测试用例，覆盖：正常转换、id=0、金额缺省、金额=0、缺少 id、非数字金额、负数金额。

---

## 五、关键取舍、依赖与风险

### 取舍

1. **修导入路径 vs 建 src/ 目录**：选择修路径（一行改动），而非移动文件到 `src/`。遵循 SKILL.md "Maintain Scope Discipline"——Touch only what you're asked to touch。
2. **内置测试运行器 vs 引入 Jest/Mocha**：选择 `node:test`（Node 18+ 内置，零依赖）。遵循 "Enforce Simplicity"——避免为 7 个简单断言引入数百个传递依赖。
3. **加金额校验 vs 保持原样**：选择加校验。原始代码对 NaN 和负数静默放行，在订单场景中属于数据正确性缺陷，必须拦截。

### 依赖

- **运行时**：Node.js >= 18（`node:test` 和 `node:assert/strict` 所需）。当前环境为 Node v22.23.1，满足要求。
- **零第三方 npm 包**：`package.json` 无 `dependencies` / `devDependencies`，`npm install` 非必需。

### 风险

1. **金额语义假设**：本报告假定金额不应为负数且必须为有限数字。若业务允许负金额（如退款场景），需移除 `amount < 0` 校验。此假设已在开头显式暴露。
2. **id 类型假设**：假定 `id` 可以是数字或字符串，空串视为缺失。若业务允许空串 id，需调整校验。
3. **SKILL.md 引用文件缺失**：SKILL.md 中引用了 `../../references/definition-of-done.md`，但 ZIP 中不含该文件。本报告以 SKILL.md 正文描述的 Definition of Done 为准，未编造该文件内容。

---

## 六、验证结果

执行命令：`npm test`（等价于 `node --test test.js`）

```
TAP version 13
ok 1 - 将数字 id 转为字符串、字符串金额转为数字
ok 2 - id=0 是合法值（不应被 falsy 检查误杀）
ok 3 - 金额缺省时默认为 0
ok 4 - 金额为 0 时保持 0（不被 || 误判为缺省）
ok 5 - 缺少 id 时抛出错误
ok 6 - 非数字金额抛出错误（防止 NaN 污染）
ok 7 - 负数金额抛出错误
1..7
# tests 7
# pass 7
# fail 0
# duration_ms 174.01705
```

退出码：`0`。验证通过，符合 Definition of Done（测试通过、无回归、运行时行为已验证、文档即本报告已更新）。

---

## 七、确实影响结果的 SKILL.md 规则

> **规则：Core Operating Behaviors #6 — "Verify, Don't Assume"**
>
> 原文："Every skill includes a verification step. A task is not complete until verification passes. 'Seems right' is never sufficient — there must be evidence (passing tests, build output, runtime data)."
>
> **影响**：原始 `test.js` 仅 `console.log` 无断言，`npm test` 永不失败——这正是 "Seems right" 的典型反模式。受此规则驱动，本次改进将测试重写为含 7 个 `assert` 断言的用例，并实际运行确认退出码为 0。若未遵循此规则，仅修复路径和 ESM 配置后 `console.log` 仍会"看起来通过"，但边界值缺陷（id=0、NaN 金额）将永远不会被发现。

---

## 八、复测方法

```bash
# 1. 进入项目目录
cd project

# 2. 运行测试（无需 npm install，零外部依赖）
npm test

# 预期：7 pass / 0 fail，退出码 0
```

若需验证原始缺陷，可将 `app.js` 还原为原始版本后运行测试，预期用例 2（id=0）、6（NaN 金额）、7（负数金额）会失败。
