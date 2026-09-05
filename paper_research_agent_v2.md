# Evidence-grounded Literature Research Agent V2

> 定位：不是简单的“论文 PDF 问答”，而是一个面向科研调研的、证据可追溯的 Literature Research Agent。

## 1. 项目定位

### 核心问题

研究者面对多个论文来源时，经常需要重复完成：

- 检索相关论文
- 从 PDF 正文、表格、图片中定位证据
- 提取方法、数据集、实验结果等结构化信息
- 横向比较多篇论文
- 核验结论与原文证据
- 整理引用并形成研究总结
- 新论文出现后重新判断已有结论是否仍成立

### 核心价值

系统不与通用 ChatGPT/Claude 的“单篇 PDF 对话”能力直接竞争，而是提供：

1. **论文集合级研究**：围绕一个研究问题跨多篇论文检索和综合。
2. **结构化科研知识**：将 Paper、Method、Dataset、Task、Metric、Claim、Evidence 等组织起来。
3. **证据可追溯**：每个关键结论能够回溯到论文、页码、Section、Table/Figure 或原始文本。
4. **持续更新**：新论文加入后增量索引，并可检测已有知识/结论的潜在冲突。
5. **复杂度路由**：简单事实查询走快速 RAG；需要比较、多跳推理或全局研究的问题走 Research Agent。

---

## 2. 总体架构

```text
                         User Query
                             |
                     Query Understanding
                             |
                      Query Router
                    /                 \
              Simple Query          Research Query
                  |                      |
                  v                      v
             Hybrid RAG            Research Planner
                                        |
                              Query Decomposition
                                        |
                        +---------------+---------------+
                        |               |               |
                        v               v               v
                  Concept Search   Method Search   Evidence Search
                        |               |               |
                        +---------------+---------------+
                                        |
                               Hybrid Retrieval
                                        |
                         +--------------+--------------+
                         |              |              |
                       Dense          BM25        Knowledge Graph
                         |              |              |
                         +--------------+--------------+
                                        |
                                  Candidate Fusion
                                       / \\
                                   RRF / Merge
                                        |
                                    Reranker
                                        |
                               Evidence Filtering
                                        |
                              +---------+---------+
                              |                   |
                              v                   v
                       Text Evidence      Table/Figure Evidence
                              |                   |
                              +---------+---------+
                                        |
                              Claim Verification
                                        |
                         +--------------+--------------+
                         |                             |
                  Cross-paper Compare             Conflict Detection
                         |                             |
                         +--------------+--------------+
                                        |
                                  LLM Synthesis
                                        |
                            Citation / Evidence Binding
                                        |
                                 Research Report
```

---

## 3. 论文知识入库 Pipeline

```text
PDF
 |
 +--> Text Extraction
 |
 +--> Table Extraction
 |
 +--> Figure/Image Extraction
 |
 v
Multimodal Normalization
 |
v
LLM Structured Extraction
 |
 +--> Metadata
 +--> Methods
 +--> Models
 +--> Tasks
 +--> Datasets
 +--> Metrics
 +--> Claims
 +--> Results
 +--> Evidence
 +--> Entities / Relations
 |
v
Validation
 |
 +--> Schema validation
 +--> Entity normalization
 +--> Relation validation
 +--> Source/evidence verification
 |
v
Human Review
 |
 +------------------------------+
 |                              |
 v                              v
Approved Document Objects    Approved KG Facts
 |                              |
 v                              v
Chunk / Paper Card          Knowledge Graph
 |
 v
Dense Index + BM25 Index
```

### 设计原则

- 原始 PDF 是最终证据源，不把 LLM 摘要当作事实源。
- KG 中的关键关系必须能够回溯到 Evidence。
- 对低置信度关系进行人工审核。
- 大型原始文件、图片和长结果不直接塞进 Agent State；使用 document_id / evidence_id / object storage 引用。

---

## 4. 核心数据模型

### 4.1 Paper

```text
Paper
- paper_id
- title
- authors
- year
- venue
- abstract
- doi/arxiv_id
- document_uri
```

### 4.2 Method

```text
Method
- method_id
- canonical_name
- aliases
- description
```

### 4.3 Dataset / Task / Metric

用于结构化实验和条件检索。

### 4.4 Claim

```text
Claim
- claim_id
- statement
- claim_type
- confidence
- conditions
```

