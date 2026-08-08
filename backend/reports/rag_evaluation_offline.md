# RAG 离线检索评测

- 运行配置：FakeEmbedding / MockReranker
- Collection：`tracecommerce_chunks_zh_cn`
- 样本数：16（可回答 12，必须拒答 4）
- Answerable Hit@K：1.0000
- Answerable MRR：0.8333
- 当前阈值无答案误放行数：0
- 推荐 `MIN_EVIDENCE_SCORE`：`0.1842`
- 阈值 Precision：1.0000
- 阈值 Recall：0.9167
- 阈值 F1：0.9565

> 这是离线 Fake/Mock 配置的基线，不代表真实 BGE 模型表现。切换模型、
> Collection 或知识版本后必须重新运行 `scripts/evaluate_rag.py`。

## 明细

| ID | Gold Hit | Evidence | Level | Sufficient |
|---|---:|---:|---|---:|
| markets-purpose | True | 0.3333 | low | True |
| tax-responsibility | True | 0.2156 | low | True |
| return-vs-refund | True | 0.2111 | low | True |
| partial-refund | True | 0.1429 | insufficient | False |
| hs-code | True | 0.2952 | low | True |
| ddp-requirements | True | 0.5111 | medium | True |
| local-currency-pricing | True | 0.3852 | medium | True |
| local-currency-gateway | True | 0.3061 | low | True |
| international-tools | True | 0.3893 | medium | True |
| tracking-missing | True | 0.6187 | medium | True |
| tracking-customer | True | 0.3000 | low | True |
| fulfillment-status | True | 0.1842 | low | True |
| out-poem | False | 0.0000 | insufficient | False |
| out-profit | False | 0.0370 | insufficient | False |
| out-live-order | False | 0.0526 | insufficient | False |
| out-mars | False | 0.1687 | insufficient | False |
