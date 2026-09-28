# Evidence-Grounded Literature Research Agent

面向科研调研的证据驱动论文 Agent。设计来源：`paper_research_agent_v2.md`。

当前阶段：**P0 骨架已完成，选型基本定稿**。

## 0. 技术栈（已定）

| 层 | 选型 | 决策 |
| --- | --- | --- |
| PDF 解析 | MinerU（magic-pdf） | ADR-001 |
| Dense 检索 | Qdrant | ADR-002 |
| 稀疏检索 | BM25s（落盘索引） | ADR-002 |
| 图存储 | Neo4j | ADR-003 |
| 关系数据 | SQLite -> 可切 Postgres | ADR-005 |
| LLM | LongCat API（`api.longcat.chat/openai/v1`，仅 chat，无 embedding） | ADR-006 |
| Embedding | BAAI/bge-m3 本地（1024 维，同时出 sparse） | ADR-007 |
| Reranker | BAAI/bge-reranker-v2-m3 本地 | ADR-007 |
| 跨语言策略 | 中文 query→Dense；英文改写式→BM25；bge-sparse 对冲 | ADR-008 |
| 编排 | **延后至 P5 决定**（LangGraph / 自研），当前仅预留接口 | D4 |
| 前端 | FastAPI（REST + SSE） + Vue3 + Element Plus + pdfjs | ADR-009 |
| 运行环境 | `dev_cpu`（无 GPU 开发机）/ `gpu_8g`（8GB 4060 部署机）双 profile | ADR-010 |
| 对象存储 | 本地文件系统 -> 可换 MinIO | D7 |

依赖服务：`docker compose up -d` 启动 Qdrant + Neo4j；`LITAGENT_PROFILE` 切换环境档位。详见 `docs/DECISIONS.md`。

---

## 1. 可行性分析

### 1.1 结论

整体可行，但原文档 7 个 Phase 的工作量对一个个人项目过大。建议按「**一条纵向闭环优先，再逐层加宽**」推进：先让 10~20 篇 PDF 跑通
`解析 -> 抽取 -> 审核 -> 索引 -> 检索 -> 带引用回答` 的最小闭环，再补 KG、路由、Research Agent。

### 1.2 主要风险与对策

| 风险 | 等级 | 说明 | 对策 |
| --- | --- | --- | --- |
| PDF 解析质量（表格/公式/图表） | 高 | 表格错乱会直接摧毁 Evidence 与后续冲突检测 | 起步先用成熟解析器产出结构化 JSON + 保留 `page/bbox`；表格以 HTML/Markdown 双份存储，核对后再入 KG |
| 证据定位精度 | 高 | 「可追溯」是项目立身之本，页码错一位就失分 | 抽取时强制输出 `page + section + char_span/bbox`，入库前做原文回查校验（span 命不中即判为低置信） |
| 实体归一 / 实体链接 | 中高 | `LoRA` vs `LoRA: Low-Rank Adaptation`、同一方法多种别名 | 维护 alias 表 + 向量相似度候选 + 低分转人工审核；不要指望一次性自动解决 |
| 冲突检测需要实验条件 | 中高 | 文档 §9 要求比较 Dataset/Backbone/Metric/Split/Year，但 §4 数据模型没有 `Result` / `ExperimentalCondition` | **必须在 Phase 2 补 `Result` + `Condition` 实体**，否则 Phase 5 冲突检测无法落地（见 §3 数据模型待补） |
| 人工审核环节成本 | 中 | 文档 Pipeline 中 Human Review 是必需节点，但做 UI 很贵 | MVP 用脚本/命令行或极简页面过审；审核结果落库即为后续训练数据 |
| 评测集构建 | 中 | 文档 §11 指标很多，全做会拖慢主线 | P1 先建 30 条「问题 -> 证据 gold」小集，只测 Recall@K + 引用正确率；其余指标随 Phase 递增 |
| Deep Research 成本/延迟 | 中 | 多轮子问题 + 并行检索，token 与耗时易失控 | 限制子问题数、每问证据上限、全局 budget；State 只存 ID（遵循 §6） |
| 增量更新 / 后训练（Phase 6/7） | 低优先 | 强依赖前序数据积累 | 前置条件满足后再启动，先只预留接口与目录 |

