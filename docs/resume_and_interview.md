# 简历与面试说明

## 简历项目名称

面向跨境电商客服与运营的可追溯 RAG Agent 系统

## 项目描述参考

- 基于 FastAPI、LangGraph、PostgreSQL 和 Milvus 构建跨境电商知识问答系统，设计 13 个 Agent 节点及证据不足、空检索、引用失败和最多两次重检索分支。
- 实现 BGE-M3 Dense 与 Milvus Sparse 混合召回、Metadata Filter、BGE Reranker 精排和证据充分性判断；适配 Milvus 2.4 Sparse IP 与 2.5+ BM25，支持中英文查询。
- 设计可追溯回答协议，返回文档、原始 URL、真实 Chunk 片段、检索/Rerank 分数、置信度、request_id 和节点执行轨迹；引用无法支撑答案时强制 fallback。
- 实现 Shopify 白名单采集、本地多格式文档导入、结构化分块、内容哈希增量更新、JWT/RBAC、Alembic、Docker Compose 和 Fake 模型自动化测试。

## 两分钟介绍结构

1. 业务问题：跨境规则变化快，通用模型容易幻觉。
2. 数据：Shopify 官方帮助中心和本地企业文档。
3. 检索：跨语言 Dense + BM25 + Metadata Filter + Reranker。
4. Agent：LangGraph 条件分支、重写重试、风险检查和会话记忆。
5. 可追溯：真实 Chunk 引用和 request_id 全链路追踪。
6. 工程：FastAPI、PostgreSQL、Milvus、JWT/RBAC、Docker、测试。
7. 边界：公开短启动集用于验证，完整同步受 robots 和目标站访问策略约束。

## 高频追问

### 为什么不使用普通 Chain？

检索可能为空、证据可能不足、引用可能无效，需要条件分支、状态保存和有限重试。LangGraph 能显式表达这些状态迁移，并为每个节点生成执行轨迹。

### 为什么 Dense 和 BM25 都需要？

Dense 擅长跨语言语义召回，Sparse 检索对 HS code、VAT、DDP、国家名和产品编号等精确词更稳定。Milvus 2.5+ 使用 BM25，本机 2.4 使用确定性词法 Sparse Vector；混合检索降低单一路径漏召回风险。

### 如何防止 LLM 伪造引用？

LLM 只生成答案；引用由后端从真实检索 Chunk 构造。系统校验 chunk_id、URL 和 quoted_text 原文子串，任一不一致就设置 grounded=false 并 fallback。

### 为什么测试不用真实 LLM？

付费 LLM 会引入费用、网络和随机性，无法稳定回归。测试使用 FakeLLM、FakeEmbedding、MockReranker 和内存向量库，真实模型与 Milvus通过适配器和条件集成测试验证。

### 当前系统有什么不足？

公开启动数据规模小，Shopify 可能限制自动采集；生产还需要异步任务队列、PostgreSQL Checkpointer、租户权限、真实标注评测集、监控告警和灰度发布。
