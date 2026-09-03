# 可复用商品图生成工作流（ComfyUI API 格式）

本工作流基于 `comfyui` Skill 规范构建，用于在 ComfyUI 中生成电商商品主图。
采用标准 SDXL 文生图管线，输出 1024×1024 白底棚拍风格商品图。

---

## 一、节点配置

工作流文件：`product_image_workflow_api.json`（ComfyUI **API 格式** JSON，非 UI 布局格式）

共 7 个节点，数据流如下：

```
CheckpointLoaderSimple(4) ──MODEL──> KSampler(3) ──LATENT──> VAEDecode(8) ──IMAGE──> SaveImage(9)
        │                       ▲
        ├──CLIP──> CLIPTextEncode(6, 正向) ──CONDITIONING──┤
        ├──CLIP──> CLIPTextEncode(7, 负向) ──CONDITIONING──┤
        └──VAE─────────────────────────────────────────────┘
                        ▲
EmptyLatentImage(5) ────┘ (1024×1024)
```

| 节点 ID | class_type | 作用 | 类型 |
|---------|-----------|------|------|
| 4 | CheckpointLoaderSimple | 加载 SDXL 底模，输出 MODEL/CLIP/VAE | 固定（加载器） |
| 5 | EmptyLatentImage | 创建 1024×1024 空白潜空间 | 模板化（尺寸） |
| 6 | CLIPTextEncode | 正向提示词编码 | 模板化（文本） |
| 7 | CLIPTextEncode | 负向提示词编码 | 模板化（文本） |
| 3 | KSampler | 采样器（seed/steps/cfg/sampler/scheduler） | 模板化（采样参数） |
| 8 | VAEDecode | 潜空间解码为像素图 | 固定（图结构） |
| **9** | **SaveImage** | **保存最终图片（output_node）** | 模板化（文件名前缀） |

**output_node = "9"**（SaveImage 节点，字符串 ID，非 class 名）。

---

## 二、关键参数

### 模板化参数（复用时修改这些，不动图结构）

| 参数 | 节点 | 输入键 | 默认值 | 说明 |
|------|------|--------|--------|------|
| 正向提示词 | 6 | text | `product photography, a ceramic coffee mug...` | 商品描述 + 摄影词 |
| 负向提示词 | 7 | text | `blurry, low quality, watermark...` | 排除常见瑕疵 |
| seed | 3 | seed | 42 | 随机种子，固定后可复现 |
| steps | 3 | steps | 30 | 采样步数，25–35 适合商品图 |
| cfg | 3 | cfg | 7.0 | 提示词遵循度，6–8 为宜 |
| sampler_name | 3 | sampler_name | dpmpp_2m | 采样器 |
| scheduler | 3 | scheduler | karras | 调度器 |
| denoise | 3 | denoise | 1.0 | 去噪强度（文生图固定 1.0） |
| width | 5 | width | 1024 | 宽（px），SDXL 推荐 1024 |
| height | 5 | height | 1024 | 高（px），SDXL 推荐 1024 |
| filename_prefix | 9 | filename_prefix | product_image | 输出文件名前缀 |

### 固定参数（不应随意改动）

- **节点 4 ckpt_name**：`sd_xl_base_1.0.safetensors`。换模型时仅改此字段，并将模型文件放入 `ComfyUI/models/checkpoints/`。
- **所有节点连线**：MODEL/CLIP/VAE/CONDITIONING/LATENT/IMAGE 的连接关系。

### 推荐商品图提示词结构

```
product photography, <商品主体描述>, on a clean white background,
studio lighting, soft shadows, high detail, 8k uhd,
commercial product shot, centered composition
```

替换 `<商品主体描述>` 即可生成不同商品（如 `a wireless earphone case`、`a glass perfume bottle`）。

---

## 三、输入输出样例

### 输入

见 `examples/input_example.json`，核心字段：

```json
{
  "positive_prompt": "product photography, a ceramic coffee mug on a clean white background, studio lighting, soft shadows, high detail, 8k uhd, commercial product shot, centered composition",
  "negative_prompt": "blurry, low quality, watermark, text, logo, deformed...",
  "seed": 42,
  "width": 1024,
  "height": 1024,
  "steps": 30,
  "cfg": 7.0,
  "sampler_name": "dpmpp_2m",
  "scheduler": "karras"
}
```

### 输出

- ComfyUI 实际运行后：图片保存至 `ComfyUI/output/product_image_00001_.png`。
- 本环境因无 ComfyUI 服务，使用 Seedream 5.0 Pro 以相同提示词生成了参考样例：
  `examples/output_sample.jpg`（2048×2048，展示工作流预期的白底棚拍商品图效果）。

---

## 四、依赖

### 运行依赖（在有 ComfyUI 的机器上）

