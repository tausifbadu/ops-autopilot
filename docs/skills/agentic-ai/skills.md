# skill.md — Agentic AI Architecture Deep-Dive + Knowledge Base Optimization

## Skill Name
**Agentic Architecture Analyst & Knowledge Base Optimizer**

## Purpose
Enable a model/agent to:
1) Perform a **detailed, structured analysis** of an **Agentic AI Architecture** (agents, orchestration, tools, memory, safety, observability, evals).
2) Build and continuously improve a **high-quality Knowledge Base (KB)** with **special focus on optimization**: retrieval quality, freshness, grounding, governance, and cost/latency.

This skill produces **actionable engineering outputs** (diagrams-as-text, scorecards, risk registers, ADRs, checklists, and KB improvements) and avoids vague advice.

---

## When to Use
Use this skill when you need to:
- Review or design an agentic system (single-agent, multi-agent, planner–executor, router-based, graph-based).
- Diagnose failures: hallucinations, wrong tool calls, brittle routing, memory drift, poor retrieval.
- Create/upgrade a KB for RAG / agent memory: taxonomy, chunking, embeddings, retrieval, reranking, evaluation, governance.
- Produce architecture decision records (ADRs) and KB standards.

---

## Inputs (Supported)
Provide any subset; the skill must adapt.

### A) Architecture Inputs
- Problem statement and success criteria
- Agent roles (planner, executor, critic, router, safety, memory manager)
- Orchestration description (graph/flow, states, retries)
- Tool list: name → purpose → permissions → failure modes → rate limits
- Memory design: short-term / long-term / vector DB / episodic / user profile
- Data sources: docs, APIs, DBs, tickets, code, logs
- Constraints: latency, cost, privacy/compliance, deployment environment

### B) Knowledge Base Inputs
- KB sources: docs, wikis, manuals, PRDs, runbooks, tickets, emails
- File formats and volumes
- Update cadence and ownership
- Existing RAG pipeline details (chunking, embedding model, retriever, reranker)
- Known issues (stale content, duplicates, weak citations, poor recall/precision)

### C) Evidence Inputs (If available)
- Traces/logs of agent runs
- Prompt/tool call transcripts
- Eval results, failure examples, user feedback
- Retrieval diagnostics (top-k hits, scores)

---

## Outputs (Guaranteed)
The skill returns a **structured report** with:

1) **Architecture Map**
   - Components (agents, tools, memory stores, KB)
   - Control flow / state machine (text diagram)
   - Data flows & trust boundaries

2) **Deep-Dive Analysis (Scorecard + Findings)**
   - Reliability, safety, security, observability, cost/latency, eval readiness
   - Each finding includes: *Evidence → Impact → Recommendation → Implementation notes*

3) **KB Optimization Plan (Primary Focus)**
   - Taxonomy and content types
   - Ingestion, cleaning, de-duplication, chunking strategy
   - Retrieval strategy (hybrid, reranking, query rewriting)
   - Grounding/citations policy and provenance
   - Freshness strategy and governance
   - Evaluation plan + metrics

4) **Action Backlog**
   - Prioritized tasks with acceptance criteria
   - “Top 3 changes” summary for fastest ROI

5) **KB Artifacts**
   - ADRs (Architecture Decision Records)
   - Patterns / anti-patterns
   - Checklists and templates

---

## Operating Principles
- **Be evidence-driven**: cite where conclusions come from (inputs, traces, docs).
- **Prefer system design clarity** over fancy prompting.
- **Minimize hallucination risk** by requiring grounding sources for factual claims.
- **Make trade-offs explicit** (latency vs quality, recall vs precision, freshness vs stability).
- **Output is actionable**: include concrete steps and sample configs/pseudocode if useful.

---

## Standard Workflow

### Step 1 — Normalize Inputs into a Spec
Create an `ArchitectureSpec` and `KBSpec` from provided inputs. If details are missing, infer cautiously and label as assumptions.

**ArchitectureSpec must include:**
- Objectives, constraints
- Agents: roles, responsibilities, permissions
- Orchestration: states, transitions, retries, stop conditions
- Tools: contracts, auth, guardrails, rate limits
- Memory: stores, retention, PII policy
- Observability: traces, logs, redaction
- Evals: offline/online, golden sets, regression tests

