# 智能随行杯新品上市可执行方案

> 文档版本：v1.0（最小可验证版本）
> 生成日期：2026-08-26
> 输入依据：`product_brief.md`（唯一产品简报来源）
> 关联 Skill：`google-ads-api-quickstart`（Google Ads API 快速上手，分类：营销与增长）
> API 版本锚定：`[SYSTEM: Using Google Ads API version: v24 (Resolved from release notes)]`
> 说明：上述版本号因 Google Ads API Release Notes 官方 URL（`https://developers.google.com/google-ads/api/docs/release-notes.md.txt`）抓取失败，按 SKILL.md 离线回退规则取最后已知稳定版本 `v24`，非硬编码默认值。

---

## 0. 前提声明与输入校验

### 0.1 已确认信息（来自 product_brief.md）
| 项目 | 内容 |
|---|---|
| 产品名称 | 智能随行杯 |
| 目标用户 | 一二线城市通勤人群 |
| 核心卖点 | 12 小时保温、重量 280g、可拆洗杯盖 |
| 建议零售价 | 199 元 |
| 已确认素材 | 产品白底图、基础规格、品牌主色 #176B87 |

### 0.2 不适用输入
- `product_release_notes.md`：内容为"星河笔记 2.3"（一款 Markdown 笔记软件的版本发布说明），与智能随行杯无产品关联。本方案不引用其任何功能、兼容性或已知问题信息，避免跨产品虚构。

### 0.3 禁止编造项（严格遵守）
- 第三方检测结论（保温性能实测、食品接触材料安全认证等）
- 销量数据、预售数据、复购率
- 用户评价、口碑反馈、KOL 试用结论
- 竞品价格、竞品市场份额

### 0.4 结论与假设分离原则
- 本文档中**结论**均基于已确认信息或可验证逻辑推导。
- **假设**均以「假设：」前缀标注，并在第 8 节"待补项"中列出验证路径。
- 需要外部数据但当前无法获取的内容，一律列为待补项，不做数值填充。

---

## 1. 产品定位与上市目标

### 1.1 产品定位
面向一二线城市通勤人群的轻量保温随行杯，以"轻量 + 长保温 + 易清洁"为差异化组合，定价 199 元处于中端随行杯价格带。

### 1.2 上市目标（定性，不含虚构数值）
- **认知目标**：在目标通勤人群中建立"轻量保温随行杯"的产品认知。
- **转化目标**：通过多渠道内容与投放驱动产品页访问与购买转化。
- **资产目标**：积累首批真实用户反馈与投放数据，为后续优化提供依据。

> 假设：品牌方已有可承接流量的产品详情页（电商或官网）。若尚无落地页，需优先补齐，否则所有渠道动作无法闭环。

---

## 2. 受众定义

### 2.1 核心受众
- **人群**：一二线城市通勤人群
- **典型场景**：每日地铁/公交通勤、办公室全天饮水、差旅短途出行
- **痛点推导**（基于已确认卖点反推，非用户调研数据）：
  - 通勤包负重敏感 → 280g 轻量化
  - 早出晚归需要全天热水 → 12 小时保温
  - 杯盖缝隙难清洗 → 可拆洗杯盖

### 2.2 受众细分（假设性划分，待验证）
| 细分 | 特征假设 | 核心信息侧重 |
|---|---|---|
| 精致通勤白领 | 注重生活品质、愿意为设计付费 | 设计感 + 保温性能 |
| 健身/户外爱好者 | 关注材质与耐用性 | 轻量化 + 易清洁 |
| 礼品购买者 | 为他人选购、看重包装与性价比 | 199 元价格带 + 实用属性 |

> 以上细分为基于产品属性的逻辑划分，非真实用户画像数据。实际受众结构需通过投放测试或用户调研验证。

---

## 3. 信息结构

