# 失败回滚方案

## 自动回滚
1. 写入前备份：每次覆盖 summary_output.md 前，旧文件备份到 .backup/summary_时间戳.md.bak
2. 写入失败：输出错误+提示备份路径+exit 1，不删除旧文件
3. 用户取消：Step 8 确认时选取消，立即退出，不做任何变更（借鉴 SKILL.md "stop rather than creating"）

## 手动回滚
```bash
ls -lt .backup/
cp .backup/summary_XXXXXXXX_XXXXXX.md.bak summary_output.md
```

## 完全重置
```bash
rm summary_output.md && rm -rf .backup/
```

## 与 release-skills 对比
| 场景 | release-skills | 本脚本 |
|------|---------------|--------|
| dry-run | 不做变更 | 同 |
| 用户取消 | 不创建commit/tag | 不写入文件 |
| 已推送tag | git push --delete | 不涉及 |
| 已发布Release | gh release delete | 不涉及 |

## 数据安全
- todos.json 只读不写
- 输出覆盖前自动备份
- 所有人员名为模拟数据
