#!/usr/bin/env bash
# terminal-tools-foundations 前后台执行方案 —— 可重复验证脚本
# 依赖：macOS 自带 bash / python3 / curl / lsof（系统预装，不新增任何依赖）
# 用法：bash verify_plan.sh

PASS=0; FAIL=0
ok(){   echo "[通过] $1"; PASS=$((PASS+1)); }
bad(){  echo "[失败] $1"; FAIL=$((FAIL+1)); }

WORK="$(mktemp -d)/term-demo"
mkdir -p "$WORK"
PORT=23456
LOG="$WORK/server.log"
SRV_PID=""

cleanup(){
  if [ -n "$SRV_PID" ] && kill -0 "$SRV_PID" 2>/dev/null; then
    kill "$SRV_PID" 2>/dev/null          # 先 SIGTERM（礼貌停止，shell 退出码 143）
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      kill -0 "$SRV_PID" 2>/dev/null || break
      sleep 0.3
    done
    kill -0 "$SRV_PID" 2>/dev/null && kill -9 "$SRV_PID" 2>/dev/null  # 兜底 SIGKILL（137）
  fi
  rm -rf "$(dirname "$WORK")"
}
trap cleanup EXIT

echo "===== 1. 短命令（前台）====="
if python3 --version >/dev/null 2>&1; then ok "python3 可用"; else bad "python3 不可用"; fi
echo "verify-ok" > "$WORK/index.html"
if [ -f "$WORK/index.html" ]; then ok "前台写文件成功"; else bad "写文件失败"; fi

echo "===== 2. 启动长时间服务（后台）====="
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  bad "端口 $PORT 被占用，请更换端口"; exit 1
fi
# 直接以后台进程启动（不包子 shell），$! 即真实 python3 PID，避免孤儿进程
python3 -m http.server $PORT --directory "$WORK" >"$LOG" 2>&1 &
SRV_PID=$!
echo "后台服务 PID=$SRV_PID"
for _ in $(seq 1 25); do
  curl -s -m 1 "http://127.0.0.1:$PORT/index.html" >/dev/null 2>&1 && break
  sleep 0.2
done
if curl -s -m 2 "http://127.0.0.1:$PORT/index.html" | grep -q "verify-ok"; then
  ok "后台服务响应正常（PID=$SRV_PID）"
else
  bad "后台服务无响应"; exit 1
fi

echo "===== 3. 会话管理与日志查看 ====="
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then ok "端口 $PORT 处于监听状态"; else bad "端口未监听"; fi
curl -s "http://127.0.0.1:$PORT/missing" -o /dev/null
sleep 0.3
if grep -q "GET /index.html" "$LOG"; then ok "日志记录了访问请求"; else bad "日志未记录请求"; fi
if grep -q "404" "$LOG"; then ok "日志记录了 404（异常请求可追溯）"; else bad "日志未记录 404"; fi

echo "===== 4. 语义退出码（grep 退出码 1 不是错误）====="
grep "verify-ok" "$WORK/index.html" >/dev/null
if [ $? -eq 0 ]; then ok "grep 有匹配退出码 0"; else bad "grep 有匹配应为 0"; fi
grep "不存在xyz" "$WORK/index.html" >/dev/null
if [ $? -eq 1 ]; then ok "grep 无匹配退出码 1（语义：无匹配，非错误）"; else bad "grep 无匹配应为 1"; fi

echo "===== 5. 安全停止 ====="
kill "$SRV_PID" 2>/dev/null
for _ in $(seq 1 20); do
  kill -0 "$SRV_PID" 2>/dev/null || break
  sleep 0.3
done
if ! kill -0 "$SRV_PID" 2>/dev/null; then
  ok "SIGTERM 后进程已退出"
else
  bad "SIGTERM 未生效，尝试 SIGKILL"; kill -9 "$SRV_PID" 2>/dev/null
fi
SRV_PID=""
sleep 0.5
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then bad "端口仍被占用"; else ok "端口 $PORT 已释放"; fi
if curl -s -m 2 "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then bad "服务仍可访问"; else ok "服务已不可访问"; fi

echo ""
echo "===== 结果：通过 $PASS，失败 $FAIL ====="
[ "$FAIL" -eq 0 ]
