# 低功耗温度采集设备固件模块

## 1. 任务划分

| 模块 | 文件 | 职责 |
|------|------|------|
| 板级配置 | `inc/bsp_config.h` | 集中所有硬件参数（时钟、引脚、超时、阈值），禁止在代码中硬编码 |
| 硬件抽象层 | `inc/hal.h` / `src/hal_target.c` | I2C/UART/RTC/ADC/IWDG/GPIO 的寄存器级驱动，目标为 STM32F4 |
| 温度传感器驱动 | `inc/temp_sensor.h` / `src/temp_sensor.c` | TMP102 单次转换触发、读取、整数换算、范围校验、一致性校验 |
| 电源管理 | `inc/power_mgr.h` / `src/power_mgr.c` | 电池状态分级、采样间隔自适应、Stop 模式进出、外设门控 |
| 应用层 | `inc/app.h` / `src/app.c` | 状态机、帧组装、错误计数、看门狗喂狗、主循环 |
| 主机模拟层 | `test/hal_mock.h` / `src/hal_mock.c` | 在主机上模拟硬件，支持故障注入和状态观测 |
| 验证测试 | `test/test_app.c` | 8 组 36 项断言，覆盖正常/异常路径 |

### 工作流（对应 Skill Core Workflow）

1. 分析约束：STM32F4、64KB RAM/512KB Flash 量级、电池供电、60s 采样间隔
2. 设计架构：裸机超级循环（不引入 FreeRTOS），RTC 唤醒 + Stop 模式
3. 实现驱动：HAL 抽象 + TMP102 驱动 + 电源管理
4. 验证实现：`-Wall -Werror` 零警告、clang 静态分析零告警、36 项测试全通过
5. 优化资源：整数运算（无浮点）、静态分配（无 malloc）、`-Os`、外设门控
6. 测试验证：主机模拟覆盖全部逻辑路径；硬件在环计划见第 6 节

## 2. 关键代码

### 2.1 低功耗主循环（app.c）

```
初始化 → 喂狗 → 读电池 → 采样(I2C) → 校验 → 组帧 → UART发送 → 喂狗 → RTC唤醒+Stop → (唤醒) → 循环
```

- 不使用 FreeRTOS：本设备只有一个周期任务，RTOS 会额外占用约 4-8KB Flash 和 1-2KB RAM，
  且增加调度抖动。裸机超级循环 + RTC 唤醒更符合资源约束。
- 两次喂狗：周期开始和发送完成后各一次，任何步骤卡死都会被 IWDG 复位。

### 2.2 温度读取（temp_sensor.c）

- TMP102 配置为关断模式，每次用 OS 位触发单次转换（转换完自动断电），典型电流 <1µA
- 两次读取做一致性校验（差值 ≤0.1°C），防止 I2C 毛刺导致错误数据
- 全部整数运算：原始值 → 0.01°C 用 `(raw * 25) / 4`，不使用浮点
- I2C 每次操作带 50ms 超时，失败后总线恢复 + 最多 3 次重试

### 2.3 电源管理（power_mgr.c）

| 电池状态 | 电压范围 | 采样间隔 |
|----------|----------|----------|
| 满电 | ≥3700mV | 60s |
| 良好 | 3400-3700mV | 60s |
| 低电 | 3200-3400mV | 300s（5分钟） |
| 临界 | <3200mV | 600s（10分钟） |

- 采样间隔 >1s 一律使用 Stop 模式（RTC 唤醒），符合 Skill 低功耗最佳实践
- Stop 前关闭 I2C/UART/ADC 时钟，唤醒后恢复 PLL 和外设

### 2.4 通信帧格式

```
[0xAA][0x55][温度高][温度低][电池高][电池低][状态][异或校验]
```
共 8 字节，9600 波特 UART，发送耗时约 8.3ms。

## 3. 资源预算

### Flash（估算，ARM Thumb-2 `-Os`）

