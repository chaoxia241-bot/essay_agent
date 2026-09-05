# 技术选型决策记录（ADR）

## 已决策

### ADR-001 PDF 解析采用 MinerU

- 状态：accepted（2026-08-31）
- 背景：正文/表格/公式/图片的解析质量直接决定 Evidence 可信度，自研成本过高。
- 备选：Docling、PyMuPDF + 自研。
- 决策：采用 **MinerU（magic-pdf）**，输出 Markdown + JSON 中间层 + 图片/表格资产，保留 `page/bbox` 用于证据定位。
- 影响与代价：
  - 需要 GPU 或较重的 CPU 依赖（`magic-pdf[full]`），解析是离线批处理步骤，不进入在线链路。
  - 解析产物统一落 `data/parsed/<paper_id>/`，原始 PDF 只读不改动。
  - 抽取层必须消费 MinerU 的 `page/section/span` 信息，禁止只依赖 Markdown 文本做定位。
  - 表格以 Markdown + HTML 双份保存，避免单一格式丢失结构。

### ADR-002 检索采用 Qdrant（Dense） + BM25s（稀疏）

- 状态：accepted（2026-08-31）
- 背景：需要 Dense 与 BM25 双路召回后做 RRF 融合。
- 备选：Postgres+pgvector、Elasticsearch 一体、LanceDB/FAISS。
- 决策：**Qdrant** 存向量与 payload 过滤；**BM25s** 做关键词检索，索引落盘 `data/index/bm25`，进程内加载。
- 影响与代价：
  - 多一个服务（Docker Qdrant），换来 ANN 性能与元数据过滤能力。
  - 业务元数据（Paper/Claim/Evidence 等）不塞进 Qdrant 大 payload，只存 `chunk_id/paper_id/page/section/type` 等检索过滤字段，正文回查走关系库。
  - BM25s 索引需重建机制：新增论文走增量追加，词表变化超阈值时全量重建。
  - 迁移成本受控：检索层收敛为 `DenseRetriever` / `SparseRetriever` 两个接口，换库只改实现。

### ADR-003 图存储采用 Neo4j

- 状态：accepted（2026-08-31）
- 背景：需要表达 Paper/Method/Dataset/Task/Metric/Result/Claim 之间的关系并支持多跳遍历。
- 备选：Postgres + AGE、NetworkX 内存图。
- 决策：**Neo4j**（Docker），Cypher 管理关系，可视化用于人工审核与调试。
- 影响与代价：
  - 关系必须有 `evidence_id` 与 `confidence`；无证据的关系不允许入图（文档 §4 原则）。
  - 低置信关系先入审核队列，审核通过后才写入正式标签。
  - 图只存结构化关系，不存长文本；长文本一律回到 Evidence / 对象存储。

### ADR-004 模型先走廉价云端 API，后接本地部署与微调

- 状态：accepted（2026-08-31）
- 背景：主线是 Agent 流程与证据体系，不应被本地推理环境阻塞；文档 §13 的 Qwen3-8B 实验后置。
- 备选：本地 Qwen3-8B + vLLM 起步、纯本地。
- 决策：
  - P1–P5 全部走**云端 API**，统一用 **OpenAI 兼容协议**封装（`openai` SDK + `base_url` 切换），供应商可无痛替换。
  - 配置按用途分层：`extraction` / `synthesis` / `planner`，可分别指向不同价位模型。
  - 所有调用记录 `model`、`prompt_version`、`tokens`、`cost`，为 P7 构建 SFT/偏好数据留痕。
- 影响与代价：
  - 抽象层必须屏蔽供应商差异，本地 vLLM 接入时只改 `base_url` 与 driver。
  - 需要 budget 控制（子问题数、证据上限、max_tokens），防止 Deep Research 成本失控。
  - 保留本地化路径：`configs/models.yaml` 中 driver 可切换为 `vllm`，`src/litagent/training/` 目录已预留。

### ADR-005 业务元数据用 SQLite 起步，可切 Postgres

- 状态：proposed（默认执行，待确认）
- 背景：已选 Qdrant 与 Neo4j，但 Paper/Claim/Evidence/审核队列等强结构化数据仍需关系库；P1 阶段规模小。
- 决策：**SQLAlchemy ORM + SQLite** 起步，DSN 可切换 Postgres，不改业务代码。
- 影响与代价：SQLite 并发写入弱；若 Paper 数量过千或需多进程写入，再切 Postgres。

### ADR-006 LLM 采用 LongCat API