### 3.1 核心信息层级
```
第一层（主标题）：轻量保温，随行一整天
  ↓
第二层（三大支柱，对应已确认卖点）：
  ├─ 12 小时保温 —— 从早到晚，水温如初
  ├─ 280g 轻量化 —— 比手机还轻，通勤无负担
  └─ 可拆洗杯盖 —— 一拆即洗，无卫生死角
  ↓
第三层（信任与行动）：
  ├─ 建议零售价 199 元
  ├─ 品牌主色 #176B87（视觉统一）
  └─ 行动号召：了解详情 / 立即购买
```

### 3.2 信息使用规范
- 所有对外文案仅使用已确认的三个卖点与价格，不添加"行业领先""最轻便"等未经证实的比较级表述。
- 保温时长表述为"12 小时保温"（产品简报原文），不扩展为"12 小时 60°C 以上"等具体温度承诺，因为第三方检测报告尚未提供。
- 品牌主色 #176B87 用于所有渠道视觉素材的主色调统一。

---

## 4. 渠道动作

### 4.1 渠道总览
| 渠道 | 类型 | 动作 | 依赖条件 |
|---|---|---|---|
| 产品详情页 | 自有 | 上线产品页，承接所有渠道流量 | 假设已有电商/官网 |
| 社交媒体内容 | 免费/付费 | 产品卖点图文/短视频种草 | 素材制作 |
| Google Ads 搜索广告 | 付费 | 关键词定向投放，驱动产品页访问 | 需 Google Ads 账号与 API 凭据（见 4.3） |
| 邮件/私域触达 | 自有 | 面向已有用户群的新品通知 | 假设已有私域用户池 |

### 4.2 社交媒体内容动作
- **内容形式**：基于产品白底图制作卖点图文（3 张轮播，分别对应三个卖点）；短视频脚本围绕通勤场景展示轻量化与保温。
- **发布节奏**：上市前 1 周预热（悬念内容），上市当周集中发布卖点内容，上市后 2 周持续发布场景化内容。
- **视觉规范**：统一使用品牌主色 #176B87，产品图使用已确认白底图。

> 假设：品牌方有内容制作能力或可外包。若无法制作视频，最小可验证版本可仅使用图文内容。

### 4.3 Google Ads 投放渠道（技术落地说明）

本渠道技术落地严格遵循 `google-ads-api-quickstart` Skill 的 SKILL.md 执行规范。

#### 4.3.1 投放策略概述
- **广告类型**：搜索广告（Search Ads），定向与"保温随行杯""轻量水杯""通勤保温杯"等相关的关键词。
- **目标**：驱动产品详情页访问，衡量点击成本与转化率。
- **地域定向**：一二线城市（与目标受众一致）。

#### 4.3.2 API 集成路径选择
Skill 提供两条集成路径，本方案推荐如下：

| 路径 | 适用场景 | 本方案建议 |
|---|---|---|
| 官方客户端库（Python/Java/.NET/PHP/Ruby/Perl） | 有开发资源、需要批量操作与报表拉取 | **推荐 Python**（`google-ads` 包），生态成熟，参考文件 `references/python.md` |
| 直接 HTTP REST | 无客户端库环境、轻量 Serverless | 备选，参考文件 `references/rest.md` |

#### 4.3.3 凭据要求与当前阻断状态
SKILL.md 明确要求以下 5 项认证参数，**当前全部缺失**：

| 序号 | 参数 | 用途 | 当前状态 |
|---|---|---|---|
| 1 | Developer Token | 标识开发者访问与 API 配额 | 缺失 |
| 2 | OAuth2 Client ID | 应用身份标识 | 缺失 |
| 3 | OAuth2 Client Secret | 应用密钥 | 缺失 |
| 4 | OAuth2 Refresh Token | 自动获取新访问令牌 | 缺失 |
| 5 | Client Customer ID | 目标 Google Ads 账户 10 位 ID | 缺失 |
| 6（条件必填） | Login Customer ID | 经理账户 ID（通过经理账户访问客户账户时必填） | 缺失 |

**阻断结论**：由于上述凭据全部缺失，当前无法实际执行任何 Google Ads API 调用（包括查询广告系列、创建广告、拉取报表等）。Google Ads 渠道的技术落地处于**方案就绪、执行阻断**状态。