| 模块 | 估算 Flash |
|------|-----------|
| 应用层 app.c | ~0.8 KB |
| 温度驱动 temp_sensor.c | ~0.6 KB |
| 电源管理 power_mgr.c | ~0.2 KB |
| 目标 HAL hal_target.c | ~2.5 KB |
| 启动代码 + C 库（精简） | ~2.0 KB |
| **合计** | **~6.1 KB** |

### RAM

| 项目 | 大小 |
|------|------|
| 全局/静态变量（帧缓冲、状态） | ~64 B |
| 主栈 | 512 B（预留） |
| **合计** | **~576 B** |

无动态内存分配（无 malloc/free），无堆。

### 功耗估算（单周期，3.7V 锂电池）

| 阶段 | 时长 | 电流 | 电荷 |
|------|------|------|------|
| 唤醒 + 时钟恢复 | ~1ms | ~12mA | 12µC |
| I2C 采样（含 40ms 转换等待） | ~45ms | ~5mA（含传感器） | 225µC |
| UART 发送 | ~9ms | ~8mA | 72µC |
| Stop 模式 | 59945ms | ~10µA（典型） | 600µC |
| **单周期总电荷** | | | **~909µC** |

平均电流 ≈ 909µC / 60s ≈ **15.2µA**
2000mAh 电池理论续航 ≈ 2000000µAh / 15.2µA ≈ **131000 小时 ≈ 15 年**
（实际受自放电和漏电流影响，预计 3-5 年）

## 4. 异常处理

| 异常场景 | 检测方式 | 处理策略 |
|----------|----------|----------|
| I2C 超时/总线挂死 | 每次 I2C 事务 50ms 超时 | 总线恢复（9 时钟脉冲 + 外设复位）+ 最多 3 次重试 |
| 传感器持续无响应 | 重试 3 次仍失败 | 上报 SENSOR_ERR，错误计数 +1，下周期继续 |
| 连续 10 次采样失败 | 软件错误计数器 | 请求系统复位（NVIC_SystemReset） |
| 温度越界（<-40 或 >125°C） | 范围校验 | 上报 RANGE_ERR，温度字段填 0x8000 无效值 |
| 两次读数不一致 | 差值 >0.1°C | 上报 SENSOR_ERR，本周期数据丢弃 |
| UART 发送超时 | 100ms 超时 | 本帧丢弃，错误计数 +1，不阻塞下周期 |
| 程序跑飞/死锁 | IWDG 独立看门狗（4s 超时） | 硬件自动复位，重启后状态字节标记 WDG_RESET |
| 电池低电 | ADC 电压检测 | 降低采样频率，状态字节标记 BATT_LOW/CRIT |
| 非 RTC 误唤醒 | 唤醒后检查 RTC 标志 | 直接返回处理，不影响周期 |

## 5. 约束导致的方案变化

| 新增约束 | 对方案的影响 |
|----------|-------------|
| 不新增非必要依赖 | 不引入 FreeRTOS（改用裸机超级循环）；不引入第三方 I2C/Crc 库；仅用 C99 标准库和编译器内置；Makefile 不依赖任何外部包管理器 |
| 不改动无关文件 | 所有新文件仅在 `temp_logger_fw/` 目录内；未修改 Skill 包任何文件；未修改系统文件 |
| 本地可重复验证命令 | 新增主机模拟层（hal_mock.c）使全部业务逻辑可在 macOS/Linux 上用 gcc/clang 编译运行；`make verify` 一条命令完成静态分析 + 编译 + 测试 |
| 外部账号只做模拟 | 未使用任何云服务/外部账号；温度传感器、UART、I2C 全部在主机进程内模拟；目标硬件交叉编译仅做工具链存在性检查，不实际链接（缺 arm-none-eabi-gcc 时明确报告） |

## 6. 硬件在环（HIL）验证计划