### 1.3 需要提前确认的两个设计缺口

1. **缺 `Result` / `ExperimentalCondition` 模型**：冲突检测的比较维度（Dataset/Backbone/Metric/Split/Setting/Year）无处安放。
2. **缺「LLM 抽取的置信度 + 溯源校验」字段**：Validation 阶段需要可判定规则（原文 span 命中率、schema 校验、实体链接分数），建议每个抽取对象带 `confidence` 与 `extraction_run_id`，便于回滚与人工抽样。

---

## 2. 项目结构

```text
Essay_Analysis_Agent/
├── paper_research_agent_v2.md      # 原始设计文档（需求源）
├── README.md                       # 本文件：可行性 + 进度清单
├── pyproject.toml                  # 依赖与工具配置（分组，未安装）
├── docker-compose.yml              # Qdrant + Neo4j
├── .env.example                    # 环境变量样例
├── configs/
│   ├── app.yaml                    # 服务/日志/路径
│   ├── models.yaml                 # LLM / Embedding / Reranker 配置
│   ├── ingestion.yaml              # 解析与抽取 Pipeline 配置
│   └── retrieval.yaml              # 检索/融合/重排参数
├── data/
│   ├── raw_pdfs/                   # 原始 PDF（唯一事实源，只读）
│   ├── parsed/                     # 解析产物（text/table/figure + 坐标）
│   ├── assets/                     # 图片 / 表格 HTML 等大对象
│   ├── index/                      # BM25s 落盘索引
│   └── eval/                       # 离线评测集
├── docs/
│   ├── DECISIONS.md                # ADR 决策记录 + 待确认项
│   └── DATA_MODEL.md               # 领域模型定义（含 Result / Condition 补齐）
├── scripts/                        # 入口脚本（后续实现）
├── web/                            # 前端（RuoYi 或独立 Vue，P2 再初始化）
├── tests/
└── src/litagent/
    ├── core/                       # config / logging / registry / errors
    ├── domain/                     # 领域模型（Pydantic）：Paper/Method/Dataset/Task/
    │                               #   Metric/Result/Condition/Claim/Evidence/Relation
    ├── storage/                    # 存储抽象：relational / vector / graph / object
    ├── ingestion/                  # 入库 Pipeline
    │   ├── parsers/                # PDF 文本/表格/图片解析适配
    │   ├── extractors/             # LLM 结构化抽取（metadata/methods/claims/results）
    │   ├── validators/             # schema/实体归一/溯源校验
    │   ├── review/                 # 人工审核队列
    │   └── indexers/               # chunk / dense / bm25 / kg 写入
    ├── retrieval/                  # dense / bm25 / kg / fusion(RRF) / rerank
    ├── agent/                      # router / planner / state / nodes / tools / graph
    ├── synthesis/                  # 证据绑定 / 引用 / 跨论文比较 / 冲突检测 / 报告
    ├── evaluation/                 # 评测集加载 + 指标 + 运行器
    ├── training/                   # SFT/DPO 数据构建（Phase 7，仅占位）
    └── api/                        # HTTP 接口（FastAPI 或等价，待确认）
```

设计约定（来自文档 §3/§6/§16）：

- **原始 PDF 是最终证据源**，LLM 摘要不作为事实源。
- **每条关系可回溯到 Evidence**；State 只存 ID，不存大对象。
- 存储、LLM、检索一律走**接口 + 配置注入**，便于更换实现（选型尚未定稿）。

---

## 3. 实施进度清单

状态图例：`[ ]` 未开始 / `[~]` 进行中 / `[x]` 完成

### P0 骨架与选型（当前）

