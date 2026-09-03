// native-fetch-demo.mjs
// 受约束演示：仅用 Node 内置模块，在 127.0.0.1 回环地址起本地 mock 服务，不访问外部网络。
// 模式实现严格对应 native-data-fetching SKILL.md：
//   - ApiError + fetchWithErrorHandling  -> SKILL.md §3
//   - fetchWithRetry 指数退避            -> SKILL.md §3
//   - AbortController 取消               -> SKILL.md §7
//   - in-flight 去重（对应 React Query 去重思想） -> SKILL.md §2/Decision Tree
//   - EXPO_PUBLIC_API_URL 预检           -> SKILL.md §6
//   - 人工确认点（写操作）               -> SKILL.md Limitations
import http from 'node:http';

// ---------- 1. 预检 ----------
function precheck(baseUrl) {
  const issues = [];
  if (!baseUrl) issues.push('BASE_URL 未配置（对应 EXPO_PUBLIC_API_URL 缺失）');
  if (typeof fetch !== 'function') issues.push('运行时不支持全局 fetch（需 Node 18+ 或 React Native）');
  return issues;
}

// ---------- 2. 类型化错误（SKILL.md §3） ----------
class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

// ---------- 3. 带错误处理的 fetch（SKILL.md §3，补充 AbortError 识别以配合 §7） ----------
async function fetchWithErrorHandling(url, options = {}) {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new ApiError(error.message || 'Request failed', response.status, error.code);
    }
    return response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error && error.name === 'AbortError') {
      throw new ApiError('Request aborted', 0, 'ABORT_ERR');
    }
    // 网络错误（断网、超时等）
    throw new ApiError('Network error', 0, 'NETWORK_ERROR');
  }
}

// ---------- 4. 指数退避重试（SKILL.md §3） ----------
// 生产默认 backoffBaseMs = 1000，与 SKILL.md 一致；演示传入较小值以缩短耗时。
async function fetchWithRetry(url, options, retries = 3, backoffBaseMs = 1000) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fetchWithErrorHandling(url, options);
    } catch (error) {
      // 取消与业务 4xx 不重试
      if (error.code === 'ABORT_ERR') throw error;
      if (typeof error.status === 'number' && error.status >= 400 && error.status < 500
          && error.status !== 408 && error.status !== 429) {
        throw error;
      }
      if (i === retries - 1) throw error;
      const delay = Math.pow(2, i) * backoffBaseMs;
      await new Promise((r) => setTimeout(r, delay));
    }
  }
}

// ---------- 5. 幂等：in-flight 去重（对应 React Query 自动去重） ----------
const inflight = new Map();
function dedupedFetch(key, fn) {
  if (inflight.has(key)) return inflight.get(key);
  const p = Promise.resolve().then(fn).finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

// ---------- 6. 人工确认点（变更类请求需确认） ----------
function confirmMutation(action, confirmed) {
  if (!confirmed) {
    throw new ApiError(`变更操作需人工确认后执行: ${action}`, 0, 'CONFIRMATION_REQUIRED');
  }
}

// ---------- 本地 mock 服务（仅回环地址） ----------
function startMockServer() {
  let flakyAttempts = 0;
  const server = http.createServer((req, res) => {
    if (req.url === '/healthz' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true }));
    } else if (req.url === '/users/1' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ id: 1, name: '梅梅' }));
    } else if (req.url === '/users/flaky' && req.method === 'GET') {
      flakyAttempts += 1;
      if (flakyAttempts < 3) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ message: '服务器暂时不可用', code: 'EAGAIN' }));
      } else {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id: 'flaky', name: '重试成功', attempts: flakyAttempts }));
      }
    } else if (req.url === '/users/missing' && req.method === 'GET') {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ message: 'User not found', code: 'NOT_FOUND' }));
    } else if (req.url === '/slow' && req.method === 'GET') {
      setTimeout(() => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      }, 300);
    } else if (req.url === '/users' && req.method === 'POST') {
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ created: true }));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ message: 'Not Found' }));
    }
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)));
}

// ---------- 测试运行器 ----------
let passed = 0;
let failed = 0;
async function test(name, fn) {
  try {
    await fn();
    console.log(`  通过 - ${name}`);
    passed += 1;
  } catch (e) {
    console.log(`  失败 - ${name}: ${e.message}`);
    failed += 1;
  }
}