以下为上真实硬件后的验证步骤，当前环境无硬件，仅提供计划和主机侧已完成的部分。

### 6.1 已完成（主机模拟）

```bash
cd temp_logger_fw
make verify
```
- clang 静态分析：0 告警
- `-Wall -Wextra -Werror -Wpedantic -Wconversion`：0 警告
- 36 项断言全部通过（正常采样、I2C 故障恢复、持续故障复位、越界、不稳定、低电量、多周期、校验和）

### 6.2 目标编译（需安装工具链）

```bash
# 安装 ARM 工具链后
brew install --cask gcc-arm-embedded
make target
# 或手动：
arm-none-eabi-gcc -std=c11 -Wall -Wextra -Werror -Os \
  -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
  -DSTM32_TARGET -Iinc -ffunction-sections -fdata-sections \
  -Wl,--gc-sections -Tstm32f4.ld \
  src/*.c -o firmware.elf
arm-none-eabi-size firmware.elf
```

### 6.3 HIL 测试项（需 STM32F4 开发板 + TMP102 + 调试器）

| 编号 | 测试项 | 工具/方法 | 通过标准 |
|------|--------|-----------|----------|
| HIL-1 | 时钟树配置 | 示波器测 MCO 引脚 | SYSCLK = 168MHz ±0.1% |
| HIL-2 | I2C 时序 | 逻辑分析仪抓 SCL/SDA | 100kHz ±5%，START/STOP/ACK 正确 |
| HIL-3 | 温度精度 | 恒温槽对比标准温度计 | ±0.5°C（-10~85°C） |
| HIL-4 | Stop 模式电流 | 精密电源/万用表（µA 档） | Stop 电流 <20µA |
| HIL-5 | RTC 唤醒精度 | 示波器/逻辑分析仪测唤醒间隔 | 60s ±0.5% |
| HIL-6 | 平均电流 | 库仑计或电源分析仪 | <20µA 平均 |
| HIL-7 | 看门狗复位 | 调试器手动卡死任务 | 4s 内复位，重启后 WDG_RESET 位置位 |
| HIL-8 | I2C 总线恢复 | 手动拉低 SDA 模拟挂死 | 9 时钟脉冲后恢复通信 |
| HIL-9 | UART 帧格式 | 逻辑分析仪/USB 转串口 | 8 字节帧，9600 8N1，校验和正确 |
| HIL-10 | 电池低电自适应 | 可调电源模拟电压下降 | 3.3V 时切 5min 间隔，3.0V 时切 10min |
| HIL-11 | ISR 延迟 | 示波器测 GPIO 翻转 | RTC ISR <5µs |
| HIL-12 | 栈水位 | 调试器读栈填充图案 | 剩余栈 >128 字节 |
| HIL-13 | 长稳测试 | 连续运行 72 小时 | 无复位、无丢帧、无看门狗超时 |

### 6.4 寄存器位域确认

`hal_target.c` 中的寄存器值参照 Skill 参考代码编写，上硬件前必须对照 STM32F4 参考手册
（RM0090）确认以下位域：I2C CCR/TRISE 计算、RTC WUTR 重装值、PWR LPDS/PDDS 位、
RCC 时钟配置。这是 Skill Core Workflow 第 4 步明确要求的。

## 7. 验证证据

### 7.1 可重复验证命令

```bash
cd temp_logger_fw
make verify    # = clang静态分析 + -Wall -Werror编译 + 36项测试
```

### 7.2 本次运行结果

```
--- clang 静态分析 ---
静态分析完成（0 error, 0 warning）

--- 编译 ---
cc -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow -Wcast-align ...
（4 个目标文件 + 测试二进制，0 警告）

--- 测试 ---
===== 温度采集固件主机验证 =====
[测试1] 正常采样周期 ............ 12 PASS
[测试2] I2C 瞬时故障后恢复 ......  4 PASS
[测试3] I2C 持续故障导致系统复位  2 PASS
[测试4] 温度越界检测 ............  3 PASS
[测试5] 读数不稳定检测 ..........  2 PASS
[测试6] 低电量自适应 ............  5 PASS
[测试7] 多周期循环稳定性 ........  4 PASS
[测试8] 校验和纯函数 ............  4 PASS
===== 结果：36 通过，0 失败 =====
```

