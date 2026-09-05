# LLM 结构化抽取 Prompt 设计规范（P1.3 直接指导实现）

> 来源：改造自参考项目 `数据处理/提取jsonl格式的提示词.md`（医疗 KG 抽取 prompt，工业级成熟度）。
> 该 prompt 的**骨架与质量约束机制**可直接复用；**医疗本体（21 类实体 / 25 种关系）整体替换为论文本体**。
> 适配方向：计算机-情感识别-多模态情感识别。

## 1. 可直接继承的六项机制

| 机制 | 参考项目做法 | 本项目映射 |
| --- | --- | --- |
| 证据溯源 | `Chunk` 节点 + `SOURCED_FROM` / `MENTIONED_IN` 关系 | `Evidence` 实体 + 关系必带 `evidence_id[]`（见 `DATA_MODEL.md`） |
| 消歧决策树 | Symptom/Sign、Cause/RiskFactor 三组判定流程 | 改为论文领域的易混判别（见 §4） |
| 实体标准化表 | 症状同义词表、科室标准表，持续扩充 | Method/Dataset/Metric 别名表 + 低分转人工审核 |
| 证据分级 | GRADE A/B/C/D | 改为论文场景的证据强度分级（见 §5） |
| 空值原则 | "宁可信缺，不可臆造" | 同样适用，且是防幻觉的第一道闸门 |
| 输出自检清单 | Q1–Q12 + 逐条 checklist | 改为论文版（见 §7），作为 prompt 尾部强制步骤 |

## 2. 输出格式

**JSONL，每行一个 Paper 对象**（非 JSON 数组）—— 便于流式追加、单篇失败不影响整体、增量索引时按行处理。

字段顺序固定：`paper_id → metadata → methods → datasets → tasks → metrics → results → claims → evidence_chunks`

## 3. 执行流程（禁止跳步）

```text
Step 1 通读全文 → 识别论文贡献点（proposes / improves / compares）
Step 2 提取元数据（title/authors/year/venue/doi）
Step 3 抽取 Method / Model / Dataset / Task / Metric 实体
Step 4 抽取 Result（优先来自表格）+ 绑定实验条件 Condition
Step 5 抽取 Claim（作者结论性陈述）+ 绑定支撑 Evidence
Step 6 逐字段走消歧决策树（§4）
Step 7 实体标准化与别名归集（§6）
Step 8 为每个实体/关系绑定 page + section + char_span/bbox
Step 9 逐条运行自检清单（§7）→ 输出 JSONL
```

## 4. 消歧决策树（论文领域版）

参考项目用决策树解决"高频分类错误"，本项目最易混淆的是以下四组：

### 4.1 Method vs Model vs Framework

```
该名称指的是什么？
├─ 一种通用的训练/融合/对齐策略（如 LoRA、cross-modal attention fusion）
│ → Method
├─ 一个具体的网络结构或预训练模型（如 BERT、ViT、CLIP）
│ → Model
├─ 一个可复用的工程框架/工具库（如 PyTorch、MMF）
│ → Framework（不进 KG 核心，仅记录）
└─ 不确定？
 → 问："换掉底层 backbone 后它还成立吗？" 成立 → Method / 否则 → Model
```

### 4.2 Dataset vs Task vs Benchmark

```
├─ 具体数据集合（CMU-MOSI、IEMOCAP、CH-SIMS）→ Dataset
├─ 要解决的问题（multimodal sentiment analysis、emotion recognition）→ Task
├─ 一套评测协议/榜单（如某个 leaderboard）→ Benchmark（记录为 Task 的属性）
└─ 注：MOSI 在不同论文中可能指数据集也可能指其上的任务，按上下文判定
```

### 4.3 Result vs Claim

```
├─ 可从表格/正文定位到的具体数值（Acc-2 = 84.1%）→ Result（必须绑定 Condition）
├─ 作者对结果的解释或推广性陈述（"本方法在低资源场景下同样有效"）→ Claim
└─ 数值 + 作者解读出现在同一句 → 拆开存，Claim 引用该 Result 作为证据
```

### 4.4 Metric vs Metric Value

```
├─ 评价指标本身（Accuracy、F1、MAE、Pearson Corr）→ Metric
├─ 该指标在某次实验中的取值（F1 = 84.1）→ Result.value
└─ 指标的变体（Acc-2 / Acc-7 / binary accuracy）→ Metric 的别名，归一到规范名 + 保留原始字符串
```

## 5. 证据强度分级（改造自 GRADE）

| 级别 | 含义 | 典型来源 |
| --- | --- | --- |
| `A` | 论文自己报告的实验结果 | 实验表格、消融表 |
| `B` | 论文正文明确陈述的结论 | Section 中的结论句 |
| `C` | 转述他文结果 | Related Work、综述中的引用 |
| `D` | 推测、展望、未验证主张 | Future Work、讨论中的假设 |

用途：冲突检测时，`A` 级证据之间才做数值对比；`C`/`D` 不参与冲突判定。

## 6. 实体标准化表（种子，持续扩充）

多模态情感识别方向的数据集与指标高度标准化，归一成本远低于医疗领域 —— 这是选该方向做种子论文的额外收益。

| 类型 | 非标准写法 → 规范名 |
| --- | --- |
| Dataset | CMU-MOSI / MOSI → `MOSI`；CMU-MOSEI / MOSEI → `MOSEI`；CH-SIMS / SIMS → `CH-SIMS` |
| Task | MSA / Multimodal Sentiment Analysis → `Multimodal Sentiment Analysis`；ERC / Emotion Recognition in Conversation → `Emotion Recognition in Conversation` |
| Metric | Acc-2 / binary accuracy / Acc_2 → `Accuracy-2`；F1-score / F1 → `F1`；MAE → `MAE`；Corr / Pearson Correlation → `Pearson Correlation` |

规则：**保留原始字符串**（`raw_value`），归一只影响链接，不影响展示与溯源。同一实体的别名持续累积，供后续实体链接与向量召回使用。

## 7. 自检清单（论文版）

- [ ] 每行是独立 JSON 对象，可被 `JSON.parse()` 解析
- [ ] `paper_id` 唯一，元数据齐全（year/venue 缺失时按空值规则处理）
- [ ] 每个 Result 已绑定 `dataset_id` / `metric_id` / `split`（缺一不可，否则无法参与冲突检测）
- [ ] 每个 Claim 至少绑定一条 Evidence
- [ ] 每条 Evidence 含 `page` + `section`，表格/图片含 `bbox` 或 `source_uri`
- [ ] `char_span` 回查原文可命中（由代码校验，不命中则降置信）
- [ ] 方法名/数据集名/指标名已归一到标准表，别名已收集
- [ ] 术语未被翻译（LoRA、MOSI、IEMOCAP 等保持原文）
- [ ] 未臆造原文不存在的信息（宁缺毋造）
- [ ] 证据强度已标注（A/B/C/D）
- [ ] 列表字段已去重，单值字段不含换行符

## 8. 与代码层的分工

| 环节 | 归属 |
| --- | --- |
| 消歧、归一、分级 | **Prompt 层**（LLM 完成，但结果需校验） |
| `char_span` 回查、schema 校验、置信度计算 | **代码层**（`ingestion/validators/`，不信任 LLM 自述） |
| 低置信对象转人工 | **审核队列**（P2，阈值见 `configs/ingestion.yaml`） |

关键原则：**LLM 自述的置信度不可信**，置信度由代码的原文回查与规则校验给出，两者取低。