- [x] 可行性分析 + 风险清单
- [x] 项目骨架目录 + 配置文件 + docker-compose + ADR 记录
- [x] 技术选型主项确认（MinerU / Qdrant+BM25s / Neo4j / 云端 API 优先）
- [x] 领域模型 schema 草案（`docs/DATA_MODEL.md`，含新增 `Result`、`Condition`）
- [x] 双环境 profile 设计（无 GPU 开发机 / 8GB GPU 部署机）
- [x] 前端方案定稿 + SSE 事件协议 + 目录约定（`docs/FRONTEND.md`）
- [ ] 确认 LongCat 模型 ID 与 JSON 结构化输出能力
- [ ] `pyproject.toml` 依赖锁定具体版本 + 安装，起 Qdrant/Neo4j 验证连通性
- [ ] 在 GPU 机跑 MinerU 解析 10 篇种子论文，产物同步回开发机
- [ ] 验证 bge-m3 本地加载（CPU 档）与建索引耗时
- [ ] 建中文 query 评测集（≥30 条，含 gold evidence），验证跨语言三路召回

### P1 Evidence Layer（最小闭环）

**P1.1 环境就绪**

- [x] Python 3.12 核心开发环境、环境检查脚本与 Windows 锁文件
- [~] parsing + retrieval + graph + llm + local-models 依赖（按对应节点安装）
- [ ] `docker compose up -d` 起 Qdrant + Neo4j，验证连通性
- [ ] 核对 LongCat `/v1/models` 模型 ID，实测 `json_object` 结构化输出
- [ ] bge-m3 CPU 档加载验证，记录单条 encode 耗时

**P1.2 解析与领域模型**

- [x] Pydantic 领域模型：`Paper` / `Section` / `Chunk` / `Evidence` / `Claim` / `Result` / `Condition` / 抽取与审核记录
- [ ] MinerU 解析 10 篇种子论文（GPU 机执行），产出 md + json + bbox，同步回开发机
- [ ] 分块：section 优先，表格整体不切，chunk 头附 title/section 路径

**P1.3 抽取与校验**

- [ ] 抽取 prompt + JSON schema（metadata / claims / evidence）
- [ ] span 回查原文校验，不命中则降置信
- [ ] SQLite 落库 + 审核队列表（低置信对象入队）

**P1.4 检索**

- [ ] bge-m3 dense + sparse 写入 Qdrant；BM25s 建索引
- [ ] `query_rewrite`：中文 query → 英文检索式（BM25 硬约束）+ 术语保护表
- [ ] 三路 RRF 融合；GPU 档开启 bge-reranker-v2-m3

**P1.5 问答与评测**

- [ ] CLI 问答，答案带 `[Paper, Page/Section/Table]` 引用
- [ ] 埋好 `step` / `citation` 事件结构（P2 接 SSE 时零改动）
- [ ] 30 条中文 query 评测集（含 gold evidence）+ Recall@K / 引用正确率

**出口标准**：10 篇入库，中文事实类问题能命中原文位置并给出可点击级引用；评测 Recall@10 ≥ 基线值（首轮自测后设定）。

### P2 最小 KG

- [ ] `Method` / `Dataset` / `Task` / `Metric` / `Result` / `Condition` 实体与关系
- [ ] 实体别名词表 + 实体链接（低分转人工）
- [ ] 人工审核最小流程（脚本/极简页面），审核记录落库
- [ ] 关系 -> Evidence 绑定校验

**出口标准**：可回答「哪些论文在数据集 X 上比较了 A 与 B」。

### P3 KG + RAG

- [ ] 实体/关系理解（query -> entity+relation）
- [ ] KG 遍历召回候选论文/claim
- [ ] KG 结果与 Dense/BM25 融合排序
- [ ] 评测集扩到「关系型问题」

### P4 Query Router

- [ ] 三档路由：Simple RAG / KG+RAG / Deep Research
- [ ] 路由准确率评测 + 误路由样本回收

### P5 Research Agent

