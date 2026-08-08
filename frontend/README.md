# TraceCommerce 前端控制台

这是 TraceCommerce RAG Agent 的本地 Web 控制台，使用 React、TypeScript、
Vite、Axios 和 Lucide Icons 实现。

## 页面功能

- JWT 登录与服务就绪状态检查
- 中文知识库问答与连续会话
- 回答置信度、意图、风险提示和证据引用
- 有用/无用反馈
- 对话记录
- 知识源同步、文档筛选、上传与删除
- 按 `request_id` 查看 LangGraph 节点轨迹和耗时

## 本地运行

先启动 FastAPI 后端并确认 <http://localhost:8000/ready> 返回成功，然后运行：

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 <http://localhost:3000>。

管理员账户由项目根目录 `.env` 中的 `ADMIN_EMAIL` 和 `ADMIN_PASSWORD` 设置。
首次启动前必须修改示例值，不要将真实凭据提交到版本控制。

```text
邮箱：YOUR_ADMIN_EMAIL
密码：YOUR_ADMIN_PASSWORD
```

本地开发默认使用 `/api/v1`，Vite 会把 API 请求代理至
`http://127.0.0.1:8000`。如果前后端分开部署，可复制 `.env.example` 为
`.env.local` 并调整 `VITE_API_BASE_URL`。

## 构建检查

```powershell
npm run check
npm run build
```

生产构建产物生成在 `frontend/dist`。
