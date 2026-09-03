# add-mnemon Skill 执行报告

> 执行日期：2026-08-12
> Skill 来源：用户上传的 add-mnemon.zip
> 执行环境：macOS，工作目录非 NanoClaw 项目，Docker 不可用

---

## 一、Skill 真实能力边界（与题目假设的冲突说明）

`add-mnemon` 是一个**容器镜像改造 Skill**，面向名为 NanoClaw 的 agent 运行项目。它的全部职责是：

1. 在 `container/Dockerfile` 中添加一层，从 GitHub Releases 下载并安装 `mnemon` 二进制；
2. 在 `container/entrypoint.sh` 的 `set -e` 之后插入一行 `mnemon setup --target claude-code --yes --global`，使每次容器启动时注册 Claude Code 记忆钩子；
3. 将两个结构守卫测试（vitest）复制到 `src/` 目录，防止后续升级时误删安装层或入口行；
4. 重建镜像、重启服务、验证钩子注册与记忆召回。

`mnemon` 本身是一个基于图的持久化记忆工具：在 agent 响应前自动唤起相关历史上下文，在每轮对话后自动存储新见解。记忆写入容器内 `/home/node/.claude/mnemon/`，映射到宿主机 per-agent-group 的 `.claude/` 挂载目录，容器重启后保留。

### 题目假设与 SKILL.md 的冲突

| 题目假设 | SKILL.md 实际情况 | 处理方式 |
|---|---|---|
| 表格分类"个人效率" | Skill 属于 DevOps/容器配置类，修改 Dockerfile 与 entrypoint | 以文件规则为准，不按个人效率工具扩张 |
| 信息记忆、承诺追踪、阶段复盘 | 仅提供"对话上下文自动记忆与召回"；**无承诺追踪、无阶段复盘功能** | 不编造不存在的功能 |
| 每天维护不超过 15 分钟 | 安装后钩子自动运行，**无每日维护概念**；仅在升级版本或重置记忆时需人工操作 | 说明实际运维频率 |
| 旧资料结构混乱，需要迁移 | Skill **不提供任何旧资料导入/迁移机制**；mnemon 通过对话自动积累记忆，无批量导入入口 | 不提供虚构迁移步骤 |
| 给出模板 | Skill **未提供任何模板文件** | 不编造模板 |
| 一周试运行计划 | Skill 提供的是安装后验证步骤（Phase 3），**无试运行计划框架** | 基于 SKILL.md 验证步骤给出"安装验证计划"，不冒充个人效率试运行 |

---

## 二、实际执行情况（Phase 1 预检）

### 已完成

| 检查项 | SKILL.md 要求 | 实际结果 |
|---|---|---|
| 读取 Skill 文件 | SKILL.md、REMOVE.md、两个测试文件 | 已全部读取（见第四节） |
| 检查是否已应用 | `grep -q 'MNEMON_VERSION' container/Dockerfile` | 无法执行——`container/Dockerfile` 不存在 |
| 检查 provider 兼容性 | `grep -H '"provider"' groups/*/container.json` | 无法执行——`groups/` 目录不存在 |
| 查询最新版本 | `curl .../releases/latest \| grep tag_name` | **已执行，最新版本为 `v0.2.0`**（SKILL.md 示例为 v0.1.1，实际应用时应以 v0.2.0 为准） |
| 工具链检查 | docker、pnpm、curl、systemctl/launchctl | pnpm 10.34.5 可用、curl 可用、launchctl 可用；**Docker 未安装或不可用** |

### 未执行及原因

| 阶段 | 步骤 | 阻断原因 |
|---|---|---|
| Phase 2.1 | 修改 `container/Dockerfile` | 当前目录不是 NanoClaw 项目，该文件不存在 |
| Phase 2.2 | 修改 `container/entrypoint.sh` | 同上 |
| Phase 2.3 | 复制测试到 `src/` 并运行 vitest | `src/` 目录不存在；且无待修改的源文件供测试断言 |
| Phase 2.4 | `./container/build.sh` + `docker run` 冒烟测试 | `container/build.sh` 不存在；Docker 不可用 |
| Phase 3 | systemctl/launchctl 重启、docker logs/exec 验证 | 无 NanoClaw 服务、无 Docker 容器 |

**需要你确认/提供的事项：**
1. NanoClaw 项目的实际路径（当前工作目录 `/Users/bytedance/Doubao/chats/2026-08-12/new-chat-532` 不是该项目）；
2. 该项目是否运行默认 Claude provider（SKILL.md 第 12 行要求先确认 `groups/*/container.json` 中 `"provider"` 为 `claude` 或缺省，其他 provider 下钩子不会触发）；
3. 目标主机是否已安装并运行 Docker；
4. 是否允许从 GitHub（`github.com/mnemon-dev/mnemon`、`api.github.com`）下载二进制——见第三节合规说明。