### 7.3 未完成项（如实报告）

- **ARM 交叉编译未执行**：本机未安装 `arm-none-eabi-gcc`，`make target` 明确报告缺失。
  安装工具链后可执行，但还需 STM32F4 头文件和链接脚本（未提供，属于外部依赖）。
- **硬件在环测试未执行**：无 STM32 开发板和 TMP102 实物，HIL 计划仅提供步骤。
- **hal_target.c 未经过编译器验证**：该文件仅在 `STM32_TARGET` 宏定义时编译，
  主机测试不覆盖；寄存器位域需上硬件确认。
- **cppcheck 未运行**：本机未安装 cppcheck，已用 clang 静态分析器（`--analyze`）替代，
  覆盖空指针解引用、死存储、未初始化变量等检查。

## 8. 实际读取的 Skill 文件及影响

### 读取的文件（相对路径）

| 文件 | 是否影响执行 |
|------|-------------|
| `embedded-systems/SKILL.md` | 是——定义了核心工作流、MUST/MUST NOT 约束、输出模板 |
| `embedded-systems/references/power-optimization.md` | 是——Stop 模式策略、RTC 唤醒、外设门控、ADC 低功耗、电池自适应 |
| `embedded-systems/references/microcontroller-programming.md` | 是——GPIO/定时器/I2C/UART/ADC/IWDG 寄存器配置模式、低功耗模式 |
| `embedded-systems/references/communication-protocols.md` | 是——I2C 带超时读写、UART 中断缓冲、总线恢复、CRC/校验建议 |
| `embedded-systems/references/memory-optimization.md` | 是——静态分配、const 放 Flash、最小数据类型、`-Os`/`--gc-sections`、_Static_assert |
| `embedded-systems/references/rtos-patterns.md` | 部分——参考后决定不使用 FreeRTOS（单周期任务无需 RTOS），但采纳了短 ISR、任务通知思想 |

### 实际影响执行的 SKILL.md 规则

1. **Core Workflow 第 4 步**：用 `-Wall -Werror` 编译 + 静态分析，零警告零告警才通过
2. **MUST: volatile**：`g_error_count`、`g_app_status` 等 ISR/主循环共享变量声明为 `volatile`
3. **MUST: 短 ISR**：RTC 唤醒中断仅清标志，不做处理
4. **MUST: 看门狗**：IWDG 4s 超时，周期开始和结束各喂一次
5. **MUST: 同步原语**：I2C 总线访问通过 HAL 串行化；临界区接口预留
6. **MUST: 记录资源使用**：第 3 节 Flash/RAM/功耗预算
7. **MUST: 处理所有错误条件**：第 4 节异常处理表，I2C/UART/ADC/看门狗全覆盖
8. **MUST: 考虑时序和抖动**：RTC 唤醒而非 SysTick 延时，`vTaskDelayUntil` 思想用于周期精确
9. **MUST NOT: ISR 中阻塞**：ISR 无循环等待
10. **MUST NOT: 无边界动态分配**：全部静态分配，无 malloc
11. **MUST NOT: 跳过临界区保护**：hal_critical_enter/exit 接口
12. **MUST NOT: 无 FPU 意识用浮点**：全部整数运算（0.01°C 单位），即使 M4F 有 FPU 也不用
13. **MUST NOT: 硬编码硬件值**：全部集中在 bsp_config.h
14. **MUST NOT: 忽略功耗**：Stop 模式、外设门控、单次转换、降频策略
15. **Output Template**：按要求提供了硬件初始化、驱动实现、应用代码、资源摘要、时序优化说明
