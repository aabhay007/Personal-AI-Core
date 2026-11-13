# Personal AI Core — Master Engineering Plan

**Project type:** Reusable AI platform  
**Initial release:** V1  
**Development environment:** Google Antigravity  
**Deployment:** Vercel + Oracle Cloud VPS + Neon PostgreSQL  
**Primary language:** Python  
**Architecture:** Modular monolith with extensible integrations

---

# 1. Project Vision

Build a reusable AI platform that can understand user requests, retrieve information, interact with external applications, execute controlled operations, and coordinate multi-step tasks.

This is not intended to be another basic chatbot.

The platform should eventually support:

- Multiple LLM providers.
- Multiple users and isolated workspaces.
- Persistent conversations and context.
- Document ingestion and semantic search.
- External API integrations.
- Database integrations.
- Tool/function calling.
- Multi-step agent execution.
- Long-running tasks.
- Human approval for sensitive operations.
- Extensible plugin/tool architecture.

The first application built on top of this platform will be a general-purpose developer assistant.

The underlying AI core must remain independent of that application.

## Core architectural principle

The AI core should not be tightly coupled to any particular frontend, database, LLM provider, or external application.

All integrations should communicate through standardized interfaces.

# 2. Technology Stack

Use the following technologies unless a documented technical limitation requires a change.

| Component | Technology |
|---|---|
| Frontend | Next.js + React |
| Frontend language | TypeScript |
| Styling | Tailwind CSS |
| UI components | shadcn/ui |
| Backend | Python + FastAPI |
| Python version | Python 3.12+ |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Database migrations | Alembic |
| Primary database | PostgreSQL |
| Database hosting | Neon |
| Vector search | pgvector |
| Initial LLM | OpenAI API |
| LLM integration | Official OpenAI Python SDK |
| AI orchestration | Custom lightweight orchestrator initially |
| Advanced orchestration | LangGraph in a later phase |
| Cache | Redis, later |
| Deployment | Docker + Docker Compose |
| Frontend hosting | Vercel |
| Backend hosting | Oracle Cloud VPS |
| Reverse proxy | Caddy or Nginx |
| Source control | GitHub |

### Important technology decisions

**Do not introduce unnecessary infrastructure.**

For V1:

- Do not use Kubernetes.
- Do not introduce microservices.
- Do not introduce Kafka or RabbitMQ.
- Do not introduce Redis before there is a demonstrated need.
- Do not introduce LangChain and LangGraph simultaneously.
- Do not build a custom vector database.
- Do not build custom authentication cryptography.

Start with a modular monolith. Introduce additional infrastructure only when justified.

# 3. High-Level Architecture

The application should follow this architecture:

```text
                  USER
                    |
                    v
           NEXT.JS FRONTEND
                    |
                    v
             FASTAPI BACKEND
                    |
          AUTHENTICATION LAYER
                    |
                    v
             AI ORCHESTRATOR
                    |
          +---------+----------+
          |         |          |
          v         v          v
       LLM       KNOWLEDGE    TOOL
      PROVIDER    ENGINE     REGISTRY
          |         |          |
          v         v          v
       OpenAI    PostgreSQL   External
                 + pgvector   Integrations
          |
          v
      AI RESPONSE
          |
          v
       FRONTEND
```

PostgreSQL will store application data, conversation history, knowledge metadata, and vector embeddings.

External documents should eventually be stored in object storage rather than directly in PostgreSQL.

# 4. Repository Structure

Use a monorepo.

```text
personal-ai-core/
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   ├── layout/
│   │   │   ├── settings/
│   │   │   └── ui/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── services/
│   │   ├── types/
│   │   └── styles/
│   │
│   ├── public/
│   ├── package.json
│   └── next.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── conversations.py
│   │   │       ├── messages.py
│   │   │       ├── documents.py
│   │   │       ├── tools.py
│   │   │       └── integrations.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   │
│   │   ├── ai/
│   │   │   ├── providers/
│   │   │   ├── orchestrator/
│   │   │   ├── prompts/
│   │   │   ├── context/
│   │   │   └── streaming/
│   │   │
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   └── developer_assistant.py
│   │   │
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── schemas.py
│   │   │   ├── calculator.py
│   │   │   └── datetime_tool.py
│   │   │
│   │   ├── knowledge/
│   │   │   ├── ingestion.py
│   │   │   ├── chunking.py
│   │   │   ├── embeddings.py
│   │   │   ├── retrieval.py
│   │   │   └── citations.py
│   │   │
│   │   ├── integrations/
│   │   │   ├── base.py
│   │   │   ├── database/
│   │   │   ├── github/
│   │   │   └── rest_api/
│   │   │
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
│
├── infrastructure/
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── deployment/
│
├── docs/
│   ├── architecture.md
│   ├── database-schema.md
│   ├── api-reference.md
│   ├── security.md
│   └── development-roadmap.md
│
├── .gitignore
├── README.md
└── MASTER_PLAN.md
```

