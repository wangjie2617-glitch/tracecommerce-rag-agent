import {
  Activity,
  ArrowUp,
  BookOpen,
  Bot,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  Clock3,
  Database,
  ExternalLink,
  FileText,
  Fingerprint,
  Gauge,
  History,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Upload,
  UserRound,
  X
} from "lucide-react";
import {
  FormEvent,
  Fragment,
  KeyboardEvent,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import {
  clearSession,
  deleteDocument,
  getErrorMessage,
  getReadyStatus,
  getTrace,
  listConversations,
  listDocuments,
  listKnowledgeSources,
  loadSession,
  login,
  queryAgent,
  saveSession,
  submitFeedback,
  syncKnowledgeSource,
  uploadDocument
} from "./api";
import type {
  ChatAnswer,
  ChatMessage,
  ConversationSummary,
  KnowledgeDocument,
  KnowledgeSource,
  ReadyStatus,
  RequestTrace,
  TraceStep,
  User
} from "./types";

type View = "chat" | "knowledge" | "trace";

const INTENT_NAMES: Record<string, string> = {
  shipping: "物流配送",
  refund: "订单退款",
  return: "退货换货",
  payment: "跨境支付",
  duties_and_taxes: "关税税费",
  vat: "增值税",
  product: "商品问题",
  account: "账户问题",
  store_operation: "店铺运营",
  international_market: "国际市场",
  localization: "本地化",
  currency_pricing: "货币定价",
  policy: "政策规则",
  complaint: "投诉风险",
  out_of_scope: "范围外问题"
};

const NODE_NAMES: Record<string, string> = {
  validate_input: "输入校验",
  detect_language: "语言识别",
  classify_intent: "意图分类",
  rewrite_query: "问题改写",
  build_filters: "检索过滤",
  retrieve_documents: "混合检索",
  rerank_documents: "结果重排",
  evaluate_evidence: "证据评估",
  generate_answer: "答案生成",
  verify_citations: "引用校验",
  risk_check: "风险检查",
  fallback_response: "安全拒答",
  finalize_response: "结果封装"
};

const SAMPLE_QUESTIONS = [
  "Shopify 跨境订单为什么需要填写 HS 编码？",
  "客户申请退钱时应该怎么处理？",
  "当地货币付款需要使用什么支付网关？",
  "怎么设置退货和换货规则？"
];

function formatDate(value: string | null | undefined): string {
  if (!value) return "尚未同步";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function App() {
  const [session, setSession] = useState<{ token: string; user: User } | null>(
    () => loadSession()
  );

  useEffect(() => {
    const handleUnauthorized = () => setSession(null);
    window.addEventListener("tracecommerce:unauthorized", handleUnauthorized);
    return () =>
      window.removeEventListener(
        "tracecommerce:unauthorized",
        handleUnauthorized
      );
  }, []);

  if (!session) {
    return (
      <LoginPage
        onSuccess={(result) => {
          saveSession(result);
          setSession({ token: result.access_token, user: result.user });
        }}
      />
    );
  }

  return (
    <Console
      user={session.user}
      onLogout={() => {
        clearSession();
        setSession(null);
      }}
    />
  );
}

function LoginPage({
  onSuccess
}: {
  onSuccess: (result: Awaited<ReturnType<typeof login>>) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ready, setReady] = useState<ReadyStatus | null>(null);

  useEffect(() => {
    getReadyStatus()
      .then(setReady)
      .catch(() => setReady(null));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      onSuccess(await login(email.trim(), password));
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story">
        <div className="brand brand--light">
          <div className="brand-mark">
            <Fingerprint size={24} />
          </div>
          <div>
            <strong>TraceCommerce</strong>
            <span>Evidence-first AI</span>
          </div>
        </div>
        <div className="story-copy">
          <span className="eyebrow eyebrow--light">可追溯 RAG Agent</span>
          <h1>
            让每一次回答，
            <br />
            都能回到证据。
          </h1>
          <p>
            面向跨境电商客服与运营的中文知识助手，将检索、证据评估、回答生成与引用校验串成一条可审计链路。
          </p>
        </div>
        <div className="story-metrics">
          <div>
            <span>知识语言</span>
            <strong>简体中文</strong>
          </div>
          <div>
            <span>检索模式</span>
            <strong>Dense + Sparse</strong>
          </div>
          <div>
            <span>Agent编排</span>
            <strong>LangGraph</strong>
          </div>
        </div>
        <div className="story-grid" aria-hidden="true" />
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <span className="login-icon">
              <ShieldCheck size={22} />
            </span>
            <div>
              <p className="eyebrow">工作台登录</p>
              <h2>欢迎回来</h2>
            </div>
          </div>
          <p className="login-description">
            使用系统账号进入知识检索与可追溯问答控制台。
          </p>

          <label className="field">
            <span>邮箱</span>
            <div className="input-wrap">
              <UserRound size={18} />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="field">
            <span>密码</span>
            <div className="input-wrap">
              <Fingerprint size={18} />
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="请输入本地管理员密码"
                autoComplete="current-password"
                required
              />
            </div>
          </label>

          {error && (
            <div className="form-error" role="alert">
              <CircleAlert size={17} />
              <span>{error}</span>
            </div>
          )}

          <button className="primary-button login-button" disabled={loading}>
            {loading ? (
              <>
                <LoaderCircle className="spin" size={18} />
                正在验证
              </>
            ) : (
              <>
                进入控制台
                <ArrowUp className="button-arrow" size={18} />
              </>
            )}
          </button>

          <div className="service-state">
            <span
              className={`status-dot ${ready?.status === "ready" ? "online" : ""}`}
            />
            {ready?.status === "ready"
              ? "PostgreSQL 与 Milvus 服务正常"
              : "请先启动后端与数据库服务"}
          </div>
        </form>
      </section>
    </main>
  );
}

function Console({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [view, setView] = useState<View>("chat");
  const [mobileNav, setMobileNav] = useState(false);
  const [latestAnswer, setLatestAnswer] = useState<ChatAnswer | null>(null);
  const [ready, setReady] = useState<ReadyStatus | null>(null);

  useEffect(() => {
    getReadyStatus().then(setReady).catch(() => setReady(null));
  }, []);

  const nav = [
    { id: "chat" as const, label: "智能问答", icon: MessageSquareText },
    { id: "knowledge" as const, label: "知识资产", icon: BookOpen },
    { id: "trace" as const, label: "执行追踪", icon: Activity }
  ];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNav ? "sidebar--open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Fingerprint size={23} />
          </div>
          <div>
            <strong>TraceCommerce</strong>
            <span>RAG Agent Console</span>
          </div>
        </div>

        <nav className="main-nav" aria-label="主导航">
          <p className="nav-caption">工作台</p>
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={view === item.id ? "active" : ""}
                key={item.id}
                onClick={() => {
                  setView(item.id);
                  setMobileNav(false);
                }}
              >
                <Icon size={19} />
                <span>{item.label}</span>
                {item.id === "trace" && latestAnswer && (
                  <span className="nav-pulse" />
                )}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-spacer" />
        <div className="infra-card">
          <div className="infra-head">
            <Database size={17} />
            <span>基础设施</span>
          </div>
          <div className="infra-row">
            <span>PostgreSQL</span>
            <b className={ready?.database === "ok" ? "ok" : ""}>
              {ready?.database || "未知"}
            </b>
          </div>
          <div className="infra-row">
            <span>Milvus</span>
            <b className={ready?.vector_store === "ok" ? "ok" : ""}>
              {ready?.vector_store || "未知"}
            </b>
          </div>
        </div>
        <button className="user-card" onClick={onLogout}>
          <span className="avatar">{user.display_name.slice(0, 1)}</span>
          <span>
            <strong>{user.display_name}</strong>
            <small>{user.roles.join(" · ")}</small>
          </span>
          <LogOut size={17} />
        </button>
      </aside>

      {mobileNav && (
        <button
          className="sidebar-scrim"
          aria-label="关闭导航"
          onClick={() => setMobileNav(false)}
        />
      )}

      <main className="main-stage">
        <header className="topbar">
          <button
            className="icon-button menu-button"
            onClick={() => setMobileNav(true)}
            aria-label="打开导航"
          >
            <Menu size={21} />
          </button>
          <div>
            <p>{nav.find((item) => item.id === view)?.label}</p>
            <span>中文跨境电商知识工作台</span>
          </div>
          <div className="topbar-state">
            <span
              className={`status-dot ${ready?.status === "ready" ? "online" : ""}`}
            />
            {ready?.status === "ready" ? "服务在线" : "服务离线"}
          </div>
        </header>

        {view === "chat" && (
          <ChatWorkspace
            onAnswer={(answer) => {
              setLatestAnswer(answer);
            }}
            onOpenTrace={(answer) => {
              setLatestAnswer(answer);
              setView("trace");
            }}
          />
        )}
        {view === "knowledge" && <KnowledgeWorkspace user={user} />}
        {view === "trace" && (
          <TraceWorkspace
            latestAnswer={latestAnswer}
            onClearLatest={() => setLatestAnswer(null)}
          />
        )}
      </main>
    </div>
  );
}

function ChatWorkspace({
  onAnswer,
  onOpenTrace
}: {
  onAnswer: (answer: ChatAnswer) => void;
  onOpenTrace: (answer: ChatAnswer) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [query, setQuery] = useState("");
  const [threadId, setThreadId] = useState<string>();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listConversations().then(setConversations).catch(() => undefined);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const sendQuery = useCallback(
    async (value: string) => {
      const normalized = value.trim();
      if (!normalized || sending) return;
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: normalized
      };
      setMessages((current) => [...current, userMessage]);
      setQuery("");
      setSending(true);
      setError("");
      try {
        const answer = await queryAgent(normalized, threadId);
        setThreadId(answer.thread_id);
        setMessages((current) => [
          ...current,
          {
            id: answer.request_id,
            role: "assistant",
            content: answer.answer,
            result: answer
          }
        ]);
        onAnswer(answer);
        listConversations().then(setConversations).catch(() => undefined);
      } catch (requestError) {
        setError(getErrorMessage(requestError));
      } finally {
        setSending(false);
      }
    },
    [onAnswer, sending, threadId]
  );

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendQuery(query);
    }
  }

  function newConversation() {
    setMessages([]);
    setThreadId(undefined);
    setError("");
  }

  const isEmpty = messages.length === 0;

  return (
    <div className="chat-layout">
      <section className="chat-main">
        <div className="chat-toolbar">
          <div className="context-badge">
            <span className="agent-orb">
              <Bot size={18} />
            </span>
            <span>
              <strong>跨境业务助手</strong>
              <small>中文知识库 · 引用强校验</small>
            </span>
          </div>
          <div className="toolbar-actions">
            <button
              className="ghost-button mobile-history"
              onClick={() => setHistoryOpen(!historyOpen)}
            >
              <History size={17} />
              历史
            </button>
            <button className="ghost-button" onClick={newConversation}>
              <Sparkles size={17} />
              新对话
            </button>
          </div>
        </div>

        <div className="message-stream">
          {isEmpty ? (
            <div className="chat-empty">
              <div className="empty-symbol">
                <span />
                <Bot size={34} />
              </div>
              <p className="eyebrow">EVIDENCE-FIRST ASSISTANT</p>
              <h1>今天想查询什么业务问题？</h1>
              <p className="empty-copy">
                我会先检索中文知识库、评估证据，再给出带原文引用的回答。
              </p>
              <div className="question-grid">
                {SAMPLE_QUESTIONS.map((item, index) => (
                  <button key={item} onClick={() => void sendQuery(item)}>
                    <span>0{index + 1}</span>
                    <p>{item}</p>
                    <ArrowUp size={17} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message) =>
                message.role === "user" ? (
                  <div className="message message--user" key={message.id}>
                    <div className="message-avatar">
                      <UserRound size={17} />
                    </div>
                    <div>
                      <span>你的问题</span>
                      <p>{message.content}</p>
                    </div>
                  </div>
                ) : (
                  <AnswerCard
                    key={message.id}
                    result={message.result}
                    onOpenTrace={() => onOpenTrace(message.result)}
                  />
                )
              )}
              {sending && (
                <div className="agent-thinking">
                  <span className="agent-orb">
                    <Bot size={18} />
                  </span>
                  <div>
                    <strong>正在构建证据链</strong>
                    <span className="thinking-line">
                      <i />
                      <i />
                      <i />
                    </span>
                  </div>
                </div>
              )}
              {error && (
                <div className="inline-error">
                  <CircleAlert size={18} />
                  <span>{error}</span>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <textarea
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入中文业务问题，Enter 发送，Shift + Enter 换行"
              rows={1}
              maxLength={2000}
            />
            <button
              className="send-button"
              aria-label="发送问题"
              disabled={!query.trim() || sending}
              onClick={() => void sendQuery(query)}
            >
              {sending ? (
                <LoaderCircle className="spin" size={19} />
              ) : (
                <Send size={19} />
              )}
            </button>
          </div>
          <p>回答仅依据当前知识库，不构成法律、税务或海关专业意见。</p>
        </div>
      </section>

      <aside className={`history-panel ${historyOpen ? "history-panel--open" : ""}`}>
        <div className="history-heading">
          <div>
            <p className="eyebrow">CONVERSATIONS</p>
            <h3>最近会话</h3>
          </div>
          <button
            className="icon-button history-close"
            onClick={() => setHistoryOpen(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="history-list">
          {conversations.length === 0 ? (
            <div className="history-empty">
              <History size={22} />
              <span>完成第一次问答后，会话会显示在这里。</span>
            </div>
          ) : (
            conversations.slice(0, 8).map((item) => (
              <button
                key={item.thread_id}
                className={threadId === item.thread_id ? "current" : ""}
                onClick={() => {
                  setThreadId(item.thread_id);
                  setMessages([]);
                  setHistoryOpen(false);
                }}
              >
                <MessageSquareText size={16} />
                <span>
                  <strong>{item.title || "未命名会话"}</strong>
                  <small>{formatDate(item.updated_at)}</small>
                </span>
              </button>
            ))
          )}
        </div>
        <div className="history-note">
          <ShieldCheck size={17} />
          <span>每次问答均记录 request_id 与完整 Agent 轨迹。</span>
        </div>
      </aside>
    </div>
  );
}

function AnswerCard({
  result,
  onOpenTrace
}: {
  result: ChatAnswer;
  onOpenTrace: () => void;
}) {
  const [sourcesOpen, setSourcesOpen] = useState(true);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const evidenceScore = result.evidence_score ?? result.confidence ?? 0;
  const evidencePercent = Math.round(evidenceScore * 100);
  const evidenceLevelNames = {
    insufficient: "不足",
    low: "低",
    medium: "中",
    high: "高"
  };
  const evidenceLevel =
    evidenceLevelNames[result.evidence_level ?? (result.grounded ? "low" : "insufficient")];

  async function rate(value: "up" | "down") {
    setFeedback(value);
    try {
      await submitFeedback(result.request_id, value === "up");
    } catch {
      setFeedback(null);
    }
  }

  return (
    <article className="answer-card">
      <div className="answer-head">
        <span className="agent-orb">
          <Bot size={18} />
        </span>
        <div>
          <strong>TraceCommerce Agent</strong>
          <span>基于中文知识库生成</span>
        </div>
        <span className={`grounded-badge ${result.grounded ? "verified" : ""}`}>
          {result.grounded ? <ShieldCheck size={15} /> : <CircleAlert size={15} />}
          {result.grounded ? "引用来源已校验" : "证据不足"}
        </span>
      </div>

      <div className="answer-body">{result.answer}</div>

      <div className="answer-metadata">
        <Metric
          icon={<Gauge size={16} />}
          label="证据匹配分"
          value={`${evidencePercent}% · ${evidenceLevel}`}
        />
        <Metric
          icon={<Fingerprint size={16} />}
          label="意图"
          value={INTENT_NAMES[result.intent] || result.intent}
        />
        <Metric
          icon={<BookOpen size={16} />}
          label="引用"
          value={`${result.citations.length} 条`}
        />
        <Metric
          icon={<Clock3 size={16} />}
          label="轨迹"
          value={`${result.trace.length} 步`}
        />
      </div>

      {result.citations.length > 0 && (
        <div className="citation-section">
          <button
            className="citation-toggle"
            onClick={() => setSourcesOpen(!sourcesOpen)}
          >
            <span>
              <BookOpen size={17} />
              证据来源
            </span>
            <span>
              {result.citations.length} 条
              <ChevronDown
                className={sourcesOpen ? "rotate" : ""}
                size={17}
              />
            </span>
          </button>
          {sourcesOpen && (
            <div className="citations">
              {result.citations.map((citation, index) => (
                <div className="citation" key={citation.chunk_id}>
                  <div className="citation-index">{index + 1}</div>
                  <div className="citation-content">
                    <div>
                      <strong>{citation.title}</strong>
                      {citation.section_title && (
                        <span>{citation.section_title}</span>
                      )}
                    </div>
                    <blockquote>{citation.quoted_text}</blockquote>
                    <div className="citation-footer">
                      <span>
                        检索 {citation.retrieval_score.toFixed(3)}
                        {citation.rerank_score !== null &&
                          ` · 重排 ${citation.rerank_score.toFixed(3)}`}
                      </span>
                      <a
                        href={citation.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        查看原文
                        <ExternalLink size={14} />
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="warning-box">
          <CircleAlert size={17} />
          <span>{result.warnings.join("；")}</span>
        </div>
      )}

      <div className="answer-actions">
        <span>这个回答有帮助吗？</span>
        <button
          className={feedback === "up" ? "selected" : ""}
          onClick={() => void rate("up")}
        >
          <ThumbsUp size={15} />
        </button>
        <button
          className={feedback === "down" ? "selected" : ""}
          onClick={() => void rate("down")}
        >
          <ThumbsDown size={15} />
        </button>
        <button className="trace-link" onClick={onOpenTrace}>
          查看执行轨迹
          <ArrowUp size={15} />
        </button>
      </div>
    </article>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="metric">
      {icon}
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
      </span>
    </div>
  );
}

function KnowledgeWorkspace({ user }: { user: User }) {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [selectedSource, setSelectedSource] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState("cross_border_commerce");
  const isAdmin = user.roles.includes("admin");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSources, nextDocuments] = await Promise.all([
        listKnowledgeSources(),
        listDocuments(selectedSource || undefined)
      ]);
      setSources(nextSources);
      setDocuments(nextDocuments.items);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, [selectedSource]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleSync(source: KnowledgeSource) {
    setBusyId(source.id);
    setNotice("");
    setError("");
    try {
      const job = await syncKnowledgeSource(source.id);
      setNotice(`同步完成，写入 ${job.chunks_written} 个知识片段。`);
      await loadData();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId("");
    }
  }

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!file || !selectedSource) return;
    setBusyId("upload");
    setError("");
    try {
      const job = await uploadDocument({
        sourceId: selectedSource,
        file,
        businessCategory: category
      });
      setNotice(`文档导入成功，写入 ${job.chunks_written} 个知识片段。`);
      setUploadOpen(false);
      setFile(null);
      await loadData();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId("");
    }
  }

  async function handleDelete(document: KnowledgeDocument) {
    if (!window.confirm(`确定停用文档“${document.title}”吗？`)) return;
    setBusyId(document.id);
    setError("");
    try {
      await deleteDocument(document.id);
      setNotice("文档已停用并从向量库移除。");
      await loadData();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setBusyId("");
    }
  }

  const ChineseCount = documents.filter(
    (document) => document.language === "zh-CN"
  ).length;

  return (
    <div className="workspace-page">
      <section className="page-intro">
        <div>
          <p className="eyebrow">KNOWLEDGE OPERATIONS</p>
          <h1>知识资产</h1>
          <p>管理可检索文档、数据来源与增量同步任务。</p>
        </div>
        <div className="page-actions">
          <button className="ghost-button" onClick={() => void loadData()}>
            <RefreshCw size={17} />
            刷新
          </button>
          {isAdmin && (
            <button
              className="primary-button"
              disabled={!selectedSource}
              onClick={() => setUploadOpen(true)}
            >
              <Upload size={17} />
              上传中文文档
            </button>
          )}
        </div>
      </section>

      <div className="stat-grid">
        <StatCard
          icon={<Database size={20} />}
          label="知识来源"
          value={sources.length.toString()}
          note="结构化管理"
        />
        <StatCard
          icon={<FileText size={20} />}
          label="有效文档"
          value={documents.length.toString()}
          note="当前筛选范围"
        />
        <StatCard
          icon={<BookOpen size={20} />}
          label="中文文档"
          value={ChineseCount.toString()}
          note="language = zh-CN"
        />
        <StatCard
          icon={<ShieldCheck size={20} />}
          label="数据状态"
          value="可追溯"
          note="URL + 版本 + Hash"
        />
      </div>

      {(error || notice) && (
        <div className={error ? "page-alert error" : "page-alert success"}>
          {error ? <CircleAlert size={18} /> : <CircleCheck size={18} />}
          <span>{error || notice}</span>
          <button onClick={() => (error ? setError("") : setNotice(""))}>
            <X size={16} />
          </button>
        </div>
      )}

      <section className="source-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">SOURCES</p>
            <h2>知识来源</h2>
          </div>
          <span>{sources.length} 个来源</span>
        </div>
        <div className="source-grid">
          {sources.map((source) => (
            <button
              key={source.id}
              className={`source-card ${
                selectedSource === source.id ? "selected" : ""
              }`}
              onClick={() =>
                setSelectedSource(
                  selectedSource === source.id ? "" : source.id
                )
              }
            >
              <span className="source-icon">
                <Database size={20} />
              </span>
              <span className="source-copy">
                <strong>{source.name}</strong>
                <small>{source.company_name} · {source.source_type}</small>
                <span>
                  <i className={source.is_active ? "active" : ""} />
                  {source.is_active ? "已启用" : "已停用"} ·{" "}
                  {formatDate(source.last_synced_at)}
                </span>
              </span>
              {isAdmin && source.source_type === "website" && (
                <span
                  role="button"
                  tabIndex={0}
                  className="source-sync"
                  onClick={(event) => {
                    event.stopPropagation();
                    void handleSync(source);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.stopPropagation();
                      void handleSync(source);
                    }
                  }}
                >
                  {busyId === source.id ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <RefreshCw size={16} />
                  )}
                </span>
              )}
            </button>
          ))}
        </div>
      </section>

      <section className="document-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">DOCUMENTS</p>
            <h2>知识文档</h2>
          </div>
          <label className="source-filter">
            <Search size={16} />
            <select
              value={selectedSource}
              onChange={(event) => setSelectedSource(event.target.value)}
            >
              <option value="">全部知识来源</option>
              {sources.map((source) => (
                <option value={source.id} key={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="table-wrap">
          {loading ? (
            <div className="loading-state">
              <LoaderCircle className="spin" size={24} />
              正在读取知识资产
            </div>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <FileText size={28} />
              <strong>当前范围内没有文档</strong>
              <span>选择知识来源并上传中文文档。</span>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>文档</th>
                  <th>语言</th>
                  <th>业务分类</th>
                  <th>版本</th>
                  <th>采集时间</th>
                  {isAdmin && <th />}
                </tr>
              </thead>
              <tbody>
                {documents.map((document) => (
                  <tr key={document.id}>
                    <td>
                      <div className="document-name">
                        <span>
                          <FileText size={17} />
                        </span>
                        <div>
                          <strong>{document.title}</strong>
                          <small>{document.source_type}</small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="language-pill">{document.language}</span>
                    </td>
                    <td>{document.business_category || "未分类"}</td>
                    <td>v{document.current_version}</td>
                    <td>{formatDate(document.crawled_at)}</td>
                    {isAdmin && (
                      <td>
                        <button
                          className="table-action danger"
                          disabled={busyId === document.id}
                          onClick={() => void handleDelete(document)}
                        >
                          {busyId === document.id ? (
                            <LoaderCircle className="spin" size={15} />
                          ) : (
                            "停用"
                          )}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {uploadOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="modal" onSubmit={handleUpload}>
            <div className="modal-heading">
              <div>
                <p className="eyebrow">DOCUMENT INGESTION</p>
                <h2>上传中文知识文档</h2>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => setUploadOpen(false)}
              >
                <X size={19} />
              </button>
            </div>
            <p className="modal-copy">
              支持 PDF、TXT、Markdown、HTML 与 DOCX，默认以 `zh-CN`
              写入知识库。
            </p>
            <label className="field">
              <span>知识来源</span>
              <select
                value={selectedSource}
                onChange={(event) => setSelectedSource(event.target.value)}
                required
              >
                <option value="">请选择来源</option>
                {sources.map((source) => (
                  <option value={source.id} key={source.id}>
                    {source.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="upload-drop">
              <Upload size={24} />
              <strong>{file ? file.name : "点击选择文件"}</strong>
              <span>{file ? `${(file.size / 1024).toFixed(1)} KB` : "最大 10MB"}</span>
              <input
                type="file"
                accept=".pdf,.txt,.md,.markdown,.html,.htm,.docx"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                required
              />
            </label>
            <label className="field">
              <span>业务分类</span>
              <input
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                placeholder="cross_border_commerce"
              />
            </label>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() => setUploadOpen(false)}
              >
                取消
              </button>
              <button
                className="primary-button"
                disabled={!file || !selectedSource || busyId === "upload"}
              >
                {busyId === "upload" ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Upload size={17} />
                )}
                导入并向量化
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  note
}: {
  icon: ReactNode;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="stat-card">
      <span>{icon}</span>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
        <p>{note}</p>
      </div>
    </div>
  );
}

function TraceWorkspace({
  latestAnswer,
  onClearLatest
}: {
  latestAnswer: ChatAnswer | null;
  onClearLatest: () => void;
}) {
  const [requestId, setRequestId] = useState(latestAnswer?.request_id || "");
  const [trace, setTrace] = useState<RequestTrace | null>(
    latestAnswer
      ? { result: latestAnswer, retrieved: [] }
      : null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (latestAnswer) {
      setRequestId(latestAnswer.request_id);
      setTrace({ result: latestAnswer, retrieved: [] });
    }
  }, [latestAnswer]);

  async function searchTrace(event: FormEvent) {
    event.preventDefault();
    if (!requestId.trim()) return;
    setLoading(true);
    setError("");
    try {
      setTrace(await getTrace(requestId.trim()));
      onClearLatest();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setTrace(null);
    } finally {
      setLoading(false);
    }
  }

  const totalDuration = useMemo(
    () =>
      trace?.result.trace.reduce((total, step) => total + step.duration_ms, 0) ||
      0,
    [trace]
  );

  return (
    <div className="workspace-page trace-page">
      <section className="page-intro">
        <div>
          <p className="eyebrow">AGENT OBSERVABILITY</p>
          <h1>执行追踪</h1>
          <p>通过 request_id 还原检索、重排、证据评估与回答生成过程。</p>
        </div>
      </section>

      <form className="trace-search" onSubmit={searchTrace}>
        <Search size={18} />
        <input
          value={requestId}
          onChange={(event) => setRequestId(event.target.value)}
          placeholder="输入问答返回的 request_id"
        />
        <button className="primary-button" disabled={loading || !requestId.trim()}>
          {loading ? <LoaderCircle className="spin" size={17} /> : "查询轨迹"}
        </button>
      </form>

      {error && (
        <div className="page-alert error">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      {!trace ? (
        <div className="trace-placeholder">
          <div className="trace-illustration">
            <span><Check size={14} /></span>
            <i />
            <span><Search size={14} /></span>
            <i />
            <span><Sparkles size={14} /></span>
          </div>
          <h2>等待一条问答请求</h2>
          <p>完成智能问答后可直接打开轨迹，也可以粘贴历史 request_id。</p>
        </div>
      ) : (
        <>
          <div className="trace-summary">
            <div>
              <span className="trace-state">
                {trace.result.grounded ? (
                  <ShieldCheck size={20} />
                ) : (
                  <CircleAlert size={20} />
                )}
              </span>
              <span>
                <small>最终状态</small>
                <strong>
                  {trace.result.grounded ? "引用来源已校验" : "安全拒答"}
                </strong>
              </span>
            </div>
            <div>
              <Gauge size={19} />
              <span>
                <small>证据匹配分</small>
                <strong>
                  {Math.round(
                    (trace.result.evidence_score ?? trace.result.confidence ?? 0) * 100
                  )}%
                </strong>
              </span>
            </div>
            <div>
              <Clock3 size={19} />
              <span>
                <small>节点耗时</small>
                <strong>{totalDuration.toFixed(0)} ms</strong>
              </span>
            </div>
            <div>
              <LayoutDashboard size={19} />
              <span>
                <small>执行节点</small>
                <strong>{trace.result.trace.length}</strong>
              </span>
            </div>
          </div>

          <div className="trace-content">
            <section className="timeline-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">LANGGRAPH</p>
                  <h2>节点时间线</h2>
                </div>
                <span>{trace.result.trace.length} steps</span>
              </div>
              <div className="timeline">
                {trace.result.trace.map((step, index) => (
                  <TraceRow
                    step={step}
                    index={index}
                    last={index === trace.result.trace.length - 1}
                    key={`${step.node}-${index}`}
                  />
                ))}
              </div>
            </section>

            <aside className="evidence-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">EVIDENCE</p>
                  <h2>最终证据</h2>
                </div>
              </div>
              <p className="trace-answer">{trace.result.answer}</p>
              <div className="trace-citations">
                {trace.result.citations.length === 0 ? (
                  <div className="empty-state compact">
                    <CircleAlert size={22} />
                    <span>本次请求未形成有效引用</span>
                  </div>
                ) : (
                  trace.result.citations.map((citation, index) => (
                    <a
                      key={citation.chunk_id}
                      href={citation.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span>{index + 1}</span>
                      <div>
                        <strong>{citation.title}</strong>
                        <small>{citation.quoted_text.slice(0, 76)}…</small>
                      </div>
                      <ExternalLink size={15} />
                    </a>
                  ))
                )}
              </div>
              <div className="request-id">
                <span>REQUEST ID</span>
                <code>{trace.result.request_id}</code>
              </div>
            </aside>
          </div>
        </>
      )}
    </div>
  );
}

function TraceRow({
  step,
  index,
  last
}: {
  step: TraceStep;
  index: number;
  last: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Fragment>
      <button className="timeline-row" onClick={() => setOpen(!open)}>
        <span className="timeline-marker">
          <Check size={13} />
          {!last && <i />}
        </span>
        <span className="timeline-copy">
          <small>STEP {String(index + 1).padStart(2, "0")}</small>
          <strong>{NODE_NAMES[step.node] || step.node}</strong>
          <em>{step.node}</em>
        </span>
        <span className={`step-status ${step.status}`}>
          {step.status === "success" ? "成功" : step.status}
        </span>
        <span className="step-time">{step.duration_ms.toFixed(1)} ms</span>
        <ChevronDown className={open ? "rotate" : ""} size={17} />
      </button>
      {open && (
        <div className="timeline-details">
          {step.input_summary && (
            <div>
              <span>INPUT</span>
              <code>{step.input_summary}</code>
            </div>
          )}
          {step.output_summary && (
            <div>
              <span>OUTPUT</span>
              <code>{step.output_summary}</code>
            </div>
          )}
          {step.error && (
            <div>
              <span>ERROR</span>
              <code>{step.error}</code>
            </div>
          )}
        </div>
      )}
    </Fragment>
  );
}

export default App;