### 4.5 Evidence

```text
Evidence
- evidence_id
- paper_id
- type: text | table | figure
- page
- section
- chunk_id
- content
- source_uri
```

### 4.6 Relation

推荐起步关系：

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

关键原则：

```text
Relation
   |
   +--> Evidence
```

不能只保存“X improves Y”，而要保存“哪个论文、哪个实验条件、哪段/哪张表支持 X improves Y”。

---

## 5. 查询路由

### Simple RAG

适合：

```text
“这篇论文用了什么 backbone？”
“QLoRA 使用什么量化方法？”
```

流程：

```text
Query
 -> Query Rewrite
 -> Dense + BM25
 -> RRF
 -> Reranker
 -> Evidence
 -> LLM
```

### KG + RAG

适合：

```text
“哪些方法是在 LoRA 基础上继续改进的？”
“哪些论文比较了 A 和 B？”
```

流程：

```text
Query
 -> Entity/Relation Understanding
 -> KG Traversal
 -> Related Papers / Claims
 -> Dense/BM25 Evidence Retrieval
 -> Rerank
 -> LLM
```

### Deep Research Agent

适合：

```text
“从 2021 到 2026，LLM 参数高效微调的技术演化路线是什么？
 哪些方向已经形成共识，哪些仍存在争议？”
```

流程：

```text
Research Question
 -> Planner
 -> Sub-question decomposition
 -> Parallel retrieval
 -> Evidence extraction
 -> Cross-paper comparison
 -> Contradiction detection
 -> Gap analysis
 -> Synthesis
 -> Evidence-grounded report
```

---

## 6. Research Agent 的 State 设计

State 不等于数据库；只保存“继续当前 workflow 所需要的信息”。

推荐：

```text
ResearchState
├── conversation/messages
├── research_question
├── sub_questions
├── current_plan
├── current_step
├── retrieved_evidence_ids
├── candidate_paper_ids
├── selected_claim_ids
├── comparison_results
├── conflicts
├── tool_results（必要时保留，过大则只存引用 ID）
├── draft_report
└── status
```

不建议直接保存：

```text
- 整篇 PDF 二进制
- 数十 MB 图片
- 超大检索结果
- 大型 embedding matrix
- 可从数据库重新读取的冗余数据
```

---

## 7. Memory / Persistence

### Short-term

当前 conversation / research workflow：

```text
messages
plan
current_step
tool results
selected evidence
```

使用 LangGraph State + Checkpoint。

### Long-term

跨 conversation：

```text
user preferences
favorite topics
research interests
saved papers
persistent notes
```

使用 Store / DB。

### Knowledge

论文公共知识：

```text
Paper KG
Vector DB
BM25
Object Storage
```

不要把长期知识全部塞进 State。

---

## 8. 证据驱动回答

最终报告不应只是：

```text
LLM -> answer
```

而应该近似：

```text
Claim
 |
 +--> Evidence A -> Paper A / Page / Section / Table
 |
 +--> Evidence B -> Paper B / Figure
 |
 v
Synthesis
```

输出结构建议：

```text
结论

依据：
[Paper A, Table 3]
[Paper B, Section 4.2]

条件：
Dataset / Backbone / Metric / Setting

不确定性/冲突：
Paper C reports a different result under another setting.
```

---

## 9. Conflict Detection

知识图谱可以帮助发现：

```text
Paper A:
A > B on Dataset X

Paper B:
B > A on Dataset Y
```

不要让 LLM 直接生成：

```text
“A generally outperforms B.”
```

应该比较：

```text
Dataset
Backbone
Metric
Data split
Training setting
Year
```

最终输出：

```text
两篇论文存在表面冲突，但实验条件不同，因此不能直接得出全局结论。
```

---

## 10. Incremental Update

新论文加入后：

```text
New Paper
 -> Parse
 -> Structured Extraction
 -> Entity Linking
 -> Relation Extraction
 -> Evidence Validation
 -> Human Review
 -> Incremental Index
 -> KG Update
 -> Existing Claim Impact Check
```

重点不是“重新建库”，而是判断：

```text
新论文是否：
- 支持旧 Claim
- 反驳旧 Claim
- 补充旧 Claim
- 提出新 Method
- 引入新 Dataset
- 改变某个技术演化关系
```

---

## 11. 评测体系

项目不能只测“回答看起来不错”。建议建立离线评测集。