| 依赖 | 版本/要求 | 用途 |
|------|----------|------|
| ComfyUI | 最新稳定版 | 工作流执行引擎 |
| SDXL 底模 | `sd_xl_base_1.0.safetensors`（或任意 SDXL checkpoint） | 放入 `models/checkpoints/` |
| GPU 显存 | ≥ 8GB（SDXL 1024×1024 典型占用约 6–8GB） | 推理 |

> 低显存（8GB）可将分辨率降至 832×1216 或使用 FP16/FP8 量化模型；
> 本工作流为标准 SDXL 管线，无需任何自定义节点（custom nodes）。

### 验证依赖（本目录脚本）

- **Python 3.6+**，仅使用标准库（`json`、`urllib`、`os`、`sys`、`argparse`），**不安装任何第三方包**。

---

## 五、复现步骤

### 步骤 1：准备 ComfyUI 环境

```bash
# 克隆并安装 ComfyUI（在有 GPU 的机器上）
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# 下载 SDXL 底模到 models/checkpoints/
# 例如 sd_xl_base_1.0.safetensors
```

### 步骤 2：启动 ComfyUI

```bash
python main.py --listen 127.0.0.1 --port 8188
```

服务启动后，`http://localhost:8188/system_stats` 应返回 JSON。

### 步骤 3：运行验证脚本

```bash
cd comfyui_product_workflow

# 静态校验（不依赖 ComfyUI 运行）
python3 verify_workflow.py

# 静态校验 + 提交任务到本地 ComfyUI
python3 verify_workflow.py --submit

# 指定远程 ComfyUI 服务
python3 verify_workflow.py --server http://192.168.1.100:8188 --submit
```

### 步骤 4：在 ComfyUI 界面中使用

1. 打开 `http://localhost:8188`。
2. 将 `product_image_workflow_api.json` 拖入界面（API 格式 JSON 可直接加载）。
3. 修改节点 6 的提示词为目标商品描述。
4. 点击 Queue Prompt，输出图片在 `ComfyUI/output/`。

### 步骤 5：命令行批量提交（可选）

```bash
# 验证脚本的 --submit 即通过 POST /prompt 提交
# 也可直接用 curl：
curl -X POST http://localhost:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": '"$(cat product_image_workflow_api.json)"'}'
```

---

## 六、可重复验证命令

以下命令**不依赖 ComfyUI 运行**，可在任意装有 Python 3 的机器上执行：

```bash
# 1. JSON 合法性 + 节点引用完整性 + output_node + 模型依赖检查
python3 verify_workflow.py

# 2. 验证通过后退出码为 0，可用于 CI
echo "退出码: $?"

# 3. 若 ComfyUI 已启动，额外做健康检查和任务提交
python3 verify_workflow.py --submit
```

验证脚本检查项：
1. 所有节点 ID 引用是否指向存在的节点；
2. 每个节点是否有 `class_type` 和 `inputs`；
3. output_node 是否为 SaveImage 等终端保存节点；
4. 模型加载器引用的模型文件名及目标目录；
5. 模板化/固定节点分类；
6. ComfyUI 服务健康状态（`GET /system_stats`）；
7. 可选：提交任务（`POST /prompt`）。

---

## 七、约束导致的方案变化

| 约束 | 影响 |
|------|------|
| **不新增非必要依赖** | 验证脚本仅用 Python 标准库（urllib/json/argparse），未安装 requests、PIL 等第三方包；工作流选用 SDXL 标准管线，无需自定义节点。 |
| **不改动无关文件** | 所有交付物放在独立目录 `comfyui_product_workflow/` 内；未修改 Skill 原始文件 `comfyui/SKILL.md`；未在系统目录写入任何配置。 |
| **本地/沙盒可重复验证** | 提供 `verify_workflow.py`，静态校验部分在无 ComfyUI、无 GPU 的环境也能运行并给出确定性结果；`--submit` 为可选增强项。 |
| **外部账号/服务依赖只做到安全模拟或确认前步骤** | 当前环境无 ComfyUI 服务（8188 端口未监听）、无 `comfyui_image`/`comfyui_video` 工具、未安装 ComfyUI。因此：①未实际启动或安装 ComfyUI（涉及下载数 GB 模型，属于重操作）；②验证脚本对服务不可达仅做警告并给出启动指引，不强行安装；③输出样例使用 Seedream 5.0 Pro 以相同提示词生成，作为效果参考而非 ComfyUI 实际渲染结果。 |
| **使用 Seedream 5.0 Pro 生图** | 按要求，样例图由 Seedream 5.0 Pro 生成，未使用其他生图模型。 |

---

## 八、验证证据

### 静态验证结果（实际执行输出）

