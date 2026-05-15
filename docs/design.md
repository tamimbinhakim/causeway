# Design philosophy

Six principles. Each is a knife — they cut things out as much as they decide what to keep.

## 1. Conventions over configuration, defaults over magic

Every choice has one obvious place; surprising behavior is a bug. There is one place to register a route (the routes directory), one place to declare config (`config.py`), one place to install plugins (`plugins.py`). If two ways to do the same thing emerge, one of them is wrong and we kill it.

## 2. Backend-only

No SSR, no template engine, no asset pipeline. The TypeScript client is Dyadpy's job. The frontend is yours. Quay produces an ASGI app and a manifest; you produce a product.

## 3. Plugins, not batteries

Core ships **contracts** (TaskAdapter, Storage, KV, AuthProvider) and **one reference adapter** each. Picking a real implementation is a one-line plugin install. We deliberately reject the Rails / Laravel / AdonisJS "framework owns everything" model — its productivity peak is greenfield, its mismatch with reality ("we use Clerk", "we use Modal for jobs") is painful.

## 4. Type-driven, IR-grounded

Everything Quay knows about your app — routes, jobs, config — lives in Dyadpy's IR so it can flow to clients, dashboards, tests, and deployment artifacts. There is no second source of truth. If Quay knows it, the IR knows it.

## 5. General-purpose, narrow scope

Quay binds the web / task surface and stops there. No AI / LLM primitives, no ORM, no admin panel, no infra provisioning. Those layers move on a different cadence and live in user code or in dedicated libraries.

## 6. One artifact, anywhere

A Quay app is an ASGI app + a manifest. It runs under `uvicorn` locally, in Docker, on Modal, on Fly, on Lambda (via Mangum), without code changes. The deploy plugin is a wrapper around provider CLIs, not a hosting platform.

---

## The "lean core" boundary

The two coherent models in 2026 are:

- **The Rails / Laravel / AdonisJS model** — framework owns everything. Productivity peaks for greenfield; the mismatch with reality is painful.
- **The Encore / Litestar / NestJS model** — framework owns architecture and primitives, delegates implementations.

Quay is the second model. We opinionate on **structure, lifecycle, naming, and contracts** — and stay deliberately neutral on **storage, identity, infrastructure, presentation, and AI tooling**.

## Positioning matrix

| Framework          | Scope                | Owns ORM?        | Owns auth? | File routing? | AI primitives? | Closest comparison |
| ------------------ | -------------------- | ---------------- | ---------- | ------------- | -------------- | ------------------ |
| FastAPI            | router lib           | no               | no         | no            | no             | building block     |
| Litestar           | API framework        | partial (SQLA)   | primitives | no            | no             | peer-ish, lower    |
| Django + Ninja     | full framework       | yes              | yes        | no            | no             | heavy alternative  |
| AdonisJS / Laravel | full-stack batteries | yes              | yes        | no            | no             | what Quay isn't    |
| NestJS             | structural framework | no               | partial    | no            | no             | structural peer    |
| Encore.ts / .go    | backend + infra      | no (declarative) | partial    | no            | no             | closest ambition   |
| **Quay**           | backend framework    | **no**           | **no**     | **yes**       | **no**         | —                  |

In one sentence:

> _"Encore-style conventions, Litestar-style scope, Next.js-style routing, cloud-agnostic, ORM-agnostic, auth-agnostic, AI-agnostic by design."_

## Explicitly out of scope, ever

1. **No ORM in core.** Ever.
2. **No admin panel in core.** Recommend `sqladmin` / `Dashibase` / `retool`.
3. **No HTML rendering / template engine in core.**
4. **No infrastructure provisioning.** That's Terraform / Pulumi / Modal.
5. **No AI / LLM types in core.** No `quay.ai` module, no `Thread` / `@agent` / `VectorStore` primitives. LLM tooling is user code or a dedicated library (LangGraph / Pydantic AI / Mastra).
6. **No frontend.** Dyadpy ships a TypeScript client; what you do with it is your concern.

## Decision-forcing changes

If the world shifts, the plan shifts:

| If…                                                      | Then…                                                                               |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Dyadpy's IR can't represent task registrations cleanly   | Add an `extensions` namespace to Dyadpy's IR first; don't fork the IR               |
| Users hate `[id].py` literal brackets in their file tree | Add a compatibility layer for `_id.py` style — but keep brackets canonical          |
| Dramatiq adoption is too low among target users          | Switch the reference to TaskIQ (newer, asyncio-native); keep the contract identical |
| `pydantic-settings` v3 changes API significantly         | Vendor a thin wrapper that exposes a stable `Settings` interface                    |
| User demand emerges for server-rendered HTML             | Do not add it. Recommend HTMX + a separate template lib. Hold the line.             |
| User demand emerges for multi-tenancy                    | Add it in v0.3 as a `tenant` scope on `_scope.py` — not in v0.1                     |
| User demand emerges for built-in LLM helpers             | Do not add them. Point to LangGraph / Pydantic AI / Mastra. Hold the line.          |
