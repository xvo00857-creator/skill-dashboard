# 恒定时间安全测试报告

**被测 Skill**：constant-time-testing（分类：安全与合规）
**被测函数**：`mod_exp_vuln(base, exp)` — 处理不可信二进制输入（攻击者可控密文 `base`）、使用秘密指数 `exp`（私钥）的模幂运算
**测试日期**：2026-08-12
**测试环境**：macOS / arm64（Apple Silicon），Apple clang 17.0.0，10 核

---

## 一、约束条件与方案变化

### 1.1 给定约束

| 约束 | 影响 |
|------|------|
| 时间与资源受限 | dudect 单次运行从 SKILL.md 建议的 5–10 分钟缩短为 60–120 秒；不做形式化验证 |
| 环境无 Valgrind | SKILL.md 推荐的 Timecop 动态追踪无法执行，改用反汇编静态定位根因 |
| 环境为 arm64 macOS | dudect 上游仅支持 x86（SSE/RDTSC），需移植时钟源；无 `taskset` 绑核 |
| 未提供真实目标代码 | 构造与 SKILL.md 示例一致的代表性脆弱函数（square-and-multiply 模幂） |
| 无 brew/root 权限 | 无法安装 Valgrind、无法安装交叉编译器测试 x86/其他架构 |

### 1.2 因此做出的取舍（按优先级）

| 优先级 | 动作 | 放弃/降级 |
|--------|------|-----------|
| P0（必做） | dudect 统计测试（SKILL.md："Start with dudect"） | — |
| P0 | 反汇编根因定位（SKILL.md Phase 2 列出 `objdump -d`） | Timecop 动态追踪（环境缺 Valgrind） |
| P1 | 修复后 dudect 复验 | 30 分钟以上长时运行、多编译器（gcc/MSVC）、多架构（x86/ARM） |
| P1 | 功能正确性验证（64 固定 + 10000 随机用例） | — |
| P2 | 独立时序对比演示（辅助证据） | — |
| P3（未做） | 形式化验证（ct-verif/SideTrail/FaCT） | 时间/专业知识不足，标记为待确认 |
| P3（未做） | CI 集成 | 本次仅交付测试工件，CI 配置标记为待确认 |

### 1.3 验收标准

1. dudect 对脆弱版报告 t > 10（SKILL.md 阈值：t > 10 为 "Probably not constant time"，t > 500 为 "Definitely not constant time"）
2. dudect 对修复版在 ≥1000 万次测量中 t < 10 且不随样本量增长
3. 反汇编中脆弱版存在依赖秘密数据的条件分支指令，修复版不存在
4. 修复版与脆弱版在固定 + 随机用例上输出完全一致

---

## 二、测试目标

验证 `mod_exp_vuln` 在处理不可信二进制输入（密文 `base`）时，执行时间是否与秘密指数 `exp` 相关，从而存在 Kocher 时序侧信道（可逐位恢复私钥）。若存在，定位根因并给出恒定时间修复。

威胁模型：攻击者可反复提交任意密文（不可信二进制输入）并观测响应时间，私钥指数 `d` 长期固定。

---

## 三、种子与样例

### 3.1 dudect 输入类（统计测试）

输入块 16 字节：`base`（8B，不可信输入）+ `exp`（8B，秘密）。

| 类别 | base（不可信） | exp（秘密） |
|------|---------------|-------------|
| class 0 | 随机 | 固定 `0xAAAAAAAAAAAAAAAA`（汉明重量 32） |
| class 1 | 随机 | 随机 64 位值 |

类别序列由 `randombit()` 随机化（SKILL.md 强调必须随机化类别顺序）。

### 3.2 独立时序演示种子

| 种子 | exp 值 | 汉明重量 | 用途 |
|------|--------|----------|------|
| 稀疏指数 | `0x8000000000000001` | 2 | 最少乘法次数 |
| 稠密指数 | `0x7FFFFFFFFFFFFFFE` | 62 | 最多乘法次数 |

### 3.3 正确性用例

- 64 组固定组合：base ∈ {0,1,2,3,0x0123…CDEF,0xFFFF…FFFF,0xFFFF…FFC5,0x1234…CDEF}，exp ∈ {0,1,2,3,0xAAAA…AAAA,0x8000…0001,0x7FFF…FFFE,0xFFFF…FFFF}
- 10000 组随机组合（种子 42）