The structure is a starting point. Antigravity should not create empty files for every future feature. Create modules as they become necessary.

# 5. Database Design

Use Neon PostgreSQL as the primary application database.

Enable the pgvector extension for semantic search.

Use SQLAlchemy 2.x and Alembic for database management.

## Initial tables

### users

Stores user accounts.

- id — UUID primary key
- email — Unique email
- password_hash — Secure password hash
- full_name
- is_active
- created_at
- updated_at

### workspaces

Provides an isolation boundary for users and their resources.

- id — UUID
- name
- owner_id — FK to users
- created_at

### workspace_members

- id
- workspace_id
- user_id
- role
- created_at

Roles initially: owner, admin, member.

### conversations

- id — UUID
- workspace_id
- user_id
- title
- model_provider
- model_name
- created_at
- updated_at

### messages

- id — UUID
- conversation_id
- role
- content
- token_usage
- created_at

Supported roles:

- system
- user
- assistant
- tool

### documents

- id — UUID
- workspace_id
- uploaded_by
- filename
- mime_type
- storage_key
- file_size
- processing_status
- created_at

### document_chunks

- id — UUID
- document_id
- workspace_id
- chunk_index
- content
- embedding
- metadata
- created_at

Use pgvector for embeddings. Select an embedding model and dimension explicitly and keep it consistent.

### tools

- id — UUID
- workspace_id — Nullable for platform-level tools
- name
- description
- input_schema
- execution_type
- is_enabled
- requires_approval
- created_at

### tool_executions

- id — UUID
- workspace_id
- conversation_id
- tool_name
- input_arguments
- execution_status
- result_summary
- error_message
- execution_time_ms
- created_at

### integrations

- id — UUID
- workspace_id
- integration_type
- display_name
- configuration
- encrypted_credentials
- is_enabled
- created_at

### audit_logs

- id — UUID
- workspace_id
- user_id
- action
- resource_type
- resource_id
- metadata
- created_at

Never store raw passwords, plaintext API keys, or sensitive authentication tokens in logs.

All workspace-owned data must be protected by workspace authorization.

Use database constraints and indexes for integrity and performance.

# 6. Backend Architecture

FastAPI should expose versioned REST endpoints.

Initial API routes:

```text
/api/v1/auth/register
/api/v1/auth/login
/api/v1/auth/refresh
/api/v1/auth/logout

/api/v1/conversations
/api/v1/conversations/{id}

/api/v1/conversations/{id}/messages
/api/v1/chat/stream

/api/v1/documents
/api/v1/documents/{id}
/api/v1/documents/{id}/status

/api/v1/tools
/api/v1/tools/{name}/execute

/api/v1/integrations
/api/v1/integrations/{id}
```

Use Pydantic request and response schemas.

Do not expose SQLAlchemy models directly as API responses.

## Authentication

Implement secure authentication.

Requirements:

- Argon2id password hashing.
- Short-lived access tokens.
- Rotating refresh tokens.
- Refresh-token revocation.
- Secure, HttpOnly, SameSite cookies where appropriate.
- Strict CORS configuration.
- Rate limiting on authentication endpoints.
- Workspace membership verification.
- No trusting workspace IDs supplied by the browser without authorization.

Never implement custom cryptographic algorithms.

# 7. AI Core Architecture

This is the most important part of the project.

Keep the AI engine independent of HTTP endpoints and frontend logic.

## 7.1 LLM provider abstraction

Create a common provider interface.

Example:

```python
class LLMProvider:

    async def generate(
        self,
        messages,
        tools=None,
        model=None
    ):
        raise NotImplementedError

    async def stream(
        self,
        messages,
        tools=None,
        model=None
    ):
        raise NotImplementedError

    async def create_embeddings(
        self,
        texts
    ):
        raise NotImplementedError
```

Implement the first provider using the official OpenAI SDK.

Keep model names and configuration outside business logic.

The architecture should allow additional providers later.

Do not assume every provider supports identical tool-calling or streaming behavior.

## 7.2 AI orchestrator

The orchestrator is responsible for:

1. Receiving the user's request.
2. Loading relevant conversation history.
3. Loading the selected model configuration.
4. Retrieving relevant knowledge when appropriate.
5. Identifying available tools.
6. Sending the request to the LLM.
7. Processing tool calls.
8. Validating tool arguments.
9. Executing authorized tools.
10. Returning tool results to the LLM.
11. Generating the final response.
12. Persisting the conversation and execution information.

Implement explicit limits:

- Maximum tool-calling iterations.
- Maximum execution time.
- Maximum input size.
- Maximum tool output size.
- Maximum LLM token budget.

Do not allow infinite agent loops.

For V1, implement a controlled orchestration loop yourself. Evaluate LangGraph later.

## 7.3 Context management

Do not send the entire conversation history indefinitely.

Implement:

- Recent-message history.
- Token-budget management.
- Conversation summarization when needed.
- Relevant context retrieval.
- Workspace isolation.

Long-term memory should be a separate capability, not an assumption that every previous message is permanently relevant.

# 8. Tool Calling System

Build a reusable tool registry.

A tool should have:

- Unique name.
- Description.
- Input schema.
- Execution function.
- Permission requirements.
- Approval policy.
- Timeout.
- Error handling.

Example:

```python
@register_tool(
    name="calculator",
    description="Perform basic mathematical calculations"
)
async def calculator(expression: str):
    ...
```

The decorator is illustrative. Implement a validated registration mechanism with explicit schemas rather than relying on arbitrary dynamic imports.

The AI should receive tool definitions in the format supported by the selected LLM provider.

### Initial tools

1. Calculator.
2. Current date/time using server-side timezone-aware logic.
3. Document search.
4. Database metadata inspection.
5. Read-only database query through approved operations.

Start with simple tools before connecting external systems.

### Critical security rules

- Never execute arbitrary Python code generated by the LLM.
- Never evaluate arbitrary SQL generated by the LLM.
- Never trust tool arguments simply because the LLM produced them.
- Validate every argument.
- Apply workspace authorization.
- Enforce tool-specific permissions.
- Apply timeouts.
- Record tool execution.
- Require explicit approval for sensitive operations.

# 9. Knowledge Engine and RAG

Build a document-based knowledge system.

Initial supported formats:

- PDF
- TXT
- Markdown
- DOCX

Processing pipeline:

```text
Upload
  |
  v
File validation
  |
  v
Text extraction
  |
  v
Text cleaning
  |
  v
Chunking
  |
  v
Embedding generation
  |
  v
PostgreSQL + pgvector
  |
  v
Semantic retrieval
  |
  v
LLM response with citations
```

Requirements:

- Configurable chunk size and overlap.
- Preserve document metadata.
- Store page numbers when available.
- Support document processing status.
- Handle duplicate uploads.
- Handle failed embedding requests.
- Support document deletion and associated chunk deletion.
- Enforce workspace-level retrieval isolation.

Use hybrid retrieval as a future enhancement: combine keyword and semantic search.

For the first release, semantic retrieval with metadata filters is sufficient.

The assistant must distinguish retrieved information from its own generated explanations.

When using uploaded documents, it should cite document names and page references where available.

# 10. Database Integration

Build a standardized database integration interface.

Initial support:

- PostgreSQL.
- SQL Server later.

The integration should support:

- Connection configuration.
- Connection testing.
- Database metadata retrieval.
- Table and column inspection.
- Schema information.
- Approved read-only data retrieval.

Do not allow users to provide arbitrary database credentials without validation.

For V1:

- Use read-only database credentials.
- Restrict access to explicitly approved schemas and operations.
- Use parameterized SQL.
- Apply query timeouts and row limits.
- Never expose database credentials to the LLM.
- Never execute arbitrary SQL supplied by the model.

