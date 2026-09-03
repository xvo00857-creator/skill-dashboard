# 权限清单

## 文件系统
| 路径 | 权限 |
|------|------|
| todos.json | 读 |
| summary_output.md | 写 |
| .backup/ | 读写 |

## 外部服务（未配置，占位符）
- 飞书webhook: <FEISHU_WEBHOOK_URL>
- 邮件SMTP: <SMTP_HOST>

## 不需要
- root/管理员、网络、数据库、系统配置修改

## release-skills原始权限（本演示未使用）
- git commit/tag/push、gh CLI、包管理器、远程仓库写权限
