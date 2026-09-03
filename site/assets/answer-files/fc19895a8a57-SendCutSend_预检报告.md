# SendCutSend 上传预检报告

## 上下文（Context）

- 文件：`sample_bracket.dxf`（本地产物，演示样件，见下方"输入缺失说明"）
- 假定工艺：DXF 激光平板切割 + 折弯（bending）
- 订单上下文：材料 **5052 H32 Aluminum**，厚度 **0.063"**，SKU **ALU-063**，光纤激光（Fiber Laser）；数量、表面处理、硬件未指定（本次仅验证切割+折弯）
- 检查日期：2026-08-12

### 输入缺失说明
本次消息未随附待检查的 DXF/STEP 样件。为完整执行技能流程，使用 `ezdxf` 生成了一个带典型制造性缺陷的钣金支架 DXF 作为检查对象（`make_sample_dxf.py`）。若你提供真实文件，可用同一套命令直接替换 `sample_bracket.dxf` 重新检查。

## 已核查来源（Sources Checked）

- [SendCutSend 下单指南](https://cdn.sendcutsend.com/specs/sendcutsend-ordering-guide.md)（访问日期 2026-08-12）
- [sendcutsend-catalog.json](https://cdn.sendcutsend.com/specs/sendcutsend-catalog.json)（`_meta.generated_at` = 2026-04-29T20:52:33Z，178 种材料）
- [sendcutsend-specs.json](https://cdn.sendcutsend.com/specs/sendcutsend-specs.json)（`_meta.generated_at` = 2026-04-29T20:52:33Z；单位：英寸）

## 几何事实（Geometry Facts）

来自 `inspect_dxf.py`（只输出事实，不做判定；完整 JSON 见 `inspection_facts.json`）：

- DXF 版本 AC1024；`$INSUNITS=1`（英寸），`$MEASUREMENT=1`
- 边界：3.000 × 1.500 英寸（min 0,0 / max 3.0,1.5）
- 图层：CUTS（6 实体）、BEND（1 实体）、NOTES（1 实体）
- 实体类型：LWPOLYLINE×2、LINE×2、CIRCLE×3、TEXT×1
- 外轮廓与槽均为闭合多段线；无开放轮廓、无 SPLINE/ELLIPSE
- 重复线段：底边 (0,0)–(3,0) 出现 2 次（外轮廓 + 独立 LINE）
- 不支持实体：NOTES 图层 1 个 TEXT
- 孔：
  - H1 圆心 (0.10, 0.30)，直径 0.015"，最近边距 0.0925"
  - H2 圆心 (2.93, 0.75)，直径 0.125"，最近边距 0.0075"（到右外缘）
  - H3 圆心 (1.50, 0.75)，直径 0.125"，最近边距 0.6875"
- 折弯线（BEND 图层，DASHED 线型）：(0.20,0)–(0.20,1.5)，长 1.5"，垂直，贯穿全高
  - 沿折弯线 61 点射线采样：A 侧（左）整体法兰 0.200"，槽段（y≈0.6–0.9）局部法兰 0.010"；B 侧（右）整体法兰 2.800"，槽段局部法兰 0.020"
  - 内部穿越：槽的两条水平边在 (0.20,0.60)、(0.20,0.90) 穿越折弯线
  - 端点接触：折弯线两端 (0.20,0)、(0.20,1.5) 接触外轮廓（正常）
- 局限：检查脚本未做布尔运算，孔边距为圆心到线段距离减半径；折弯半径/角度不在 DXF 中编码，无法从文件测量。

## 检查结果（Findings）

| 状态 | 检查项 | 实测事实 | 规则来源 | 修改建议 |
| --- | --- | --- | --- | --- |
| ✅ pass | 单位/比例 | `$INSUNITS=1`（英寸），为指南认可代码 | [ordering-guide.md](https://cdn.sendcutsend.com/specs/sendcutsend-ordering-guide.md) 文件格式章节 | 无需修改 |
| ✅ pass | 整体尺寸 | 3.0×1.5"，在 0.375×0.25 ~ 44×30 范围内 | [catalog.json](https://cdn.sendcutsend.com/specs/sendcutsend-catalog.json) materials[sku=ALU-063].min/max_part_size | 无需修改 |
| ✅ pass | 平板最小尺寸（折弯） | 3.0×1.5 ≥ 0.375×1.5 | [specs.json](https://cdn.sendcutsend.com/specs/sendcutsend-specs.json) materials[sku=ALU-063].bending_specs.min_flat_part_size | 无需修改 |
| ✅ pass | 折弯长度 | 1.5" ≤ 44.0" | specs.json materials[sku=ALU-063].bending_specs.max_bend_length | 无需修改 |
| ✅ pass | 折弯线图层/线型 | 独立 BEND 图层，DASHED，贯穿待折区域 | ordering-guide.md Bending 章节 | 无需修改 |
| ✅ pass | 闭合轮廓 | 外轮廓与槽均闭合，无开放多段线 | ordering-guide.md DXF 章节 | 无需修改 |
| ✅ pass | H3 孔径与边距 | 直径 0.125" ≥ 0.022"；边距 0.6875" ≥ 0.020" | specs.json materials[sku=ALU-063].cutting_specs.min_hole_size / min_hole_to_edge | 无需修改 |
| ❌ fail | H1 孔径过小 | 直径 0.015" < 0.022" | specs.json materials[sku=ALU-063].cutting_specs.min_hole_size | 将 H1 孔径改为 ≥0.022"，或删除该孔/改用其他工艺 |
| ❌ fail | H2 孔到边距离不足 | 孔边到右外缘 0.0075" < 0.020" | specs.json materials[sku=ALU-063].cutting_specs.min_hole_to_edge | 将 H2 左移，使孔边到外边缘 ≥0.020"（圆心 x ≤ 2.9175） |
| ❌ fail | 左侧法兰过短 | 折弯前法兰 0.200" < 0.255" | specs.json materials[sku=ALU-063].bending_specs.min_flange_length_before_bend | 折弯线右移至 x ≥ 0.255，或向左加长外轮廓 |
| ❌ fail | 槽处局部法兰/折弯支撑不足 | 槽段局部法兰 0.010"（A 侧）/ 0.020"（B 侧），远小于 0.255"/0.303" | specs.json materials[sku=ALU-063].bending_specs.min_flange_length_before/after_bend；Direct file inspection | 将槽移出折弯区域，或在槽两侧加止裂槽并保证局部法兰 ≥ 最小值 |
| ❌ fail | 切割几何穿越折弯线 | 槽水平边在 (0.20,0.60)、(0.20,0.90) 内部穿越折弯线，折弯被中断 | Direct file inspection（ordering-guide.md：折弯线必须完整贯穿待折区域） | 槽不得跨越折弯线；重新布置槽或断开折弯线段并加止裂结构 |
| ❌ fail | 重复切割几何 | 底边 (0,0)–(3,0) 存在重合重复线 | ordering-guide.md DXF 章节（重复/重叠线需移除）；Direct file inspection | 删除多余的 LINE，仅保留外轮廓一条边 |
| ❌ fail | 不支持的注释实体 | NOTES 图层含 TEXT "MATERIAL: AL 0.063 BEND UP" | ordering-guide.md 文件格式章节（文本/注释不属于切割几何） | 上传前删除 TEXT/标注，材料在下单界面选择 |
| ❓ need more info | 折弯角度 | DXF 平板样条不编码折弯角度，无法核对 ≤130° | specs.json materials[sku=ALU-063].bending_specs.max_bend_angle | 在 SCS 下单界面选择折弯角度时确保 ≤130° |

## 诊断图

见 `diagnostic.png`（编号①–⑥对应上表 fail 项；红色虚线为折弯线，红色填充为穿越折弯线的槽）。

## 结论（Verdict）

**Needs edits before upload（上传前需修改）**

存在 7 项 ❌ fail：1 个小孔、1 个孔边距不足、1 处法兰过短、1 处槽致局部法兰/支撑不足、1 处切割线穿越折弯、1 条重复线、1 个不支持文本。按 SKILL 规则，任一 ❌ fail 即不得判定为可上传。完成上述修改后可用相同命令复检。

## 约束导致的方案变化

1. **不新增非必要依赖**：仅安装技能强制要求的 `ezdxf`（技能明确禁止用纯文本解析获取几何事实）；未安装重型的 `build123d`/`OCP`，因为本次只检查 DXF，ezdxf 足以测量所需几何事实（build123d 主要用于 STEP）。
2. **不改变无关文件**：所有产物（样件 DXF、脚本、源文件副本、报告、图片）均写入当前工作目录，未触碰系统或其他项目文件。
3. **外部账号只做到确认前步骤**：未登录、未上传到 app.sendcutsend.com、未下单；仅抓取公开的指南/JSON 源并做本地几何预检。获取即时报价需在浏览器上传文件（无需登录即可报价，结账才需登录），本次按约束停在本地预检。
4. **`$cad`/`$cad-viewer` 技能未安装**：按 SKILL 要求报告此情况，而非静默省略；改用 ezdxf 直接测量，并以 matplotlib 本地出诊断图替代 CAD Viewer 交接。
5. **输入样件缺失**：用户未提供 DXF/STEP，故生成演示样件并明确标注；检查脚本对任意同构 DXF 可复用。

## 可重复验证命令

```bash
# 1. 安装唯一必要依赖
pip3 install ezdxf

# 2. （可选）重新生成演示样件
python3 make_sample_dxf.py

# 3. 抓取最新官方源
curl -sL -o sources/ordering-guide.md https://cdn.sendcutsend.com/specs/sendcutsend-ordering-guide.md
curl -sL -o sources/catalog.json      https://cdn.sendcutsend.com/specs/sendcutsend-catalog.json
curl -sL -o sources/specs.json        https://cdn.sendcutsend.com/specs/sendcutsend-specs.json

# 4. 运行事实检查（输出 JSON，不含判定）
python3 inspect_dxf.py sample_bracket.dxf

# 5. 重新生成诊断图（需 matplotlib，macOS 自带中文字体）
MPLCONFIGDIR=/tmp/mplcfg python3 make_diagram.py
```

## 验证证据

- 几何事实输出：`inspection_facts.json`（由 `inspect_dxf.py` 生成）
- 关键实测值：H1 直径 0.015、H2 边距 0.0075、左法兰 0.200、槽处局部法兰 0.010/0.020、穿越点 (0.20,0.60)/(0.20,0.90)、重复底边 1 条、TEXT 1 个
- 诊断图：`diagnostic.png`
- 官方源本地副本：`sources/ordering-guide.md`、`sources/catalog.json`、`sources/specs.json`