- 状态：accepted（2026-08-31）
- 背景：P1–P5 走廉价云端 API，后续再本地化与微调。
- 备选：DeepSeek、阿里百炼、SiliconFlow。
- 决策：**LongCat API**，`base_url = https://api.longcat.chat/openai/v1`，OpenAI 兼容，Bearer 鉴权。
- 影响与代价：
  - 平台**仅提供 chat/completions 与 models 接口，无 embeddings 端点** —— Embedding 必须本地部署（与 ADR-007 一致，无额外损失）。
  - 模型 ID 以 `GET /v1/models` 返回为准，起服前核对（配置暂写 `LongCat-2.0`）。
  - `response_format: json_object` 需实测；若不支持，结构化抽取降级为 function calling + JSON 修复重试。
  - 存在速率限制与 402（额度不足），需重试与退避；抽取批处理要限速。

### ADR-007 Embedding 与 Reranker 本地化，采用 BGE 系列

- 状态：accepted（2026-08-31）
- 背景：语料为英文论文，用户 query 为中文，属跨语言检索；LongCat 不提供 embedding。
- 决策：
  - **Embedding：BAAI/bge-m3（本地，fp16，1024 维）**。多语言对齐、8192 上下文，且**同时输出 sparse lexical weights**。
  - **Reranker：BAAI/bge-reranker-v2-m3（本地，fp16）**。
- 影响与代价：
  - 需 GPU 常驻（bge-m3 约 2GB + reranker 约 1.2GB，fp16），与 MinerU 解析错峰使用显存。
  - 索引维度固定为 1024，换模型需重建 Qdrant collection —— 因此**嵌入模型必须在 P1 建索引前定稿**。
  - 开发与部署使用同一模型权重，CPU / GPU 只影响速度，向量空间一致，索引可跨环境复用。

### ADR-008 跨语言检索策略（中文 query / 英文语料）

- 状态：accepted（2026-08-31）
- 背景：BM25 是字面匹配，中文 query 对英文语料**完全失效**；单纯换多语言 embedding 不足以补上这一路召回。
- 决策：三路召回 + 双语查询改写。
  1. **Dense 路**：中文 query 直接喂 bge-m3（多语言对齐，跨语言可用）。
  2. **BM25 路**：query 必须先由 LLM 改写为**英文检索式**才进入 BM25s（硬约束，不可跳过）。
  3. **bge-m3 sparse 路**：利用 bge-m3 自带的 lexical weights，具备跨语言能力，作为 BM25 的对冲。
  4. RRF 融合三路；Rerank 阶段默认使用英文检索式。
- 配套规则：
  - **术语保护**：方法/数据集/指标名（LoRA、ImageNet、GLUE 等）不翻译，维护词表并持续补充。
  - **评测集必须包含中文 query**，否则无法反映真实使用场景。
  - 若后续召回仍不足，再加"英文 chunk 生成中文摘要"的双视图索引（作为可选增强，不进 P1）。

### ADR-009 前端自建：FastAPI（SSE） + Vue3

- 状态：accepted（2026-08-31）
- 背景：需要展示界面，且希望界面完全可控、简历含金量高。
- 备选：Chainlit + NiceGUI、Gradio、RuoYi（Java 管理壳）。
- 决策：**FastAPI + Vue3 自建**。
  - 后端：FastAPI + SSE（`sse-starlette`），`src/litagent/api/` 只暴露 REST + SSE。
  - 前端：Vue3 + TypeScript + Vite + Element Plus + Pinia；`pdfjs-dist` 做原文定位高亮。
  - **引用走独立 SSE 事件**（`citation`），不混在 token 流里让前端正则猜 —— 这是"证据可追溯"能落地到 UI 的关键。
- 影响与代价：
  - 流式与引用交互需自研（协议已定稿，见 `docs/FRONTEND.md`，P2 实现）。
  - P1 先不实现前端，用 CLI 验证闭环，避免 UI 工作拖慢主线。
  - `step` 事件从 P1 就输出，P5 接 Research Agent 时无需改协议。

### ADR-010 双环境分级：无 GPU 开发机 + 8GB GPU 部署机

- 状态：accepted（2026-08-31）
- 背景：公司开发机无 GPU，个人笔记本 / 台式机为 8GB RTX 4060；流程验证在无 GPU 机，实际部署在 8GB GPU 机。
- 决策：`configs/models.yaml` 增加 **profile 机制**（`LITAGENT_PROFILE` 切换）：
  - `dev_cpu`（无 GPU）：`device=cpu`、`fp16=false`、embedding batch 8、**先关闭 reranker**（验证召回后再开）、MinerU 走 CPU。
  - `gpu_8g`（部署机）：`device=cuda`、`fp16=true`、batch 32、开启 reranker（top_k 50）、MinerU 走 GPU。