```
== 1. 结构校验 ==
  [通过] 共 7 个节点，6 个被引用
  [通过] 无孤立节点
  [通过] 所有节点引用均可解析

== 2. 模板化节点 / 固定节点识别 ==
  节点    3 | KSampler                 | 模板化参数: seed, steps, cfg, sampler_name, scheduler, denoise
  节点    4 | CheckpointLoaderSimple   | 固定（加载器/模型）
  节点    5 | EmptyLatentImage         | 模板化参数: width, height, batch_size
  节点    6 | CLIPTextEncode           | 模板化参数: text
  节点    7 | CLIPTextEncode           | 模板化参数: text
  节点    8 | VAEDecode                | 固定（图结构/连线）
  节点    9 | SaveImage                | 模板化参数: filename_prefix
  小结: 模板化节点 5 个，固定加载器 1 个

== 3. output_node 校验 (output_node="9") ==
  [通过] output_node 9 是终端保存节点: SaveImage
  [通过] 输出图片来自节点 8

== 4. 模型依赖 ==
  节点 4 (CheckpointLoaderSimple): sd_xl_base_1.0.safetensors -> ComfyUI/models/checkpoints/

== 5. ComfyUI 服务检查 (http://localhost:8188) ==
  [警告] 服务不可达: [Errno 61] Connection refused

结果: 通过 5, 失败 0, 警告 1
```

### 输出样例

`examples/output_sample.jpg`（Seedream 5.0 Pro 生成，2048×2048，与工作流正向提示词一致）。

---

## 九、缺失项与已完成范围

### 已完成

- [x] 解压并完整阅读 `comfyui/SKILL.md`
- [x] 按 Skill 规范创建 API 格式工作流 JSON（7 节点 SDXL 商品图管线）
- [x] 明确 output_node="9"（SaveImage，字符串 ID）
- [x] 区分模板化节点与固定节点
- [x] 标注模型依赖及目标目录
- [x] 零依赖验证脚本（静态校验 + 可选服务提交）
- [x] 输入样例 JSON
- [x] 输出样例图（Seedream 5.0 Pro）
- [x] 复现步骤与验证命令
- [x] 约束影响说明

### 未完成 / 缺失项（如实说明）

| 缺失项 | 原因 | 影响 |
|--------|------|------|
| ComfyUI 实际渲染输出 | 当前环境无 ComfyUI 服务、未安装 ComfyUI、无 GPU | 无法提供 ComfyUI 引擎实际生成的 PNG；样例图由 Seedream 5.0 Pro 替代生成 |
| `comfyui_image`/`comfyui_video` 工具调用 | 这两个工具在当前工具环境中不存在（tool_search 未找到） | 无法通过 OpenMontage 工具链提交工作流；改用直接 HTTP 提交方式（脚本已实现） |
| SDXL 模型文件 | 未下载（约 6.5GB），且无 ComfyUI 目录结构 | 工作流中引用了 `sd_xl_base_1.0.safetensors`，需用户在有 ComfyUI 的环境自行放置 |
| 工作流哈希 | 哈希由 OpenMontage 工具在提交时记录，当前无工具可生成 | 复现性契约以"工作流 JSON 内容 + 模型栈 + seed + 尺寸 + 提示词"文本形式记录 |

---

## 十、实际读取的 Skill 文件

| 文件相对路径 | 说明 |
|-------------|------|
| `comfyui/SKILL.md` | ZIP 包内唯一文件，已完整阅读（55 行，4524 字节） |

ZIP 包内无其他文件（无 bundled workflows、无脚本、无示例资源）。

### 实际影响执行的 SKILL.md 规则

1. **API 格式导出**（第 15 行）：工作流保存为 API 格式 JSON（`{node_id: {class_type, inputs}}`），而非 UI 布局格式——直接决定了 `product_image_workflow_api.json` 的结构。
2. **output_node 契约**（第 26–29 行）：自定义工作流必须传 `output_node`，传节点 ID 字符串而非 class 名，选最终保存节点——因此设 `"9"` 并在验证脚本中强制校验。
3. **模板化 vs 固定节点**（第 33–35 行）：识别 prompt/seed/尺寸/采样参数为模板化，模型加载器/连线为固定——决定了输入样例和文档中参数分类，以及验证脚本的分类逻辑。
4. **模型目录约定**（第 40 行）：checkpoint 放入 `models/checkpoints/`——验证脚本据此输出模型目标路径。
5. **Provenance 可复现性**（第 46–48 行）：记录 workflow_model_stack（底模、采样器、步数、cfg、seed、尺寸）——文档"关键参数"和"缺失项"中据此列出。
6. **服务不可用处理**（第 52 行）：服务不可达时给出结构化启动指引，不强行安装——验证脚本对 Connection refused 仅警告并提示启动命令。
7. **缺模型处理**（第 53 行）：列出缺失模型文件名、角色、目标目录——验证脚本第 4 步输出模型清单。
8. **不承诺任意工作流适配机器**（第 22 行）：在依赖章节如实标注显存需求，未保证在所有机器上可运行。
