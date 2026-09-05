# 前端方案：FastAPI + Vue3 自建（ADR-009 定稿）

> 状态：accepted（2026-08-31）
> P1 不实现前端，先把接口协议与目录约定定下来，避免 P2 返工。

## 技术栈

**后端**：FastAPI + SSE（`sse-starlette` 支持 `Last-Event-ID` 断线重连）+ Pydantic v2
**前端**：Vue3 + TypeScript + Vite + Element Plus + Pinia + vue-router
**辅助**：`pdfjs-dist`（原文定位与高亮）、`markdown-it`（报告渲染）、`vis-network` 或 AntV G6（P3 KG 可视化）

## 后端接口约定（`src/litagent/api/`）

```text
POST   /api/papers                     上传 PDF 并触发入库
GET    /api/papers                     论文列表（含解析/入库状态）
GET    /api/papers/{paper_id}          论文详情（Paper Card）

GET    /api/review/queue               人工审核队列（低置信抽取对象）
POST   /api/review/{object_id}         approve / reject / 修正

POST   /api/chat                       SSE 流式问答（三档路由自动选择）
GET    /api/evidence/{evidence_id}     证据详情（原文片段 + page/section/bbox）
GET    /api/papers/{paper_id}/file     原始 PDF 流（供前端 pdf.js 渲染）

GET    /api/graph/subgraph             P3 起：KG 子图（论文/方法/数据集关系）
POST   /api/eval/run                   离线评测触发（P1 末）
```

## SSE 事件协议

流式不再是纯 token 流，需要携带引用与过程信息：

| 事件 | 载荷 | 用途 |
| --- | --- | --- |
| `step` | `{name, status, detail}` | 展示中间过程：路由判定 / 查询改写 / 检索 / 重排 / 冲突检测 |
| `token` | `{text}` | 增量文本 |
| `citation` | `{evidence_id, paper_id, page, section, type, snippet}` | 引用块，前端渲染为可点 chip |
| `done` | `{answer_id, usage}` | 结束 |
| `error` | `{code, message}` | 异常 |

要点：

- **引用走独立事件，不混在 token 里解析**。LLM 输出中使用占位标记 `[[ev:xxx]]`，后端在流式时切分为 `token` + `citation`，前端无需正则猜。
- 每个事件带 `Last-Event-ID`，支持断线续传。
- 中间过程（`step`）从 P1 就输出，P5 接 Research Agent 时无需改协议。

## 引用交互设计（本项目最核心的 UI）

```text
答案正文 ... 该方法在 ImageNet 上提升 2.3%[1] ...
                                        ↑
                          点击 chip -> 抽屉展示原文片段 + 表格/图
                                        ↓
                        「跳转原文」-> pdf.js 打开 PDF 并定位到 page + 高亮 bbox
```

- chip 数据来自 `citation` 事件；点击后懒加载 `GET /api/evidence/{id}` 拿完整证据。
- 原文高亮依赖 `page + bbox + char_span`（来自 MinerU 与 `DATA_MODEL.md` 的约束），这是"证据可追溯"的最终落点。
- 表格证据用 Markdown/HTML 直接渲染，图片证据展示图 + 图注。

## 前端目录

```text
web/
├── index.html
├── vite.config.ts
├── src/
│   ├── api/            # SSE 客户端、REST 封装
│   ├── components/
│   │   ├── ChatStream.vue       # 流式消息 + step 折叠
│   │   ├── CitationChip.vue     # 引用 chip
│   │   ├── EvidenceDrawer.vue   # 证据抽屉（原文/表格/图）
│   │   └── PdfViewer.vue        # pdf.js 渲染 + bbox 高亮
│   ├── views/
│   │   ├── ResearchView.vue     # 主界面：对话 + 证据
│   │   ├── PapersView.vue       # 论文库管理
│   │   └── ReviewView.vue       # 人工审核队列（P2）
│   └── stores/
└── package.json
```

## 与后端的解耦原则

`src/litagent/api/` 只暴露 REST + SSE，不耦合任何前端框架。前端可独立开发，用 OpenAPI 生成的类型定义对接。

## 节奏

- P1：不实现前端，用 CLI 验证闭环（避免 UI 工作拖慢主线）。
- P2：实现 `PapersView` + `ReviewView`（审核队列是刚需）+ 最小 `ChatStream`。
- P5：完善 `step` 可视化与冲突检测结果展示。