- [ ] LangGraph（或选定框架）State + Checkpoint
- [ ] Planner / 子问题分解 / 并行工具调用
- [ ] 跨论文比较 + 冲突检测（按 Dataset/Backbone/Metric/Split/Year 对齐）
- [ ] Gap analysis + 证据驱动报告生成（结论/依据/条件/不确定性）
- [ ] 成本控制（子问题数、证据上限、token budget）

### P6 Incremental Update

- [ ] 新论文增量解析与索引
- [ ] 实体链接到已有 KG
- [ ] 已有 Claim 影响检查（支持 / 反驳 / 补充 / 新增 / 演化）

### P7 Post-training（依赖前序失败样本）

- [ ] 失败样本采集与分类（rewrite / tool / evidence / planning）
- [ ] Query Rewrite SFT、Tool-use SFT、Evidence preference、Trajectory 数据构建
- [ ] Qwen3-8B：prompt-only baseline -> LoRA -> QLoRA -> +PO
- [ ] 任务能力 vs 通用能力漂移评估

---

## 4. 参考项目评估：`数据处理/`（医疗知识图谱）

来源：`E:\Essay_Analysis_Agent\数据处理`，医疗方向，技术栈 Neo4j + 微软 GraphRAG + LangChain + ragas + FastAPI。

**结论：借鉴性中高 —— 方法论值得抄，代码基本要重写。**

### 可直接借鉴（已沉淀到本项目）

| 资产 | 借鉴点 | 落点 |
| --- | --- | --- |
| `提取jsonl格式的提示词.md` | Chunk 溯源节点 + `SOURCED_FROM` 关系、消歧决策树、实体标准化表、GRADE 证据分级、自检清单、"宁缺毋造"原则 | `docs/EXTRACTION_PROMPT_DESIGN.md` |
| `大模型评分标准-提示词版.txt` | 五维 1–5 分 rubric，每档有明确锚定定义（尤其"溯源性"维度） | `docs/EVAL_RUBRIC.md` |
| `evaluation/ragas_eval/` | RAG 评测集组织与 Evidence 级指标思路 | `docs/EVAL_RUBRIC.md` |
| `build_kg.py` 的 `node_to_text` | 把节点属性拼成可检索文本 | 用于 Paper Card 生成 |

### 不能直接用

1. **医疗本体**（21 类实体 / 25 种关系）全部作废，替换为论文本体。
2. **pdfplumber 解析链**：只提纯文本，丢失页码/表格/坐标；evidence 是 LLM 抄写的句子，无法回查原文 —— 与本项目立身之本冲突，已由 MinerU 替代。
3. **微软 GraphRAG 社区摘要**：以 LLM 摘要替代原文，违背"原始 PDF 为事实源"，且不保留原文定位（ADR-011）。
4. **`bge-small-zh-v1.5`**（512 维、纯中文）不满足中英跨语言需求，已定 bge-m3。
5. **工程习惯**：硬编码 API Key、硬编码远程库地址、xlsx 手工中转、无配置化 —— 需全部重来。

### 方向选择的额外收益

选「多模态情感识别」作种子论文对本项目验证有利：数据集（MOSI/MOSEI/IEMOCAP/MELD/CH-SIMS）与指标（Acc-2/F1/MAE/Corr）高度标准化，实体归一成本远低于医疗领域；对比实验表格密集，正好充分验证 `Result` + `Condition` 模型与 P5 冲突检测；中文数据集（CH-SIMS）与英文论文并存，天然检验跨语言策略。

> ⚠️ 安全提醒：`数据处理/导入图谱的提示词.txt` 中**明文硬编码了 DeepSeek API Key**（注释中还有通义 Key）。该目录若纳入 Git 管理，请先清理并到平台作废该 Key。

---

## 5. 剩余待确认

详见 `docs/DECISIONS.md` 末尾表格：LongCat 模型 ID 与 `json_object` 支持（P1 首日阻塞）、编排框架（P5）、对象存储（不阻塞）。