#### 4.3.4 凭据获取路径（按 SKILL.md Step 1）
1. **Developer Token**：在 Google Ads 经理账户的 API Center（`https://ads.google.com/aw/apicenter`）获取。注意：必须使用经理账户（Manager Account），非标准投放账户。
2. **OAuth2 Client ID & Secret**：在 Google Cloud Console 创建项目 → 启用 Google Ads API → 配置 OAuth 同意屏幕（用户类型选 External，发布状态选 Testing）→ 添加测试用户（必须是登录 Google Ads 的邮箱）→ 创建 Desktop App 类型 OAuth 客户端 → 下载 `client_secrets.json`。
3. **OAuth2 Refresh Token**：使用 `gcloud` CLI 执行登录流程：
   ```bash
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform \
     --client-id-file=client_secrets.json
   ```
   授权后从 `~/.config/gcloud/application_default_credentials.json` 中提取 `refresh_token`。
4. **Client Customer ID**：登录 Google Ads UI，右上角用户图标旁的 10 位 ID（去除连字符）。
5. **Login Customer ID**：经理账户的 10 位 ID（通过经理账户层级访问客户账户时必填，否则会触发 `USER_PERMISSION_DENIED`）。

#### 4.3.5 测试环境策略（按 SKILL.md 规则）
- **Pending Token 限制**：如果 Developer Token 状态为"Pending"（未审批），按 SKILL.md 规则**只能**使用 Google Ads 测试账户（Test Account），不能调用生产账户，否则会返回 `DEVELOPER_TOKEN_NOT_APPROVED` 错误。
- **测试账户搭建**：创建测试经理账户（无需已审批 Token）→ 在其下创建测试客户账户 → 使用测试客户 ID 进行配置。
- **生产访问级别**：要投放真实广告，Token 需获得 Google Ads API 合规团队审批的 **Explorer Access**、**Basic Access** 或 **Standard Access** 三者之一（按 SKILL.md 原文完整列出，不简化为"至少 Basic Access"）。

#### 4.3.6 动态版本解析（按 SKILL.md 强制规则）
- SKILL.md 要求：**不得硬编码** Google Ads API 版本或语言运行时版本，必须在执行开始时动态解析。
- 本次执行：尝试访问官方 Release Notes URL 失败，按 SKILL.md 离线回退规则取 `RESOLVED_API_VERSION = v24`。
- 代码生成时的占位符替换规则：
  - Python 导入：无版本命名空间（Python 客户端库内部处理）
  - REST 端点 URL：`https://googleads.googleapis.com/v24/customers/{customer_id}/googleAds:searchStream`
  - Java 导入：`com.google.ads.googleads.v24`（小写）
  - .NET 命名空间：`Google.Ads.GoogleAds.V24`（首字母大写）
- Python 运行时版本：官方 Supported Versions 页面同样无法访问，按 SKILL.md 离线回退取最低版本 `Python 3.9+`。

#### 4.3.7 快速验证脚本（凭据就绪后可执行）
以下为按 SKILL.md 与 `references/python.md` 规范整理的"查询广告系列"验证脚本，仅在凭据补齐后使用：

**配置文件 `google-ads.yaml`**（放在项目根目录）：
```yaml
developer_token: INSERT_DEVELOPER_TOKEN_HERE
client_id: INSERT_OAUTH2_CLIENT_ID_HERE
client_secret: INSERT_OAUTH2_CLIENT_SECRET_HERE
refresh_token: INSERT_OAUTH2_REFRESH_TOKEN_HERE
login_customer_id: INSERT_LOGIN_CUSTOMER_ID_HERE
use_proto_plus: true
```