---

## 三、敏感信息与外部服务说明

按你的要求"敏感信息不能上传外部服务"，对照 SKILL.md 逐项说明：

1. **记忆数据存储位置**：SKILL.md 第 52-55 行、第 134-143 行明确，mnemon 数据写入容器内 `/home/node/.claude/mnemon/`，映射到宿主机 `.claude/` 挂载，**为本地存储**，SKILL.md 未描述任何将记忆内容上传外部服务的行为。
2. **安装期网络请求**：Phase 1 查询版本号（`api.github.com`）和 Phase 2 下载二进制（`github.com/.../releases/download/...`）均为访问 GitHub 公开资源的 GET 请求，**不上传任何用户数据或对话内容**。本次预检中执行的版本查询仅获取了公开的 tag_name 字段。
3. **第三方二进制风险（需你确认）**：mnemon 是以 GitHub Release 二进制形式安装的第三方程序，SKILL.md 未描述其运行时网络行为。若你的对话涉及高敏感信息，建议在应用前：
   - 在网络隔离环境中审计该二进制是否有外联行为；或
   - 确认 mnemon 官方文档说明其纯本地运行后再用于敏感场景。
4. **重置/清除**：如需清除全部记忆，SKILL.md 第 143 行说明：停止容器后删除宿主机挂载路径下的 `mnemon/` 子目录即可。REMOVE.md 第 51-58 行也给出了相同方法。

---

## 四、实际读取的 Skill 文件（相对路径）

相对于解压根目录 `add-mnemon-extracted/add-mnemon/`：

1. `SKILL.md` — 主安装流程（Phase 1-3、存储、故障排查）
2. `REMOVE.md` — 卸载流程
3. `mnemon-dockerfile.test.ts` — Dockerfile 结构守卫测试
4. `mnemon-entrypoint.test.ts` — entrypoint 结构守卫测试

---

## 五、影响交付结果的 SKILL.md 规则（至少一条）

**规则：Provider 兼容性检查（SKILL.md 第 10-18 行）。**

该规则要求在应用前确认 agent group 的 `container.json` 中 provider 为默认 Claude（缺省或 `"claude"`）；若为其他 provider（如 `"opencode"`），该 group 会自行派生进程、从不调用 `claude` CLI，`mnemon setup` 注册的钩子**不会触发**，等于白装。

这条规则直接影响交付结果：在未确认 provider 之前，不能承诺"安装后记忆功能一定生效"。本次预检因 `groups/` 目录不存在而无法完成该检查，因此本报告只能给出"在满足前提条件后的安装流程"，不能声明功能已验证可用。

另一条同样影响结果的规则是**幂等性设计**（第 28 行、第 59 行、REMOVE.md 第 3 行）：每个步骤可重复执行、自动跳过已完成内容——这意味着在真实项目中可以安全重跑，无需担心重复插入。

---

## 六、最小流程（严格基于 SKILL.md，未扩张职责）

以下为在**真实 NanoClaw 项目根目录**中执行的最小步骤。版本号请使用本次预检确认的 `v0.2.0`（将下方 `0.2.0` 填入 ARG，下载 URL 中 `${MNEMON_VERSION}` 会自动展开为 `0.2.0`）。

### 步骤 0：前置确认（不可跳过）

```bash
# 确认在 NanoClaw 项目根目录
test -f container/Dockerfile && test -f container/entrypoint.sh && echo "项目结构正常" || echo "不在 NanoClaw 项目根目录"

# 确认 provider 为 Claude（无输出或输出 "claude" 才可继续）
grep -H '"provider"' groups/*/container.json 2>/dev/null
```

### 步骤 1：Dockerfile 安装层

在 `container/Dockerfile` 的 `# ---- Bun runtime` 段**之前**插入（若 `grep -q 'MNEMON_VERSION' container/Dockerfile` 已命中则跳过）：

```dockerfile
# ---- mnemon — persistent agent memory ----------------------------------------
ARG MNEMON_VERSION=0.2.0
RUN ARCH=$(dpkg --print-architecture) && \
    curl -fsSL "https://github.com/mnemon-dev/mnemon/releases/download/v${MNEMON_VERSION}/mnemon_${MNEMON_VERSION}_linux_${ARCH}.tar.gz" \
    | tar -xz -C /usr/local/bin mnemon && \
    chmod +x /usr/local/bin/mnemon

ENV MNEMON_DATA_DIR=/home/node/.claude/mnemon
```