The AI should interact through predefined database tools.

Example:

User: "Show me all unpaid invoices."

The AI determines that it needs the invoice retrieval tool, supplies validated filters, and receives a controlled result.

It does not get unrestricted database access.

# 11. Frontend Requirements

Build a clean, modern AI interface.

Use Next.js App Router, TypeScript, Tailwind CSS, and shadcn/ui.

Initial pages:

```text
/login
/register
/chat
/chat/[conversationId]
/documents
/tools
/integrations
/settings
```

### Main chat interface

Include:

- Sidebar with conversation history.
- New conversation button.
- Main message area.
- Markdown rendering.
- Code block rendering.
- Copy response functionality.
- Regenerate response.
- Stop generation.
- Streaming responses.
- Tool execution indicators.
- Error handling.
- Model selection.

### Document management

Include:

- Upload documents.
- Document list.
- Processing status.
- Delete document.
- Document details.

### Tools management

Include:

- Available tools.
- Tool descriptions.
- Enable/disable controls.
- Permission requirements.
- Execution history.

### Integrations

Include:

- Connected integrations.
- Connection status.
- Configuration.
- Disconnect functionality.

### Design philosophy

Avoid building a generic clone of ChatGPT.

Create a professional developer-oriented interface.

Prioritize usability, speed, and clarity over animations and decorative elements.

# 12. File Storage

Do not use Neon PostgreSQL as a file storage system.

Store file metadata in PostgreSQL and the actual files in object storage.

During local development, use local storage through a defined storage abstraction.

For production, use an S3-compatible object storage service such as Cloudflare R2.

Requirements:

- Private buckets.
- No public document URLs.
- Short-lived signed download URLs.
- File type and size validation.
- Workspace ownership verification.
- Secure deletion.

# 13. Streaming

Implement streaming responses from the backend to the frontend.

Use Server-Sent Events (SSE) initially.

The frontend should display:

- Incoming response tokens.
- Tool execution events.
- Tool completion.
- Errors.
- Final response.

Define a consistent event protocol, for example:

```text
event: message_start

event: content_delta

event: tool_start

event: tool_result

event: message_complete

event: error
```

Do not expose internal prompts, provider credentials, or hidden reasoning.

The frontend should receive only information intended for the user.

# 14. Deployment Architecture

## Frontend — Vercel

Deploy Next.js on Vercel.

Configure:

```text
NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
```

Do not put private API keys in frontend environment variables.

## Backend — Oracle Cloud VPS

Use the existing Oracle VPS.

Initial infrastructure:

```text
Oracle Ubuntu VPS
       |
       v
     Docker
       |
       +--- FastAPI
       |
       +--- Caddy / Nginx
       |
       +--- Optional background worker
```

The VPS will communicate with:

- Neon PostgreSQL.
- OpenAI API.
- Cloudflare R2.
- External integrations.

Use HTTPS.

Configure firewall rules and SSH security.

Do not expose PostgreSQL directly to the public internet.

Use Neon connection pooling where appropriate.

The backend should use asynchronous I/O for external API calls and LLM requests.

Do not assume that increasing the number of application workers will automatically improve performance on a 2 OCPU VPS.

Monitor CPU, RAM, network traffic, request latency, and database connection usage.

The application must remain stateless between requests wherever possible. Persist important conversation and task state in PostgreSQL.

# 15. Testing Strategy

Testing is mandatory.

Use:

- pytest for backend tests.
- httpx for API testing.
- Testcontainers or isolated test databases where appropriate.
- Vitest for frontend unit tests.
- Playwright for end-to-end testing.

Required backend tests:

- Authentication.
- Workspace isolation.
- Conversation creation.
- Message persistence.
- LLM provider errors.
- Tool argument validation.
- Tool permission checks.
- Tool execution limits.
- Document ingestion.
- Retrieval isolation.
- Database query restrictions.
- Streaming behavior.

Required security tests:

- User A cannot access User B's conversations.
- Workspace A cannot retrieve Workspace B's documents.
- Unauthorized users cannot execute restricted tools.
- Expired tokens are rejected.
- Invalid integration credentials are handled safely.
- Tool calls cannot bypass server-side authorization.

# 16. Logging and Observability