**验证脚本 `get_campaigns.py`**（用于确认 API 连通性，查询现有广告系列）：
```python
import argparse
import os
import sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

def main(client, customer_id):
    googleads_service = client.get_service("GoogleAdsService")
    query = "SELECT campaign.id, campaign.name, campaign.status FROM campaign ORDER BY campaign.id"
    print("Querying Google Ads API...")
    try:
        stream = googleads_service.search_stream(customer_id=customer_id, query=query)
        for response in stream:
            for row in response.results:
                print(f"Campaign found: ID = {row.campaign.id}, Name = '{row.campaign.name}', Status = {row.campaign.status.name}")
    except GoogleAdsException as ex:
        print(f"Request ID '{ex.request_id}' failed with status '{ex.error.code().name}':")
        for error in ex.failure.errors:
            print(f"\tError: {error.message}")
        sys.exit(1)

if __name__ == '__main__':
    local_config = os.path.join(os.getcwd(), "google-ads.yaml")
    if os.path.exists(local_config):
        googleads_client = GoogleAdsClient.load_from_storage(local_config)
    elif "GOOGLE_ADS_DEVELOPER_TOKEN" in os.environ:
        googleads_client = GoogleAdsClient.load_from_env()
    else:
        googleads_client = GoogleAdsClient.load_from_storage()

    parser = argparse.ArgumentParser(description="Lists campaigns for a specified customer ID.")
    parser.add_argument("-c", "--customer_id", required=True, help="10-digit customer ID.")
    args = parser.parse_args()
    normalized_customer_id = args.customer_id.replace("-", "")
    main(googleads_client, normalized_customer_id)
```