---

## 四、执行命令

```bash
# 1. 编译（-O0 和 -O2 两个优化级别）
./build.sh O0
./build.sh O2

# 2. dudect 统计测试（脆弱版，运行至检出或超时）
./dudect_vuln_O0
./dudect_vuln_O2

# 3. dudect 统计测试（修复版，限时 60 秒）
./dudect_ct_O0    # 60s 后 kill
./dudect_ct_O2    # 60s 后 kill

# 4. 独立时序演示
./timing_demo_O0
./timing_demo_O2

# 5. 反汇编根因分析
otool -tv /tmp/vuln_O0.o   # 脆弱版 -O0
otool -tv /tmp/vuln_O2.o   # 脆弱版 -O2
otool -tv /tmp/ct_O0.o     # 修复版 -O0
otool -tv /tmp/ct_O2.o     # 修复版 -O2

# 6. 功能正确性
clang -std=c11 -O2 -Itarget -o /tmp/correctness /tmp/correctness.c \
    target/modexp_vuln.c target/modexp_ct.c && /tmp/correctness
```

---

## 五、发现记录

### 发现 1（CRITICAL）：秘密相关条件分支 — -O0

- **位置**：`modexp_vuln.c` 第 18 行 `if (exp & 1)`
- **dudect 结果**：9 万次测量时 t = **+630.39**，判定 "Definitely not constant time"
- **反汇编证据**（`otool -tv vuln_O0.o`）：
  ```
  0x44  tbz  w8, #0x0, 0x70    ; 测试 exp 最低位，为 0 则跳过乘法
  0x4c  ...                     ; 乘法块（仅当 bit=1 执行）
  0x70  lsr  x8, x8, #1         ; exp >>= 1
  ```
  `tbz`（test bit and branch if zero）直接依赖秘密指数位，为 0 时跳过一次 64 位乘法+取模，产生显著时间差。
- **独立时序证据**（-O0，20 万次中位数，系统空闲）：稀疏指数 46.7ms vs 稠密指数 63.5ms，比值 **1.36×**
- **-O2 时序演示说明**：-O2 下两个演示指数的最高位分别为 bit 63 和 bit 62（循环仅差 1 次），墙钟时间比值 0.98×（噪声内），但 dudect 用随机指数（含各种位长）仍检出 t=31.58——这正说明简单计时对比不足以发现细微泄漏，需要 dudect 的统计检验

### 发现 2（HIGH）：秘密相关循环边界 — -O2

- **位置**：`modexp_vuln.c` 第 16 行 `while (exp > 0)`
- **dudect 结果**：10 万次测量时 t = **+31.58**，判定 "Probably not constant time"
- **反汇编证据**（`otool -tv vuln_O2.o`）：
  ```
  0x24  tst  x1, #0x1
  0x28  csel x0, x0, x9, eq     ; 内层 if 被编译器优化为无分支 csel
  0x40  cmp  x1, #0x1
  0x48  b.hi 0x14               ; 循环回边依赖 exp 最高位位置（秘密!）
  ```
  -O2 下内层 `if` 被编译为 `csel`（无分支），但 `while (exp > 0)` 的循环次数仍取决于秘密指数的最高位位置，泄漏指数位长。t 值从 630 降至 31 说明编译器部分缓解但未消除泄漏。
- **意义**：不能依赖编译器优化保证恒定时间（SKILL.md "Common Mistakes" 明确警告）

### 发现 3（已修复）：修复版无泄漏证据

| 版本 | 测量次数 | 全程最大 t | 末期 t | 判定 |
|------|----------|-----------|--------|------|
| ct -O0 | 20.8M | 3.24 | 0.67 | 无泄漏证据 |
| ct -O2 | 41.0M | 2.51 | 1.90 | 无泄漏证据 |

t 值远低于阈值 10，且不随样本量增长（恒定时间代码的 t 值在噪声范围内波动；泄漏代码的 t 值随 √n 增长）。