Implement structured logging from the beginning.

Track:

- Request ID.
- User/workspace ID where appropriate.
- Conversation ID.
- LLM provider.
- Model.
- Token usage.
- Response latency.
- Tool execution duration.
- Tool failures.
- API errors.

Never log:

- Passwords.
- API keys.
- Full authentication tokens.
- Unredacted sensitive document contents.
- Sensitive database results.

Add a basic health endpoint:

```http
GET /health
```

It should report service health without disclosing secrets or infrastructure internals.

Add provider usage tracking and basic per-user request limits.

# 17. Development Roadmap

Build the project in the following order.

## Phase 0 — Project foundation

Deliverables:

- GitHub repository.
- Monorepo.
- Next.js application.
- FastAPI application.
- Local Docker Compose setup.
- Environment configuration.
- Neon database connection.
- Initial documentation.

Acceptance criteria:

- Both applications start successfully.
- Frontend can communicate with backend.
- Backend can connect to Neon.
- Migrations run successfully.
- No secrets are committed to GitHub.

## Phase 1 — Authentication and conversations

Deliverables:

- Registration.
- Login.
- Logout.
- Token refresh.
- Workspace creation.
- Workspace membership.
- Conversation CRUD.
- Message persistence.

Acceptance criteria:

- Users can register and log in.
- Conversations persist after refreshing the browser.
- Users cannot access other users' conversations.
- Workspace authorization is enforced.

## Phase 2 — LLM integration

Deliverables:

- Provider abstraction.
- OpenAI integration.
- Model configuration.
- Basic chat.
- Streaming.
- Token usage tracking.
- Error handling.

Acceptance criteria:

- User can send a message.
- Backend calls the configured LLM.
- Assistant responds correctly.
- Responses stream to the frontend.
- Conversation history is persisted.
- Provider errors do not crash the application.

## Phase 3 — Tool calling

Deliverables:

- Tool registry.
- Tool schemas.
- Tool execution engine.
- Calculator tool.
- Date/time tool.
- Execution history.
- Tool limits.

Acceptance criteria:

- AI can select an appropriate tool.
- Arguments are validated.
- Tool executes on the backend.
- Result is returned to the LLM.
- AI can explain the result.
- Unauthorized tools cannot execute.

## Phase 4 — Knowledge engine

Deliverables:

- Document upload.
- Text extraction.
- Chunking.
- Embeddings.
- pgvector storage.
- Semantic search.
- Source citations.

Acceptance criteria:

- User can upload a PDF.
- Document is processed successfully.
- User can ask questions about it.
- Responses are grounded in retrieved content.
- Source references are displayed.
- Other workspaces' documents remain inaccessible.

## Phase 5 — Database integrations

Deliverables:

- Integration framework.
- PostgreSQL connector.
- Schema discovery.
- Approved read-only operations.
- SQL Server connector as an additional integration.

Acceptance criteria:

- User can configure a supported database connection.
- Connection can be tested.
- AI can retrieve permitted schema metadata.
- AI can invoke approved read-only data tools.
- Query limits and permissions are enforced.

## Phase 6 — Developer assistant

Deliverables:

- GitHub integration.
- Repository indexing.
- Code search.
- Documentation retrieval.
- Repository question answering.
- Basic code explanation.

Acceptance criteria:

- User can connect an authorized GitHub repository.
- AI can retrieve relevant source files.
- AI can explain project architecture.
- Responses include file paths and relevant line references where available.

## Phase 7 — Advanced agent capabilities

Deliverables:

- LangGraph evaluation and integration.
- Multi-step planning.
- Persistent task state.
- Retry and recovery mechanisms.
- Human approval workflows.
- More sophisticated memory.

Acceptance criteria:

- Agent can complete a multi-step read-only task.
- Failed steps are handled gracefully.
- Sensitive actions require approval.
- Execution history is inspectable.

## Phase 8 — Production deployment

Deliverables:

- Vercel deployment.
- Dockerized backend.
- HTTPS.
- Reverse proxy.
- Production database configuration.
- Object storage.
- Backups.
- Monitoring.
- Rate limits.
- Deployment documentation.

Acceptance criteria:

- Production frontend communicates securely with backend.
- Backend survives restarts.
- Data persists.
- Secrets are configured securely.
- Health checks work.
- Logs and errors are accessible.
- Backup and recovery procedures are documented.

---

# 18. Antigravity Development Instructions

These instructions are important.

Do not ask Antigravity to implement the entire project in a single operation.

Use the following implementation process:

1. Read the entire MASTER_PLAN.md.
2. Inspect the existing repository before making changes.
3. Understand the current architecture.
4. Implement only the currently assigned phase.
5. Follow the established folder structure and naming conventions.
6. Write tests alongside implementation.
7. Run tests and fix failures.
8. Update documentation.
9. Report completed functionality and known limitations.
10. Wait for approval before proceeding to the next phase.

### Code quality requirements

- Follow Python type hints.
- Use async functions appropriately.
- Follow PEP 8.
- Use dependency injection in FastAPI.
- Separate business logic from API controllers.
- Use repository and service layers where appropriate.
- Use Pydantic schemas for validation.
- Use SQLAlchemy models for persistence.
- Use Alembic for schema changes.
- Keep frontend components modular.
- Avoid duplicated business logic.
- Never hardcode secrets.
- Never silently swallow exceptions.
- Do not add unnecessary dependencies.

### Architectural constraints

- Do not introduce microservices without justification.
- Do not give the LLM direct unrestricted SQL access.
- Do not allow unrestricted Python execution.
- Do not put LLM provider calls inside frontend code.
- Do not mix AI orchestration with HTTP route handlers.
- Do not couple the AI engine to the developer assistant.
- Do not bypass authentication for convenience.
- Do not claim a feature is implemented without tests.

### Important development rule

If a requirement is ambiguous, stop and explain the ambiguity before implementing it.

Do not invent major architecture decisions.

---

# 19. Initial Antigravity Master Prompt

Use this prompt after creating the repository and placing this document in the project root as MASTER_PLAN.md.

---

You are the lead software architect and senior full-stack engineer responsible for implementing Personal AI Core.

Your task is to build the system according to MASTER_PLAN.md.

First, read the entire specification.

Do not immediately start implementing all features.

Your first responsibility is to:

1. Inspect the repository.
2. Analyze the project requirements.
3. Identify architectural dependencies.
4. Identify missing information.
5. Propose the initial repository structure.
6. Prepare an implementation checklist for Phase 0.
7. Identify any technical risks or conflicts in the specification.

Do not generate the entire application at once.

Implement the project incrementally, one phase at a time.

Maintain strict separation between:

- Frontend.
- Backend API.
- AI orchestration.
- LLM providers.
- Knowledge retrieval.
- Tool execution.
- External integrations.
- Database access.

Treat security, workspace isolation, and testability as first-class requirements.

Use the specified technology stack unless you identify a concrete technical limitation. Explain any proposed deviation before implementing it.

After each phase:

- Run relevant automated tests.
- Fix errors.
- Update documentation.
- Report changed files.
- Report implemented functionality.
- Report remaining limitations.
- Wait for approval before starting the next phase.

Do not use placeholder implementations for features reported as complete.

Do not expose API keys or sensitive data.

Do not implement unrestricted AI-generated SQL or arbitrary code execution.

The goal is to produce maintainable, tested, production-oriented software, not merely a working demonstration.

Begin by analyzing the repository and preparing the Phase 0 implementation plan.

---

# 20. Definition of Done for V1

The first release can be considered complete when:

- [ ] User registration and authentication work.
- [ ] Workspace isolation works.
- [ ] Conversations persist.
- [ ] OpenAI integration works.
- [ ] Streaming responses work.
- [ ] Tool calling works.
- [ ] Tool execution is validated and logged.
- [ ] Documents can be uploaded.
- [ ] Documents can be indexed.
- [ ] Semantic search works.
- [ ] Responses include document citations.
- [ ] A read-only database integration works.
- [ ] Security tests pass.
- [ ] Frontend is deployed on Vercel.
- [ ] Backend is deployed on Oracle VPS.
- [ ] Neon PostgreSQL is configured for production.
- [ ] Documentation and deployment instructions are complete.

**Final engineering objective:** Build a reusable AI foundation that can support multiple applications in the future without requiring a complete rewrite of the AI engine.

The developer assistant is the first application, not the entire platform.
