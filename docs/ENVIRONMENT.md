# P1 环境基线

## 支持范围

- Python：3.11 或 3.12；项目默认 3.12
- 工作电脑：CPU 开发、领域模型、测试、配置与轻量流程
- 个人笔记本：RTX 4060 8GB，承担 MinerU、Embedding、Reranker
- 原始论文目录：papers/，其中的 PDF 不进入 Git

## 当前工作电脑检查

检查日期：2026-09-05。

| 项目 | 状态 | 说明 |
| --- | --- | --- |
| Python base | 不采用 | 3.13.9，超出项目支持范围 |
| Conda dev | 采用 | Python 3.12.13 |
| 论文目录 | 通过 | papers/ 中有 10 篇 PDF |
| Docker | 阻塞集成 | 当前 PATH 中无 Docker；不阻塞领域模型开发 |
| GPU | 不要求 | 工作电脑按 dev_cpu profile 运行 |

## 创建本地开发环境

~~~powershell
C:/Users/Administrator/.conda/envs/dev/python.exe -m venv .venv
./.venv/Scripts/python.exe -m pip install --upgrade pip
./.venv/Scripts/python.exe -m pip install -r requirements-dev-win.lock
./.venv/Scripts/python.exe -m pip install -e . --no-deps
~~~

运行检查：

~~~powershell
./.venv/Scripts/litagent-env-check.exe
./.venv/Scripts/python.exe -m pytest
~~~

Docker 安装后再验证 Qdrant；它不作为 P1-02 领域模型的前置条件。
