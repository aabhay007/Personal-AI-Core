# Architecture Specification

## Overview
Personal AI Core is designed as a **modular monolith** with extensible integrations.
The core AI orchestration engine is strictly decoupled from the web layer, database persistence layer, and external integrations.

```text
                  USER
                    |
                    v
           NEXT.JS FRONTEND (TypeScript + Tailwind)
                    |
                    v
             FASTAPI BACKEND (/api/v1)
                    |
           AUTHENTICATION LAYER (Argon2id + JWT)
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
```

## Guiding Principles
1. **Decoupled AI Engine**: The core AI logic operates via standardized provider, tool, and retrieval interfaces.
2. **Workspace Isolation**: All resources (conversations, messages, documents, tools, integrations) are strictly bounded by `workspace_id`.
3. **Defense in Depth**:
   - No arbitrary SQL execution by LLMs (predefined parameterized operations only).
   - No arbitrary code evaluation.
   - Validation on all LLM tool inputs via Pydantic schemas.
4. **Pragmatic Infrastructure**: Monolith first. Scale to microservices or distributed queues only when technically necessary.