### Retrieval

```text
Recall@K
MRR
NDCG@K
Evidence Recall
```

### Reranking

```text
NDCG@K
MRR
Relevant@K
```

### Generation

```text
Answer correctness
Faithfulness
Citation correctness
Citation completeness
Evidence attribution accuracy
```

### Agent

```text
Tool selection accuracy
Argument accuracy
Task completion rate
Research plan quality
Sub-question coverage
```

### System

```text
Latency
Token consumption
Cost / query
Checkpoint size
Index update latency
```

---

## 12. 后训练结合点

后续模型微调不要“看到效果不好就 SFT”，而是根据失败类型选择训练方式。

```text
Query Rewrite
 -> SFT + LoRA/QLoRA

Tool Calling
 -> Tool-use SFT

Evidence Selection
 -> Preference / Ranking / DPO

Research Planning
 -> Trajectory SFT / Preference

Deep Research Policy
 -> Preference Optimization / RL（成熟后再做）
```

---

## 13. 与后续 Qwen3-8B 实验结合

推荐实验路径：

```text
Base Qwen3-8B
      |
      +--> Prompt-only baseline
      |
      +--> LoRA SFT
      |
      +--> QLoRA SFT
      |
      +--> SFT + Preference Optimization
      |
      v
Agent Evaluation
```

分别测：

```text
Query Rewrite
Tool Selection
Evidence Selection
Research Planning
Final Answer
General Capability
```

尤其关注：

```text
Task capability ↑
General capability ↓ ?
```

从而研究如何通过：

```text
Data mixture
Learning rate
Training duration
LoRA capacity
Preference optimization
Reference-model constraints
```

减少能力漂移。

---

## 14. 推荐的 V2 开发顺序

### Phase 1：Evidence Layer

完成：

```text
Paper
Claim
Evidence
Paper Card
```

目标：每个关键结论都有可定位的来源。

### Phase 2：最小 KG

先做：

```text
Paper
Method
Dataset
Task
Metric
Claim
Evidence
```

不要一开始追求复杂本体。

### Phase 3：KG + RAG

实现：

```text
Entity linking
KG traversal
Evidence retrieval
Hybrid fusion
```

### Phase 4：Query Router

实现：

```text
Simple -> RAG
Relational -> KG + RAG
Complex -> Research Agent
```

### Phase 5：Research Agent

加入：

```text
Planner
Sub-question decomposition
Parallel tool calls
Cross-paper comparison
Conflict detection
```

### Phase 6：Incremental Research

实现新论文加入后的：

```text
KG update
Index update
Claim impact analysis
```

### Phase 7：Model Post-training

以真实 Agent failure cases 构建：

```text
Query Rewrite SFT dataset
Tool-use SFT dataset
Evidence preference dataset
Research trajectory dataset
```

---

## 15. 简历定位

### 中文

> 面向科研调研的证据驱动论文 Research Agent：构建多模态论文解析与结构化知识抽取 Pipeline，对正文、表格和图像进行统一解析，经人工审核后构建论文知识库及知识图谱；采用 Query Rewrite、Dense + BM25 Hybrid Retrieval、RRF、Reranker 实现高召回检索，并基于查询复杂度动态路由简单 RAG 与多跳 Research Agent，支持跨论文证据抽取、方法对比、冲突检测及带原文定位的引用生成；同时支持新论文增量索引与知识更新。

### 英文标题

> Evidence-Grounded Literature Research Agent

### 英文描述关键词

```text
Multimodal PDF Parsing
Hybrid Retrieval
Dense Retrieval
BM25
RRF
Reranking
Knowledge Graph
Evidence Grounding
Claim Verification
Conflict Detection
Incremental Indexing
LangGraph
LLM Post-training
LoRA / QLoRA
```

---

## 16. 设计原则总结

```text
RAG：找到相关证据
KG：表达和导航关系
Evidence Layer：保证结论可追溯
Agent：决定研究步骤和工具调用
State：保存当前 workflow 所需上下文
Checkpoint：保证 workflow 可恢复
Memory：管理跨轮次/跨任务的信息
LLM：完成理解、抽取、比较和综合
Fine-tuning：改变稳定行为，而不是代替知识库
```

最终目标：

> 从“论文问答 Demo”升级为“可以围绕研究问题自主检索、组织、验证和综合论文证据的 Research Agent”。