**安装与运行**（凭据就绪后）：
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install google-ads
python get_campaigns.py -c XXXXXXXXXX
```

> 按 SKILL.md 静态诊断约束：排错时**不得**在工作区执行 bash 命令或运行本地测试脚本来复现错误，应依赖静态代码分析与配置审查。上述脚本仅作为凭据就绪后的交付物，不在当前阻断状态下执行。

#### 4.3.8 常见错误预案（按 SKILL.md Step 4）
| 错误 | 根因 | 处理方案 |
|---|---|---|
| `USER_PERMISSION_DENIED` | OAuth 用户通过经理账户间接访问客户账户，但请求头缺少经理账户 ID | 在配置中添加 `login_customer_id`（经理账户 10 位 ID）。`login_customer_id` = 经理账户 ID，`client_customer_id` = 客户账户 ID。这是 SKILL.md 明确指出的 #1 权限错误原因 |
| `DEVELOPER_TOKEN_NOT_APPROVED` | Pending 状态 Token 调用了生产账户 | 使用测试账户，或等待 Token 获批为 Explorer/Basic/Standard Access |
| `NOT_ADS_USER` | 生成 Refresh Token 的 OAuth 用户无目标账户访问权限 | 使用有访问权限的 Google 账户重新走 OAuth 流程 |
| `FileNotFoundException` | 客户端库找不到 `google-ads.yaml` | 确保文件名精确为 `google-ads.yaml`，放在运行目录或 `$HOME` 下 |

> 安全护栏（按 SKILL.md）：不得建议暴露明文密码、创建未审批的新开发者 Token、扩大 OAuth 范围来绕过权限错误；不得建议修改客户端库源码、绕过 Token 验证或使用第三方"破解"包装器。

---

## 5. 指标体系

### 5.1 指标分层
| 层级 | 指标 | 数据来源 | 当前状态 |
|---|---|---|---|
| 认知层 | 曝光量、展示次数 | 各渠道后台 | 待投放后获取 |
| 点击层 | 点击率（CTR）、点击量 | 各渠道后台 | 待投放后获取 |
| 转化层 | 产品页访问量、加购率、购买转化率 | 电商/官网分析工具 | 待上线后获取 |
| 效率层 | 单次点击成本（CPC）、单次获取成本（CPA）、广告支出回报率（ROAS） | Google Ads / 电商后台 | 待投放后获取 |
| 产品层 | 真实用户评价数量与评分、复购率 | 电商平台 | 待有真实销售后获取（禁止编造） |

### 5.2 指标使用规范
- 本方案**不预设任何指标目标值**（如"CTR 达到 3%"），因为缺乏历史投放数据与行业基准数据。
- 首轮投放的目标是**积累基线数据**，后续根据实际数据设定优化目标。
- 所有指标数据必须来自真实渠道后台，不得估算或编造。

---

## 6. 风险与阻断

### 6.1 执行阻断项（当前无法推进）
| 编号 | 阻断项 | 影响范围 | 解除条件 |
|---|---|---|---|
| B1 | Google Ads API 5 项凭据全部缺失 | Google Ads 渠道无法执行任何 API 调用 | 按 4.3.4 获取全部凭据 |
| B2 | 首发日期尚未确定 | 所有渠道排期无法锁定具体日期 | 品牌方确定首发日期 |
| B3 | 防水等级未提供 | 产品详情页与广告文案中无法描述防水性能 | 供应商提供防水等级参数 |
| B4 | 食品接触材料报告未提供 | 无法对外宣称材质安全性，广告文案受限 | 提供第三方检测报告 |
| B5 | 产品落地页状态未知 | 所有渠道流量无承接页 | 确认并上线产品详情页 |

### 6.2 风险项（可缓解但不可消除）
| 编号 | 风险 | 缓解措施 |
|---|---|---|
| R1 | Developer Token 处于 Pending 状态，无法投放真实广告 | 先使用测试账户验证 API 连通性，同时提交 Token 审批申请 |
| R2 | 经理账户层级配置错误导致 `USER_PERMISSION_DENIED` | 严格按 SKILL.md 配置 `login_customer_id`，首次调用前核对账户层级 |
| R3 | 缺乏历史投放数据，首轮投放效率不确定 | 以小预算测试起步，积累基线数据后再优化 |
| R4 | 卖点未经第三方检测验证，广告文案存在合规风险 | 仅使用产品简报已确认信息，不做扩展承诺；待检测报告补齐后再丰富文案 |
| R5 | `product_release_notes.md` 与本产品无关，若误用会导致信息混乱 | 已在 0.2 节明确标注不适用，全方案不引用其内容 |

---

## 7. 最小可验证版本（MVV）

### 7.1 MVV 定义
在当前阻断条件下，可完成的最小可验证交付物为：**一套不依赖 Google Ads API 实际调用、不依赖未确认产品信息的上市方案框架 + Google Ads 技术就绪文档**。

### 7.2 MVV 关键步骤
| 步骤 | 内容 | 产出 | 验收标准 |
|---|---|---|---|
| S1 | 产品信息校验与缺口识别 | 本文档第 0 节 | 已确认信息与缺失信息明确分离；不适用输入已标注 |
| S2 | 受众与信息结构定义 | 本文档第 2、3 节 | 受众基于已确认目标用户推导；信息结构仅使用三个已确认卖点 |
| S3 | 渠道动作规划（含 Google Ads 技术方案） | 本文档第 4 节 | 每个渠道有明确动作与依赖条件；Google Ads 部分遵循 SKILL.md 全部规则 |
| S4 | 指标体系与风险识别 | 本文档第 5、6 节 | 指标不预设目标值；阻断项与风险项分开列出 |
| S5 | Google Ads 技术就绪验证 | 配置文件模板 + 验证脚本（4.3.7） | 脚本符合 SKILL.md 与 python.md 规范；占位符已按 v24 替换；包含客户 ID 归一化逻辑 |

### 7.3 MVV 验收标准（整体）
1. 文档中所有产品信息均可追溯至 `product_brief.md`，无编造内容。
2. Google Ads 技术部分严格遵循 SKILL.md：动态版本解析（v24 回退）、5 项凭据清单、测试账户规则、静态诊断约束、常见错误预案均已覆盖。
3. 阻断项明确列出，未假装可执行 Google Ads API 调用。
4. `product_release_notes.md` 已标注为不适用，未被引用。
5. 结论与假设分离，待补项有明确验证路径。

### 7.4 后续推进条件
MVV 之后的完整执行需要：
1. 补齐 Google Ads API 5 项凭据（解除 B1）。
2. 品牌方确定首发日期（解除 B2）。
3. 补齐防水等级与食品接触材料报告（解除 B3、B4）。
4. 确认并上线产品落地页（解除 B5）。

以上条件全部满足后，可进入实际投放执行与数据回收阶段。

---

## 8. 待补项清单

| 编号 | 待补项 | 用途 | 获取方式 | 优先级 |
|---|---|---|---|---|
| P1 | Google Ads Developer Token | API 调用身份 | Google Ads 经理账户 API Center | 高 |
| P2 | OAuth2 Client ID & Secret | API 认证 | Google Cloud Console | 高 |
| P3 | OAuth2 Refresh Token | API 认证 | gcloud CLI 登录流程 | 高 |
| P4 | Client Customer ID | 目标广告账户 | Google Ads UI | 高 |
| P5 | Login Customer ID | 经理账户路由（如适用） | Google Ads 经理账户 UI | 高 |
| P6 | 首发日期 | 渠道排期 | 品牌方确定 | 高 |
| P7 | 防水等级 | 产品详情与广告文案 | 供应商参数 | 中 |
| P8 | 食品接触材料检测报告 | 材质安全宣称 | 第三方检测机构 | 中 |
| P9 | 产品落地页 URL | 流量承接 | 电商/官网上线 | 高 |
| P10 | 历史投放数据（如有） | 基线对比与目标设定 | 品牌方过往广告账户 | 低 |
| P11 | 竞品价格与市场数据 | 定价策略验证 | 市场调研（当前禁止编造） | 低 |
| P12 | 用户画像调研数据 | 受众细分验证 | 用户调研 | 低 |

---

## 附录 A：实际读取的 Skill 文件清单

| 文件相对路径 | 读取状态 | 用途 |
|---|---|---|
| `google-ads-api-quickstart/SKILL.md` | 已完整读取 | 主执行依据，含动态版本解析、凭据要求、排错规则 |
| `google-ads-api-quickstart/references/python.md` | 已完整读取 | Python 客户端库配置与验证脚本参考 |
| `google-ads-api-quickstart/references/rest.md` | 已完整读取 | REST 直接调用路径参考 |
| `google-ads-api-quickstart/references/java.md` | 未读取 | 本方案选用 Python 路径，Java 参考不涉及 |
| `google-ads-api-quickstart/references/dotnet.md` | 未读取 | 同上 |
| `google-ads-api-quickstart/references/php.md` | 未读取 | 同上 |
| `google-ads-api-quickstart/references/ruby.md` | 未读取 | 同上 |
| `google-ads-api-quickstart/references/perl.md` | 未读取 | 同上 |

## 附录 B：影响结果的 SKILL.md 关键规则

1. **5 项必填凭据规则（SKILL.md Step 1）**：直接导致 Google Ads 渠道处于"方案就绪、执行阻断"状态，是本方案最大的执行限制。若忽略此规则而虚构凭据或假装 API 可调用，将违反"不得编造"的核心约束。

2. **动态版本解析强制规则（SKILL.md "Crucial Requirement" 节）**：要求不得硬编码 API 版本，必须动态解析。本次因官方 URL 不可达，按离线回退取 v24，并在文档首部输出强制锚定块。此规则影响了所有技术备注中的版本号表述。

3. **Pending Token 仅限测试账户规则（SKILL.md Step 1.1 与 Step 4.2）**：决定了测试阶段必须使用测试账户，且生产访问需明确列出 Explorer/Basic/Standard 三个访问级别（不得简化）。此规则影响了 4.3.5 测试环境策略的设计。

4. **静态诊断约束（SKILL.md Step 4 开头）**：排错时不得执行 bash 命令或运行本地测试脚本复现错误。此规则决定了本方案不在当前环境执行验证脚本，仅将其作为凭据就绪后的交付物。

5. **login_customer_id 防错规则（SKILL.md Step 1.5 与 Step 4.1）**：通过经理账户访问客户账户时必须设置 `login_customer_id`，否则是 `USER_PERMISSION_DENIED` 的 #1 原因。此规则已纳入配置模板与错误预案。
