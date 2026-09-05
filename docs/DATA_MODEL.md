# 领域模型（P0 定稿草案）

> 对应文档 §4，并补齐两个缺口：`Result` / `ExperimentalCondition`（冲突检测必需）。
> 只定义字段语义与约束，不写代码。实现落在 `src/litagent/domain/`。

## 通用约定

- 所有 ID 使用带前缀的字符串：`paper:xxx`、`ev:xxx`、`claim:xxx`、`rel:xxx`。
- 所有由 LLM 抽取生成的对象必须携带：
  - `confidence: float`（0~1）
  - `extraction_run_id: str`（可追溯到某次抽取运行，便于回滚与重抽）
  - `review_status: pending | approved | rejected`
- `review_status != approved` 的对象不进入 KG 正式标签（ADR-003）。

## 实体

### Paper

| 字段 | 说明 |
| --- | --- |
| `paper_id` | 主键 |
| `title` / `authors` / `year` / `venue` | 元数据 |
| `abstract` | 摘要全文 |
| `doi` / `arxiv_id` | 外部标识，用于去重 |
| `document_uri` | 原始 PDF 位置（唯一事实源，只读） |
| `parse_uri` | MinerU 解析产物目录 |

### Evidence（文档 §4.5，扩展定位字段）

| 字段 | 说明 |
| --- | --- |
| `evidence_id` | 主键 |
| `paper_id` | 所属论文 |
| `type` | `text \| table \| figure` |
| `page` | 页码（1-based） |
| `section` | 章节标题路径，如 `4.2 > Ablation` |
| `char_span` | 原文字符区间 `[start, end]`，用于回查校验 |
| `bbox` | 页面坐标（来自 MinerU），table/figure 必填 |
| `chunk_id` | 关联检索分块 |
| `content` | 文本/表格 Markdown/图注 |
| `source_uri` | 表格 HTML、图片文件等资产引用（大对象不入库） |

约束：`type != text` 时必须有 `bbox` 或 `source_uri`；`char_span` 回查原文不命中则自动降 `confidence`（ADR-001）。

### Claim（文档 §4.4，扩展）

`claim_id`、`statement`、`claim_type`（如 `performance | method_relation | limitation`）、`confidence`、`conditions`（指向 `Condition` 集合）、`paper_id`、`evidence_ids`。

### Method / Dataset / Task / Metric

统一结构：`*_id`、`canonical_name`、`aliases[]`、`description`。
`Dataset` 额外记录 `modality`、`scale`（可选），用于横向比较。

### Result（新增，文档缺口补 1）

| 字段 | 说明 |
| --- | --- |
| `result_id` | 主键 |
| `paper_id` / `evidence_id` | 来源论文与证据（多来自表格） |
| `method_id` | 被评估方法 |
| `dataset_id` / `task_id` / `metric_id` | 实验设置 |
| `value` | 数值或文本结果，保留原始字符串与解析数值 |
| `split` | train/val/test 或具体子集 |
| `is_best` | 原文是否标注最优 |
| `conditions` | 指向 `Condition` 集合 |

### ExperimentalCondition（新增，文档缺口补 2）

冲突检测的比较维度（文档 §9）：`dataset`、`backbone`、`metric`、`split`、`training_setting`、`year`。
设计为**可枚举的键值对**（`key` + `value` + `normalized_value`），避免为每个维度单独建表造成僵化。

## 关系（文档 §4.6）

```text
Paper --authored_by--> Author
Paper --proposes--> Method
Paper --evaluates--> Dataset
Paper --uses--> Model
Paper --addresses--> Task
Paper --reports--> Result
Paper --supports--> Claim
Paper --cites--> Paper
Paper --extends--> Paper
Method --improves--> Method
Method --compared_with--> Method
Method --evaluated_on--> Dataset
```

关系统一属性：`evidence_id[]`、`confidence`、`source`（`llm | rule | human`）、`extraction_run_id`。
**无 `evidence_id` 的关系禁止入图**（文档 §4 关键原则）。

## 存储映射

| 数据 | 存储 |
| --- | --- |
| Paper / Claim / Evidence 元数据、审核队列 | SQLite（SQLAlchemy，可切 Postgres） |
| 分块向量 + 检索过滤字段 | Qdrant |
| BM25 索引 | BM25s 落盘 `data/index/bm25` |
| 实体与关系 | Neo4j |
| PDF、图片、表格 HTML | 本地文件系统（后续可换 MinIO） |