### 步骤 2：entrypoint 启动钩子

在 `container/entrypoint.sh` 的 `set -e` 之后、捕获 stdin 的 `cat` 之前插入（若 `grep -q 'mnemon setup' container/entrypoint.sh` 已命中则跳过）：

```bash
mnemon setup --target claude-code --yes --global >/dev/stderr 2>&1
```

`>/dev/stderr 2>&1` 必须保留——SKILL.md 第 82 行说明，这避免 mnemon 输出干扰宿主机与 agent-runner 之间的 JSON stdin 握手。

### 步骤 3：复制并运行守卫测试

```bash
cp .claude/skills/add-mnemon/mnemon-dockerfile.test.ts src/mnemon-dockerfile.test.ts
cp .claude/skills/add-mnemon/mnemon-entrypoint.test.ts src/mnemon-entrypoint.test.ts
pnpm exec vitest run src/mnemon-dockerfile.test.ts src/mnemon-entrypoint.test.ts
```

### 步骤 4：重建镜像并冒烟测试

```bash
./container/build.sh
docker run --rm --entrypoint mnemon nanoclaw-agent:latest --version
```

### 步骤 5：重启服务

```bash
# macOS
launchctl kickstart -k gui/$(id -u)/$(launchd_label)
# Linux
# systemctl --user restart $(systemd_unit)
```

### 步骤 6：验证钩子与记忆

```bash
# 确认 setup 已执行
docker logs $(docker ps --filter name=nanoclaw-v2 --format '{{.Names}}' | head -1) 2>&1 | grep -i mnemon

# 确认钩子写入 settings.json
docker exec $(docker ps --filter name=nanoclaw-v2 --format '{{.Names}}' | head -1) \
  cat /home/node/.claude/settings.json | grep -A5 mnemon
```

随后与 agent 对话，开新会话引用上一会话内容，确认上下文自动召回。

---

## 七、关于"迁移步骤"和"模板"的说明

- **迁移步骤**：SKILL.md 与 REMOVE.md 均未提供旧资料导入或迁移功能。mnemon 的记忆通过日常对话自动积累，无批量导入命令。若你有"旧资料结构混乱"需要整理，这**超出 add-mnemon 的能力边界**，需要使用其他工具或 Skill，不能由本 Skill 完成。
- **模板**：Skill 包内无任何模板文件，本报告不编造模板。
- **卸载**：如需回滚，按 `REMOVE.md` 执行——删除 Dockerfile 安装层、删除 entrypoint 中的 setup 行、删除两个测试文件、重建重启、可选删除 `mnemon/` 数据目录。所有步骤幂等。

---

## 八、安装后验证计划（基于 SKILL.md Phase 3，非"个人效率试运行"）

SKILL.md 没有"一周试运行"框架，以下是严格基于其 Phase 3 验证步骤整理的**安装验证清单**，用于确认功能真正生效：

| 时间点 | 验证项 | 对应 SKILL.md 位置 |
|---|---|---|
| 安装后即刻 | `docker run --rm --entrypoint mnemon nanoclaw-agent:latest --version` 能输出版本号 | 第 100 行 |
| 首次容器启动后 | `docker logs ... \| grep -i mnemon` 有 setup 输出，无报错 | 第 120 行 |
| 首次容器启动后 | `settings.json` 中存在 mnemon 钩子配置 | 第 126-128 行 |
| 首次对话后 | `$MNEMON_DATA_DIR` 目录非空，有记忆数据写入 | 第 156 行 |
| 容器重启后 | 新会话能自动召回上一会话上下文，无需重述 | 第 132 行 |
| 升级版本时 | 更新 `MNEMON_VERSION` 后重建，两个 vitest 守卫测试通过 | 第 88-94 行 |
| 需要重置时 | 停止容器、删除宿主机 `mnemon/` 子目录，重启后记忆清空 | 第 143 行 |

日常运维量：安装成功后**无需每日维护**，钩子自动触发。仅在版本升级（改 ARG、重建镜像）或需重置记忆时有人工操作，单次耗时远低于 15 分钟。

---

## 九、待确认事项汇总

1. NanoClaw 项目根目录路径；
2. 目标 agent group 的 provider 是否为默认 Claude；
3. Docker 是否可用；
4. 是否允许从 GitHub 下载第三方二进制，以及是否需要先行网络行为审计；
5. 若确有"旧资料整理/承诺追踪/阶段复盘"需求，需另寻对应工具——这些不在 add-mnemon 职责范围内。