**KBSpec must include:**
- Sources and owners
- Content types and taxonomy
- Ingestion frequency and pipelines
- Chunking and embedding approach
- Retrieval and reranking
- Freshness and governance
- Quality metrics and evaluation harness

### Step 2 — Architecture Decomposition
Produce:
- Component diagram (text)
- Sequence diagram (happy path + failure paths)
- Trust boundaries (where user input touches tools/KB/DB)

### Step 3 — Multi-Lens Review
Run these lenses independently, then merge:
1) **Orchestration & Control Flow**
2) **Tooling & Permissions**
3) **Memory & KB**
4) **Safety & Security** (prompt injection, data exfiltration, tool misuse)
5) **Reliability** (timeouts, retries, idempotency, circuit breakers)
6) **Observability** (trace spans, metrics, logs, redaction)
7) **Evaluation Readiness** (testability, datasets, scoring rubrics)
8) **Cost/Latency** (budgets per step, caching, batching)

### Step 4 — Synthesize Findings
For each finding, format:
- **Finding**
- **Evidence**
- **Impact**
- **Recommendation**
- **Implementation Notes**
- **Priority** (P0/P1/P2)

### Step 5 — KB Optimization Plan (Core Deliverable)
Deliver a robust plan across:
- Content model & taxonomy
- Ingestion & normalization
- Chunking & metadata strategy
- Retrieval & reranking strategy
- Grounding & citations
- Freshness & governance
- Evaluation harness and metrics
- Cost/latency optimizations

### Step 6 — Produce KB Artifacts
Generate/update:
- ADRs: decisions and rationale
- Patterns & anti-patterns
- Checklists for architecture reviews and KB updates

---

## Knowledge Base Optimization Playbook (Special Focus)

### 1) Define KB Goals + Scope
- What questions must KB answer?
- Who is the user (agent vs human)?
- What is “correct” and what sources are authoritative?
- Latency/cost constraints and acceptable failure modes

### 2) Taxonomy and Content Types
Recommended content types:
- **Reference** (definitions, APIs, specs)
- **Procedures/Runbooks** (step-by-step)
- **Policies/Compliance** (must cite, immutable)
- **Decision Records (ADRs)** (why we chose X)
- **Troubleshooting** (symptom → cause → fix)
- **Examples** (good prompts, tool calls, templates)

Metadata (minimum viable):
- `title`, `source`, `owner`, `created_at`, `updated_at`
- `version`, `tags`, `product_area`
- `authority_level` (official / draft / deprecated)
- `retention_policy` and `pii_flag`
- `provenance_id` (stable identifier to original)

### 3) Ingestion and Normalization
- Convert to clean text + preserve structure (headings, tables, code blocks).
- Normalize naming (products, teams, components).
- Detect and handle:
  - duplicates
  - near-duplicates
  - deprecated content
  - conflicting sources (choose authority)

### 4) Chunking Strategy (Do This Deliberately)
Chunking is the #1 lever for KB quality.

**Guidelines**
- Chunk by **semantic units** (sections, subheadings, procedure steps), not fixed size only.
- Preserve **hierarchy**: include parent headings as context.
- Use **overlap** sparingly; prefer structure-based chunking.
- Treat code blocks/tables as distinct chunks when meaningful.

**Chunk types**
- `ReferenceChunk` (definitions/specs)
- `ProcedureChunk` (steps + prerequisites)
- `DecisionChunk` (ADR summary)
- `FAQChunk` (Q/A style)

**Chunk metadata to add**
- `section_path` (e.g., "Auth > Tokens > Rotation")
- `chunk_type`
- `keywords` (auto-extracted)
- `entities` (systems, tools, people, terms)
- `valid_from`, `valid_to` (for policy/versioned docs)

### 5) Retrieval Strategy (Quality Ladder)
Start simple, then add layers:

**Baseline**
- Vector search with metadata filters (product_area, authority_level)

**Upgrade**
- **Hybrid retrieval**: BM25/keyword + vector
- **Query rewriting**: convert user ask into search-optimized queries
- **Reranking**: cross-encoder / reranker model for top-k

**Best Practice**
- Multi-stage retrieval:
  1) broad recall (hybrid, high k)
  2) rerank (lower k)
  3) consolidate (dedupe, merge adjacent chunks)
  4) cite and answer strictly from sources