- 配套约束：
  - **开发与部署必须用同一 embedding 模型**（bge-m3），维度固定 1024，索引可跨环境复用；仅速度不同。
  - **MinerU 解析放 GPU 机做**，产物 `data/parsed`（JSON/Markdown，体积小）同步回开发机 —— 避免在无 GPU 环境硬扛解析。
  - MinerU 关闭公式识别（`extract_formulas: false`）、使用 pipeline 后端，8GB 显存下与 embedding/reranker 服务错峰运行。
  - **开发机只跑 10 篇小样本**：仅用于验证流程正确性，不追求指标。
  - 全量索引在 GPU 机构建：解析产物 `data/parsed` 与 Qdrant 快照同步；开发机的小样本索引视为一次性，不与 GPU 机索引混用（避免半截索引污染评测结果）。
  - P1 种子论文 10 篇规模下，CPU 建索引（约千级 chunk）在十几分钟量级，可接受；reranker 在 CPU 上只用于小批量验证。
- 影响与代价：需保证 profile 切换不引入行为差异（如 fp16/fp32 数值差导致的排序抖动），**评测一律以 GPU 环境结果为准**。

### ADR-011 不采用微软 GraphRAG 的社区摘要作为主路径

- 状态：accepted（2026-08-31）
- 背景：参考项目 `数据处理/图rag/` 已跑通微软 GraphRAG（entity extraction + community reports），具备可直接复用的经验与配置。
- 备选：直接沿用微软 GraphRAG 构建论文 KG 与检索。
- 决策：**不采用其社区摘要（community report）作为主检索路径**，仅借鉴其工程经验。
- 理由（与本项目第一原则冲突）：
  1. 微软 GraphRAG 用 **LLM 生成的社区摘要替代原文**做检索，本质是"以摘要为事实源"，违背文档 §3「原始 PDF 是最终证据源，不把 LLM 摘要当作事实源」。
  2. 它**不保留原文定位**（page/bbox/span），无法满足"结论可回溯到页码/表格"这一核心诉求。
  3. 构建成本高（社区摘要 token 开销大、增量更新需重算社区），与 P6 增量索引目标冲突。
- 可借鉴的部分：`entity extraction` 阶段的实体/关系抽取 prompt 思路、缓存与断点续跑机制、构建产物目录组织。
- 影响：P3 的 KG+RAG 走自建的「实体链接 + Cypher 遍历 + 向量/稀疏融合」路径，而非社区摘要检索。

### ADR-012 复用参考项目的三项非代码资产

- 状态：accepted（2026-08-31）
- 参考项目：`E:\Essay_Analysis_Agent\数据处理`（医疗 KG，Neo4j + 微软 GraphRAG + LangChain + ragas）。
- 决策：复用其**方法论资产**，重写其**代码资产**。
  1. 抽取 prompt 骨架 → `docs/EXTRACTION_PROMPT_DESIGN.md`（证据溯源、消歧决策树、标准化表、自检清单、空值原则）
  2. 五维评分 rubric → `docs/EVAL_RUBRIC.md`（去掉医疗"安全性"，新增"引用正确性"与"冲突识别"）
  3. ragas 评测经验 → 评测集结构与 Evidence Recall 类指标设计
- 不复用：pdfplumber 解析链（丢失 page/表格/坐标）、医疗本体、`bge-small-zh-v1.5`（纯中文、512 维，不满足跨语言）、Neo4j 存向量的做法（已定 Qdrant）、硬编码密钥与 xlsx 中转的工程习惯。详见 ADR-011 与 README「参考项目评估」。

## 仍待确认

| 编号 | 事项 | 说明 | 阻塞什么 |
| --- | --- | --- | --- |
| D5a | LongCat 模型 ID | 以 `GET /v1/models` 为准，需确认具体名称与是否支持 JSON 结构化输出 | P1 首日 |
| D4 | 编排框架 | 延后至 P5 决定（LangGraph / 自研状态机）；P1–P4 只按接口预留 | P5 |
| D7 | 对象存储 | 默认本地文件系统，规模上来再换 MinIO | 不阻塞 |

## ADR 模板

```text
### ADR-00X <标题>
- 状态：proposed / accepted / superseded
- 日期：
- 背景：
- 备选方案：
- 决策：
- 影响与代价：
```