// ---------- 主流程 ----------
const server = await startMockServer();
const { port } = server.address();
const BASE_URL = `http://127.0.0.1:${port}`;
console.log(`本地 mock 服务已启动: ${BASE_URL}（回环地址，不访问外网）\n`);

try {
  // 预检
  console.log('[预检]');
  const badPrecheck = precheck('');
  await test('BASE_URL 缺失时被检出', () => {
    if (badPrecheck.length === 0) throw new Error('应检出 BASE_URL 缺失');
  });
  const okPrecheck = precheck(BASE_URL);
  await test('BASE_URL 与 fetch 均就绪时预检通过', () => {
    if (okPrecheck.length !== 0) throw new Error(`不应有问题: ${okPrecheck.join(';')}`);
  });
  const health = await fetchWithErrorHandling(`${BASE_URL}/healthz`);
  await test('连通性探测 /healthz 返回 ok', () => {
    if (!health.ok) throw new Error('健康检查失败');
  });

  // 基础请求与错误处理
  console.log('\n[请求与错误处理]');
  const user = await fetchWithErrorHandling(`${BASE_URL}/users/1`);
  await test('正常 GET 返回用户数据', () => {
    if (user.id !== 1 || user.name !== '梅梅') throw new Error('返回数据与预期不符');
  });
  await test('404 抛出 ApiError 且携带 status=404', async () => {
    try {
      await fetchWithErrorHandling(`${BASE_URL}/users/missing`);
      throw new Error('应抛出错误');
    } catch (e) {
      if (!(e instanceof ApiError)) throw new Error('应为 ApiError 类型');
      if (e.status !== 404 || e.code !== 'NOT_FOUND') throw new Error('status/code 不正确');
    }
  });

  // 重试
  console.log('\n[重试（指数退避）]');
  const flaky = await fetchWithRetry(`${BASE_URL}/users/flaky`, undefined, 3, 30);
  await test('500 连续两次后第三次成功（退避基数 30ms，生产为 1000ms）', () => {
    if (flaky.attempts !== 3) throw new Error(`应在第 3 次尝试成功，实际 attempts=${flaky.attempts}`);
  });

  // 幂等去重
  console.log('\n[幂等 / 去重]');
  let dupCalls = 0;
  const dupFn = async () => {
    dupCalls += 1;
    await new Promise((r) => setTimeout(r, 50));
    return fetchWithErrorHandling(`${BASE_URL}/users/1`);
  };
  const [r1, r2] = await Promise.all([
    dedupedFetch('GET /users/1', dupFn),
    dedupedFetch('GET /users/1', dupFn),
  ]);
  await test('并发相同 GET 只触发一次底层调用（in-flight 去重）', () => {
    if (dupCalls !== 1) throw new Error(`应只调用 1 次，实际 ${dupCalls} 次`);
    if (r1.id !== 1 || r2.id !== 1) throw new Error('返回数据不一致');
  });

  // 取消
  console.log('\n[请求取消]');
  const ac = new AbortController();
  const slowP = fetchWithErrorHandling(`${BASE_URL}/slow`, { signal: ac.signal });
  setTimeout(() => ac.abort(), 50);
  await test('AbortController 提前取消在途请求', async () => {
    try {
      await slowP;
      throw new Error('应被取消');
    } catch (e) {
      if (e.code !== 'ABORT_ERR') throw new Error(`应为 ABORT_ERR，实际 ${e.code}`);
    }
  });

  // 人工确认点
  console.log('\n[人工确认点]');
  await test('写操作未经确认被拦截（不发请求）', async () => {
    try {
      confirmMutation('POST /users', false);
      throw new Error('应被拦截');
    } catch (e) {
      if (e.code !== 'CONFIRMATION_REQUIRED') throw new Error('应为 CONFIRMATION_REQUIRED');
    }
  });
  await test('写操作经确认后执行成功', async () => {
    confirmMutation('POST /users', true);
    const created = await fetchWithErrorHandling(`${BASE_URL}/users`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: '新用户' }),
    });
    if (!created.created) throw new Error('应返回 created=true');
  });
} finally {
  server.close();
  console.log(`\n结果: ${passed} 通过, ${failed} 失败`);
  process.exitCode = failed === 0 ? 0 : 1;
}