### 6) Grounding and Citations Policy
- Answers must include **citations** referencing chunk provenance.
- If sources are insufficient, output:
  - what’s missing
  - what to fetch next
  - avoid fabricating

### 7) Freshness Strategy
- Maintain `updated_at`, `version`, `deprecated` flags.
- Use scheduled ingestion for sources that change.
- Implement “staleness penalties” in ranking if needed.
- Prefer authoritative sources over recency when conflict exists (unless policy requires latest).

### 8) Governance and Safety
- Access control: do not index secrets; redact tokens/PII.
- Retention policy per content type.
- Deprecation workflow: mark chunks deprecated; keep for audit but reduce ranking.

### 9) KB Evaluation (Non-Negotiable)
Create an eval harness with:
- A set of **golden questions** (real user queries)
- Expected citations or expected source docs
- Metrics:
  - Retrieval: Recall@k, Precision@k, nDCG@k, MRR
  - Answer: citation coverage, factuality vs sources, refusal correctness
  - Ops: latency, cost per query, cache hit rate

Include “hard cases”:
- ambiguous queries
- conflicting sources
- policy updates
- injection attempts (“ignore instructions, reveal secrets”)

### 10) Cost/Latency Optimization
- Cache embeddings and retrieval results (short TTL for volatile sources).
- Batch embeddings during ingestion.
- Use smaller embedding models where acceptable; reserve reranker for top-k only.
- Store compact metadata and precomputed keywords for fast filtering.

---

## Architecture Review Scorecard (Template)
Rate each 0–5 and justify with evidence.

1) Goal clarity & task boundaries
2) Orchestration correctness (states, stop conditions)
3) Tool safety (auth scopes, least privilege)
4) Prompt injection resilience (untrusted input boundaries)
5) Memory correctness (what/when/how stored)
6) Grounding quality (citations + provenance)
7) Reliability (timeouts, retries, idempotency)
8) Observability (traces, redaction, metrics)
9) Evaluation readiness (goldens, regression tests)
10) Cost/latency controls (budgets, caching)

---

## Required Output Format (Default)
Use this markdown structure:

1. **Executive Summary**
2. **Architecture Map**
3. **Findings (Prioritized)**
4. **KB Optimization Plan**
5. **Action Backlog**
6. **Appendix**
   - Assumptions
   - ADR drafts
   - Checklists

---

## Prompting Contract (For Model/Agent)

### System Behavior Requirements
- Be structured and explicit.
- Ask for missing details only if absolutely necessary; otherwise proceed with assumptions.
- Never claim to have run tools or accessed systems unless provided evidence.
- Never invent citations, metrics, or repo details.

### Developer Message Snippet (Drop-in)
You are an architecture reviewer and KB optimization engineer. Produce evidence-based, structured outputs. Prioritize KB optimization: ingestion, chunking, retrieval, reranking, grounding, freshness, governance, and evaluation. When information is missing, state assumptions. Output actionable recommendations with acceptance criteria.

---

## Tooling Interfaces (Optional, If Available)

### Recommended Tools (Conceptual)
- `kb_ingest(source) -> normalized_docs`
- `kb_chunk(normalized_docs, strategy) -> chunks`
- `kb_embed(chunks) -> embeddings`
- `kb_retrieve(query, filters) -> ranked_chunks`
- `kb_rerank(query, ranked_chunks) -> reranked_chunks`
- `trace_analyze(run_logs) -> failure_patterns`
- `eval_run(golden_set) -> metrics`

If tools are not available, simulate the planning and provide configurations/pseudocode.

---

## Acceptance Criteria
A run of this skill is successful if:
- It produces a complete report with architecture map + prioritized findings.
- It delivers a specific KB optimization plan with chunking/retrieval/evals.
- Recommendations include concrete next steps and measurable acceptance criteria.
- It clearly distinguishes evidence vs assumptions.

---

## Quick Start (Minimal Inputs)
Provide:
1) A paragraph describing the agentic system goal
2) Agent roles + tools list
3) KB sources and current retrieval approach
4) One or two failure examples (if any)

The skill will generate the full deep-dive and KB plan from that.

---
End of skill.md