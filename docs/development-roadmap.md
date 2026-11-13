# Development Roadmap

This roadmap tracks the phased development of the **Personal AI Core** platform according to `MASTER_PLAN.md`.

| Phase | Title | Status | Key Deliverables |
|---|---|---|---|
| **Phase 0** | **Project Foundation** | **Completed** | Monorepo layout, Next.js, FastAPI, Docker Compose, Alembic, tests |
| **Phase 1** | **Authentication & Conversations** | **Completed** | Argon2id auth, rotating JWTs, workspaces, conversation persistence |
| **Phase 2** | **LLM Integration & Streaming** | **Next** | LLM provider abstraction, OpenAI SDK, SSE streaming, token tracking |
| **Phase 3** | **Tool Calling System** | Planned | Tool registry, schemas, execution sandbox, audit logs, timeout limits |
| **Phase 4** | **Knowledge Engine & RAG** | Planned | Document ingestion (PDF/TXT/MD), chunking, embeddings, pgvector |
| **Phase 5** | **Database Integrations** | Planned | Read-only connectors, schema inspection, parameterized query tools |
| **Phase 6** | **Developer Assistant** | Planned | GitHub integration, repo indexing, code search, architectural Q&A |
| **Phase 7** | **Advanced Agent Capabilities** | Planned | Multi-step agent execution, LangGraph integration, human approval |
| **Phase 8** | **Production Deployment** | Planned | Vercel deployment, Oracle Cloud VPS, HTTPS, Caddy, monitoring |
