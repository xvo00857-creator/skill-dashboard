# CLIP 受约束可复用工具流程方案

> 依据随附 Skill `clip`（OpenAI CLIP，Vision-Language 零样本模型）的 SKILL.md 实现。
> 本方案只使用当前机器已有权限与本次提供/生成的数据，不静默创建、删除或覆盖外部资源。

## 1. Skill 能力边界（以 SKILL.md 为准）

CLIP 能做：
- 零样本图像分类（无需训练数据）
- 图文相似度 / 图文匹配
- 语义图像搜索（文本查图）
- 内容审核（NSFW / 暴力等宽泛类别）
- 跨模态检索（图→文、文→图）
- 图像去重（基于嵌入相似度）

CLIP **不能**做（SKILL.md Limitations，本工具不扩展这些职责）：
- 细粒度识别（如具体车型、品种细分）
- 边界框 / 目标定位（整图理解，无 bbox）
- 空间位置、物体计数等精细空间判断
- 需要精确描述的 caption 生成（应换 BLIP-2 / LLaVA）

依赖：`torch`、`transformers`、`pillow`，模型通过 `clip.load()` 加载，默认 `ViT-B/32`。

## 2. 受约束的可复用流程

### 2.1 总体步骤
1. **预检（preflight）**：检查 Python 版本、torch/clip/PIL/numpy 是否可导入、CUDA 是否可用、模型权重是否已在本地、缓存目录是否可写、输入图片是否可读。预检不加载模型、不联网。
2. **环境隔离**：在项目目录创建 `.venv`（`--system-site-packages` 复用已装 torch，避免污染系统 Python）；依赖安装带 3 次指数退避重试。
3. **模型加载（含下载确认门）**：默认 `ViT-B/32`。若权重不在 `~/.cache/clip/`，**必须**显式传 `--accept-model-download` 才会下载（约 338MB，来自 OpenAI）；否则退出码 3 并提示，不发生任何网络写入。
4. **编码与缓存（幂等）**：图片/文本嵌入以 `(模型名, 内容 sha256)` 为键存入项目本地 `.clip_cache/`。文件未改动则命中缓存，不重复编码；重复运行结果一致。
5. **任务执行**：`classify` / `search` / `dedup` 三个子命令，批处理、嵌入 L2 归一化后算余弦相似度（SKILL.md 要求）。
6. **输出**：结构化 JSON 到 stdout 或 `--out` 文件，便于程序消费与复核。

### 2.2 四项工程约束的落点

| 约束 | 实现方式 |
|---|---|
| 预检 | `preflight` 子命令 + 每次运行前的输入/标签/路径校验；缺依赖直接退出码 2 |
| 幂等 | 嵌入缓存按文件内容哈希；`classify2.json` 与 `classify.json` 预测完全一致即证明 |
| 重试 | 模型加载/下载、pip 安装均包 3 次指数退避；坏图单张跳过不中断整批 |
| 人工确认点 | ① 首次下载模型权重需 `--accept-model-download`；② 去重默认 dry-run，真删除需 `--apply` + `--i-understand-delete` 双开关 |

### 2.3 写入范围（不越界）
- 只写：项目目录下 `.venv/`、`.clip_cache/`、`results/`、以及 CLIP 官方缓存 `~/.cache/clip/`（仅在用户授权下载后）。
- 不写：系统 Python、系统目录、任何外部服务；不删除任何输入图片（去重默认只报告）。

## 3. 使用方法

```bash
# 0) 隔离环境（已建可跳过）
python3 -m venv --system-site-packages .venv
.venv/bin/pip install ftfy regex tqdm "git+https://github.com/openai/CLIP.git"

# 1) 预检（不联网、不加载模型）
.venv/bin/python clip_tool.py preflight --images demo_images

# 2) 零样本分类（首次需加 --accept-model-download）
.venv/bin/python clip_tool.py --accept-model-download classify \
  --images demo_images --labels dog cat car "sunset over the ocean" --describe \
  --out results/classify.json

# 3) 语义图搜
.venv/bin/python clip_tool.py search --images demo_images \
  --query "an animal with fur" --describe --top-k 4 --out results/search.json

# 4) 图像去重（默认 dry-run，不删除）
.venv/bin/python clip_tool.py dedup --images demo_images --threshold 0.95 --out results/dedup.json

# 5) 核验演示结果
.venv/bin/python verify_demo.py
```