- **反汇编证据**（ct -O2）：唯一条件分支为 `cmp x8, #0x40; b.ne 0x14`（公开循环计数器 0–63），秘密位仅经 `tst` + `csel` 无分支处理。
- **功能正确性**：64 组固定 + 10000 组随机用例，修复版与脆弱版输出**完全一致**。

---

## 六、修复建议

### 6.1 已实施的修复（`modexp_ct.c`）

1. **固定迭代次数**：`for (int i = 0; i < 64; i++)` 替代 `while (exp > 0)`，消除秘密相关循环边界
2. **位掩码选择替代分支**：`mask = 0 - bit`（全 1 或全 0），`ct_select(mask, candidate, result)` 用纯位运算 `(a & mask) | (b & ~mask)` 选择结果
3. **乘法始终执行**：无论 bit 为 0 或 1 都计算 `(result * base) % MOD`，仅选择是否采用

### 6.2 生产环境进一步建议（待确认）

| 建议 | 说明 | 状态 |
|------|------|------|
| 使用经过审计的恒定时间库 | 如 OpenSSL BIGNUM、libsodium、HACL*，避免自行实现 | 待确认（本次未验证具体库版本） |
| Montgomery 乘法常时化 | 本次用编译期常量模数，除法被优化为乘法；非常量模数需 Montgomery 等常时模乘 | 待确认（未实现/未测试） |
| 多编译器/多架构回归 | SKILL.md 建议测试 gcc/clang/MSVC 及 x86/ARM 不同优化级别 | 待确认（本次仅 Apple clang/arm64） |
| 长时 dudect 运行 | SKILL.md 建议修复后运行 30 分钟以上提高统计置信度 | 待确认（本次仅 60 秒） |
| Timecop/Valgrind 动态追踪 | 在 Linux x86 CI 环境补跑，精确定位泄漏行 | 待确认（macOS 无 Valgrind） |
| 形式化验证 | 高保障场景使用 ct-verif/SideTrail 证明无泄漏 | 待确认（本次未执行） |
| 集成 CI | dudect 加入 CI，5–10 分钟超时，检出泄漏即失败 | 待确认（本次未配置） |
| 检查 `udiv` 指令 | arm64 `udiv` 对 64 位除法为常时，但 x86 `div` 可能变时；跨平台需审查 | 待确认（未在 x86 验证） |

---

## 七、验证证据清单

所有证据文件位于 `ct-test/results/`：

| 文件 | 内容 |
|------|------|
| `dudect_vuln_O0.log` | 脆弱版 -O0：t=630.39，Definitely not constant time |
| `dudect_vuln_O2.log` | 脆弱版 -O2：t=31.58，Probably not constant time |
| `dudect_ct_O0.log` | 修复版 -O0：20.8M 测量，max t=3.24 |
| `dudect_ct_O2.log` | 修复版 -O2：41.0M 测量，max t=2.51 |
| `disasm_vuln_O0.txt` | 脆弱版 -O0 反汇编（含 `tbz` 秘密分支） |
| `disasm_vuln_O2.txt` | 脆弱版 -O2 反汇编（含秘密相关循环回边） |
| `disasm_ct_O0.txt` | 修复版 -O0 反汇编（无秘密分支） |
| `disasm_ct_O2.txt` | 修复版 -O2 反汇编（仅公开循环计数器分支） |
| `timing_demo_O0.txt` | -O0 时序演示：vuln 1.36×，ct 1.00× |
| `timing_demo_O2.txt` | -O2 时序演示：vuln 0.98×（噪声内），ct 1.00× |

源代码位于 `ct-test/target/`（`modexp.h`、`modexp_vuln.c`、`modexp_ct.c`），测试 harness 位于 `ct-test/harness/`。

---

## 八、实际读取的 Skill 文件及影响的规则

### 8.1 实际读取的文件

| 文件路径（相对 ZIP 根） | 说明 |
|------------------------|------|
| `constant-time-testing/SKILL.md` | Skill 主文件，完整阅读（506 行） |
| `constant-time-testing/agents/openai.yaml` | 界面配置（图标/品牌色），与测试执行无关 |
| `constant-time-testing/assets/trail-of-bits-mark.svg` | 品牌图标，未读取内容（与测试无关） |

### 8.2 实际影响执行的 SKILL.md 规则

