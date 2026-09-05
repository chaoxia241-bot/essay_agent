# Paper Agent V2 开发与迁移计划

本计划把设计文档中的终局架构，拆成适合“无 GPU 工作电脑 + RTX 4060 8GB 个人笔记本”的可交付阶段。

## 1. 约束与分工

### 工作电脑：CPU 开发环境

适合完成：

- 领域模型、SQLite/Neo4j/Qdrant 接口和配置系统
- PDF 解析适配器、分块、证据定位校验等 CPU 逻辑
- BM25、查询改写、RRF、路由、引用格式化
- 单元测试、回归测试、评测脚本、文档和前端/API
- 使用云端 LLM 做少量结构化抽取和综合

不把工作电脑作为批量 MinerU、Embedding、Reranker 的主执行机。

### 个人笔记本：RTX 4060 8GB

适合完成：

- MinerU 批量解析论文
- BGE-M3 Embedding 建库/增量更新
- BGE Reranker 小批量重排
- 小规模离线评测和性能对比

8GB 显存按小 batch、FP16、可恢复批处理设计；LLM 仍优先使用云端 API，不把本地 8B 模型作为主链路前置条件。

## 2. Git 中提交什么

提交：源代码、配置模板、Prompt、数据库迁移、测试、评测规范、小型脱敏 fixture、设计文档。

不提交：原始 PDF、解析后的大文件、向量/倒排索引、SQLite/Neo4j 数据目录、模型缓存、完整医疗参考数据、任何 API Key。

`数据处理/` 仅作为本地参考资产，借鉴其中的抽取 Prompt、溯源关系和评测思路；不作为新系统代码直接导入。

## 3. 开发阶段与出口标准

### 阶段 0：仓库安全与可迁移基线

- 配置 `.gitignore`，完成敏感信息扫描
- 将工作电脑和个人笔记本分别配置独立 SSH Key
- 初始化 Git，建立 `main` 与功能分支约定
- 固定 Python、Docker、MinerU、BGE 模型版本
- 提供 `.env.example`，真实 `.env` 只保留在本机

出口：仓库可以安全克隆，任何机器都能按文档生成本地配置。

### 阶段 1：Evidence Layer 最小闭环

顺序固定为：

1. `Paper / Chunk / Evidence / Claim / Result / Condition` 模型
2. SQLite 元数据与溯源表
3. MinerU 适配器和 section-first chunker
4. span/page/section 回查校验
5. Dense + BM25s + RRF 检索
6. CLI 问答与 `[论文, 页码, 章节]` 引用
7. 30 条中文问题的 Recall@K、引用正确率评测

出口：10 篇种子论文可以入库，事实型问题能回到原文证据。

### 阶段 2：最小知识图谱

- Method、Dataset、Task、Metric、Result、Condition
- Alias 表和实体链接
- 低置信度人工审核队列
- 每条关系绑定 Evidence/Provenance

出口：能回答“哪些论文在数据集 X 上比较了 A 与 B”，且答案可回溯。

### 阶段 3：KG-guided RAG

- Query 实体链接
- KG 邻居扩展与候选论文过滤/加权
- KG 结果与 Dense/BM25 融合
- 增加关系型问题评测

出口：相对于纯 Hybrid RAG，关系型问题的召回和引用正确率有可记录的变化。

### 阶段 4：Wiki 与查询路由

先做 Method/Concept 两类 Wiki：

- Wiki Planner 根据 KG Delta 决定创建/更新/跳过
- Compiler 只生成有 Evidence 的段落
- Revision/Diff/Verifier 后再提交
- Simple RAG、KG+RAG、Deep Research 三档路由

出口：Wiki 是可复用的知识对象页面，不是无溯源的论文摘要。

### 阶段 5：Research Agent 与增量更新

最后再加入 Planner、子问题分解、Checkpoint、Execution Record、幂等、重试、限流、冲突检测和新论文增量更新。

后训练暂不排期，必须等前面产生真实失败样本后再决定是否 LoRA/QLoRA。

## 4. 工作节奏

### 碎片时间：工作电脑

每次 25–60 分钟，优先做一个可以独立提交的任务：模型字段、接口、测试、Prompt、文档、评测样本、bug 修复。避免在碎片时间启动长时间解析或建库。

### 集中时间：个人笔记本

每周安排 1–2 次 GPU 批处理：解析一批论文、生成 Embedding、跑重排和评测；结果通过 Git 之外的本地同步方式迁移，Git 只同步 manifest、版本和评测摘要。

### 每周结束

- 工作电脑：合并可运行代码并推送
- 个人笔记本：拉取代码，执行 GPU 批处理，保存结果摘要
- 两台机器：确认模型版本、配置版本和数据 manifest 一致

## 5. 两台电脑迁移规则

- 代码、配置模板和 Prompt：Git 同步
- 原始 PDF、解析 JSON、索引、数据库：本地数据目录或加密硬盘同步
- 模型缓存：两台机器分别缓存，不通过 Git 同步
- 结果目录使用 `manifest.json` 记录 `paper_id`、文件哈希、解析版本、Embedding 版本和时间
- 迁移前先提交代码，再迁移数据；迁移后先跑 smoke test，再跑批处理

推荐分支：`main` 保持可运行；`feature/p1-evidence`、`feature/p2-kg`、`feature/p3-kg-rag` 分阶段开发，完成评测后合并。

## 6. 推送前检查清单

1. 撤销并更换历史参考目录中曾出现的 API Key。
2. 确认 `git status` 中没有 `.env`、私钥、PDF、索引或数据库。
3. GitHub 账户同时添加工作电脑和个人笔记本的 SSH 公钥，分别命名。
4. 两台电脑分别执行 SSH 测试，再设置同一个 SSH remote alias。
5. 首次推送前先 `fetch` 检查远程是否已有提交；远程非空时先合并，不覆盖远程历史。