## 4. 一次可核验的演示结果（2026-08-12 真实运行）

数据：用 Seedream 5.0 Pro 生成的 4 张 2048×2048 图片（金毛犬、橘猫、红色轿车、海上日落），
存于 `demo_images/`。设备：Mac CPU（无 GPU），模型 ViT-B/32。

### 4.1 零样本分类（4/4 正确）
| 图片 | 预测 | 置信度 |
|---|---|---|
| dog.jpg | a photo of dog | 99.95% |
| cat.jpg | a photo of cat | 99.27% |
| car.jpg | a photo of car | 99.91% |
| sunset.jpg | a photo of sunset over the ocean | 99.97% |

### 4.2 语义图搜（查询 "a photo of an animal with fur"）
按相似度排序：dog.jpg (0.247) > cat.jpg (0.244) > sunset.jpg (0.170) > car.jpg (0.156)
—— 两种哺乳动物正确排在前两位。

### 4.3 幂等与安全门
- 第二次分类结果与第一次完全一致，嵌入全部命中缓存，未重复下载/编码。
- 未授权下载：首次缺权重且未带 `--accept-model-download` 时退出码 3，零网络写入。
- 去重 dry-run：`pairs=[]`、`deleted=[]`、`dry_run=true`；带 `--apply` 但缺 `--i-understand-delete` 时仍拒绝删除，4 张原图完好。
- `verify_demo.py` 自动校验：**16/16 项 PASS**。

原始结果见 `results/classify.json`、`results/search.json`、`results/dedup.json`、`results/classify2.json`。

## 5. 仍需确认的假设与不可访问项
- 模型权重来自 OpenAI 公网，本次已在用户授权后下载到 `~/.cache/clip/ViT-B-32.pt`；离线环境需预置该文件，否则流程会停在确认门。
- 本次为 CPU 运行，SKILL.md 性能表称 GPU 快 10–50 倍；有 CUDA 时工具会自动选用 GPU。
- 演示图片由 Seedream 5.0 Pro 生成，非真实照片；分类/检索结论仅证明流程正确，不构成对真实数据分布的准确率承诺。
- 内容审核（NSFW 等）能力 SKILL.md 有提及但本次未演示，因为未提供也未生成任何敏感样本；不凭空构造敏感数据。
- 向量数据库集成（Chroma/FAISS）SKILL.md 有示例，但本次未安装这些外部依赖，未接入，避免额外外部资源写入。

## 6. 实际影响交付结果的 SKILL.md 规则（至少一条）
1. **"Use ViT-B/32 for most cases"** —— 工具默认模型定为 ViT-B/32，演示也用它，未选更大的 ViT-L/14，直接决定了下载体积（338MB）与 CPU 上的耗时。
2. **"Normalize embeddings - Required for cosine similarity"** —— 图像/文本嵌入在编码后立即 L2 归一化，余弦相似度才正确；这是 classify/search/dedup 三个命令结果可信的前提。
3. **"Use descriptive labels - 'a photo of X' works better"** —— 实现了 `--describe` 自动加 "a photo of " 前缀，演示标签即以此形式取得 99%+ 置信度。
4. **"Cache embeddings - Expensive to recompute"** —— 实现了内容哈希缓存，第二次运行直接命中，是幂等性的核心。
5. **Limitations（无 bbox、不适合细粒度任务）** —— 工具只输出整图级类别/相似度，不提供检测框或细粒度属性，避免越权承诺。

## 7. 交付文件清单
- `clip_tool.py` —— 受约束的 CLIP 命令行工具（预检/缓存/重试/确认门）
- `verify_demo.py` —— 演示结果确定性核验脚本
- `demo_images/` —— 4 张演示图片（dog/cat/car/sunset）
- `results/*.json` —— 真实运行输出
- `.clip_cache/` —— 嵌入缓存（幂等证据）
- `.venv/` —— 隔离 Python 环境
- `clip_skill/clip/SKILL.md`、`clip_skill/clip/references/applications.md` —— 实际读取的 Skill 文件
