# 验证证据（TEST_RESULTS）

运行环境：Python 3.9.6，macOS，仅使用标准库。
运行目录：`weekly-adobe-report/`
固定运行时刻参数：`--now 2026-08-12T09:00:00+08:00`（保证结果可重复）

## 1. 可重复验证命令

```bash
# 进入目录
cd weekly-adobe-report

# 正常路径
python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00
echo "退出码: $?"   # 期望 0

# 异常场景（逐个）
python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00 --inject auth_fail
echo "退出码: $?"   # 期望 1（E_AUTH，流程暂停）

python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00 --inject empty
echo "退出码: $?"   # 期望 0（E_EMPTY，生成空数据摘要）

python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00 --inject bad_data
echo "退出码: $?"   # 期望 0（E_DATA，跳过坏记录继续）

python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00 --inject exec_fail
echo "退出码: $?"   # 期望 2（E_EXEC，重试后终止）

python3 simulate_weekly_report.py --now 2026-08-12T09:00:00+08:00 --inject notify_fail
echo "退出码: $?"   # 期望 2（E_NOTIFY，重试后落盘降级）

# 语法检查（不执行）
python3 -m py_compile simulate_weekly_report.py && echo "语法 OK"

# 确认无第三方依赖（只应看到 argparse/collections/datetime/json/os/sys/time）
python3 -c "import ast; t=ast.parse(open('simulate_weekly_report.py').read()); print(sorted({n.names[0].name for n in ast.walk(t) if isinstance(n,ast.Import)} | {n.module.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom) and n.module}))"
```

## 2. 本次实际运行结果

| 场景 | 命令 | 实际退出码 | 期望退出码 | 结果 |
|------|------|-----------|-----------|------|
| 正常路径 | 无 --inject | 0 | 0 | 通过 |
| E_AUTH | --inject auth_fail | 1 | 1 | 通过 |
| E_EMPTY | --inject empty | 0 | 0 | 通过 |
| E_DATA | --inject bad_data | 0 | 0 | 通过 |
| E_EXEC | --inject exec_fail | 2 | 2 | 通过 |
| E_NOTIFY | --inject notify_fail | 2 | 2 | 通过 |

## 3. 正常路径关键输出

- 周次：2026-W33（2026-08-10 ~ 2026-08-17，Asia/Shanghai）
- 资源总数：8
- 本周新增：4；本周修改：2
- 类型分布：pdf=4, image=3, archive=1
- 总大小：24,222,720 字节
- 贡献者 Top3：alice@example.com(3)、bob@example.com(3)、carol@example.com(2)
- 异常：1 条（1 项 archived 状态提示）
- 产物：
  - `output/run_20260812_090000.log`（分步日志）
  - `output/summary_2026-W33.json`（摘要 JSON）
  - `output/notification_2026-W33.txt`（通知内容，未真实发送）

## 4. 依赖与安全确认

- 脚本仅 import：argparse、collections、datetime、json、os、sys、time —— 全部 Python 标准库。
- 未执行 `pip install`，未新增任何依赖。
- 脚本不发起任何网络请求；不读取/写入本目录之外的文件（仅写 `output/`）。
- 不持有、不打印任何 Adobe 凭据或 token；所有工具 slug 以 `MOCK_` 前缀标识。