| SKILL.md 规则 | 对本次执行的影响 |
|---------------|-----------------|
| "Start with dudect - Quick statistical check for timing differences"（Testing Workflow / Phase 1） | 选择 dudect 作为首要工具，优先编写 dudect harness |
| dudect 输入类设计：固定 vs 随机秘密，公开输入随机（"Secret-Dependent Branch: Deep dive" 代码示例） | harness 的 `prepare_inputs` 直接采用此模式：class 0 固定指数、class 1 随机指数，base 两类均随机 |
| 四类违规模式（"Common Constant-Time Violation Patterns"） | 识别出 `if (exp & 1)` 属第 1 类（条件跳转，CRITICAL）；`while (exp > 0)` 同属秘密相关控制流 |
| Phase 2 根因工具："Timecop, compiler output (`objdump -d`)" | 因无 Valgrind，用 `otool -tv`（macOS 等价物）反汇编定位根因 |
| "Common Mistakes": "-O0 may hide leaks present in -O3" 及 "Test at production optimization level" | 同时测试 -O0 和 -O2；发现 -O2 下内层分支被优化为 csel 但循环边界仍泄漏 |
| 修复指南（Phase 3: Remediation）："Replace conditional branches with constant-time selection (bitwise operations)"、"fixed iteration count" | 修复版采用位掩码 ct_select + 固定 64 次循环 |
| t 值阈值：t > 10 为 "Probably not constant time"，t > 500 为 "Definitely not constant time" | 作为验收标准判定泄漏 |
| "Pin dudect to isolated CPU core (`taskset -c 2`)"（Tips） | macOS 无 taskset，未能绑核，标记为噪声来源（待确认） |
| "Run dudect for extended periods (hours)" / "5-10 minutes in CI" | 受时间约束仅运行 60–120 秒，修复版结论为"无泄漏证据"而非"证明无泄漏" |
| Timecop quick start（`poison`/`unpoison` + Valgrind） | 编写了 Timecop harness 方案但因环境无 Valgrind 未执行，标记为待确认 |
| "If leaks found - Use Timecop to pinpoint root cause" | 因 Timecop 不可用，用反汇编替代完成根因定位 |

### 8.3 未执行/待确认项

- **Timecop 动态追踪**：环境无 Valgrind（`valgrind: command not found`，且无 brew 无法安装），SKILL.md 指引的 Timecop 流程未执行
- **形式化验证**（ct-verif/SideTrail/FaCT）：时间与专业知识不足
- **dudect 长时运行**（30 分钟以上）：时间约束，仅运行 60–120 秒
- **多编译器/多架构**：仅 Apple clang 17 / arm64，未测试 gcc、x86、不同 CPU 微架构
- **绑核降噪**：macOS 无 `taskset`，未隔离 CPU 核心
- **dudect 上游对 arm64 macOS 的适配**：上游 dudect.h 硬编码 x86 SSE/RDTSC，本次做了本地补丁（替换为 `clock_gettime_nsec_np(CLOCK_UPTIME_RAW)`）；该补丁未经上游审核，跨平台适用性待确认

---

## 九、缺失项与已完成范围声明

### 已完成

- 解压并完整阅读 SKILL.md
- 构造代表性脆弱目标函数（处理不可信二进制输入的模幂运算）
- dudect 统计测试（脆弱版 -O0/-O2、修复版 -O0/-O2）
- 反汇编根因定位（4 个配置）
- 独立时序对比演示
- 恒定时间修复及功能正确性验证
- 修复后 dudect 复验

### 缺失/未完成（如实声明）

1. **无真实目标代码**：用户未提供待审计的实际代码库，本次目标函数为基于 SKILL.md 示例构造的代表性样例，非真实产品代码
2. **Timecop 未执行**：环境缺 Valgrind，无法运行 SKILL.md 推荐的动态追踪
3. **统计置信度有限**：修复版仅运行 60 秒（20M–41M 测量），dudect 只能给出"无泄漏证据"而非"证明无泄漏"
4. **dudect arm64 移植为本地补丁**：时钟源从 RDTSC 换为纳秒级单调时钟，分辨率和开销不同于周期计数器，可能影响弱信号检测能力
5. **未做符号执行/形式化验证**
6. **未做 CI 集成配置**
